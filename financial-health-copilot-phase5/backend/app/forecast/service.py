import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal, Sequence
from uuid import UUID

from app.core import config
from app.db.models import (
    Account,
    Category,
    IncomeSource,
    Loan,
    RecurringTransaction,
    Transaction,
)

TWO_PLACES = Decimal("0.01")
ZERO = Decimal("0.00")


@dataclass(frozen=True)
class ProjectionPoint:
    date: date
    projected_balance: Decimal
    lower_bound: Decimal
    upper_bound: Decimal
    scheduled_inflow: Decimal
    scheduled_outflow: Decimal
    unscheduled_spend: Decimal


@dataclass(frozen=True)
class ForecastResult:
    as_of_date: date
    horizon_days: int
    daily_projection: list[ProjectionPoint]
    confidence: Literal["high", "medium", "low"]
    history_days: int
    spending_cv: Decimal
    recurring_coverage_pct: Decimal
    rolling_average_daily_spend: Decimal
    trend_factor: Decimal


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def add_calendar_months(value: date, months: int = 1) -> date:
    """Advance by calendar months while retaining the day where possible."""
    month_index = value.year * 12 + value.month - 1 + months
    year, zero_based_month = divmod(month_index, 12)
    month = zero_based_month + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def add_calendar_years(value: date, years: int = 1) -> date:
    day = min(value.day, calendar.monthrange(value.year + years, value.month)[1])
    return date(value.year + years, value.month, day)


def advance_occurrence(value: date, frequency: str) -> date | None:
    normalized = frequency.lower()
    if normalized == "weekly":
        return value + timedelta(days=7)
    if normalized == "biweekly":
        return value + timedelta(days=14)
    if normalized == "monthly":
        return add_calendar_months(value)
    if normalized == "quarterly":
        return add_calendar_months(value, 3)
    if normalized in ("yearly", "annual"):
        return add_calendar_years(value)
    return None


def next_occurrence(value: date | None, frequency: str, after: date) -> date | None:
    if value is None:
        return None
    occurrence = value
    while occurrence <= after:
        advanced = advance_occurrence(occurrence, frequency)
        if advanced is None or advanced <= occurrence:
            return None
        occurrence = advanced
    return occurrence


def coefficient_of_variation(values: Sequence[Decimal]) -> Decimal:
    if len(values) < 2:
        return ZERO
    mean = sum(values, ZERO) / Decimal(len(values))
    if mean <= ZERO:
        return ZERO
    variance = sum(((value - mean) ** 2 for value in values), ZERO) / Decimal(len(values) - 1)
    return variance.sqrt() / mean


def classify_forecast_confidence(
    history_days: int,
    spending_cv: Decimal,
    recurring_coverage_pct: Decimal,
) -> Literal["high", "medium", "low"]:
    """Apply the confidence bands from FORECASTING_AND_RISK.md."""
    if (
        history_days >= config.FORECAST_CONFIDENCE_HIGH_MIN_MONTHS_HISTORY * 30
        and spending_cv < config.FORECAST_CONFIDENCE_HIGH_MAX_SPENDING_CV
        and recurring_coverage_pct >= config.FORECAST_CONFIDENCE_HIGH_MIN_RECURRING_COVERAGE_PCT
    ):
        return "high"
    if (
        history_days < 30
        or spending_cv > config.FORECAST_CONFIDENCE_MEDIUM_MAX_SPENDING_CV
        or recurring_coverage_pct < Decimal("50")
    ):
        return "low"
    return "medium"


def _full_period_totals(
    transactions: Sequence[Transaction],
    category_map: dict[UUID, Category],
    as_of_date: date,
    history_days: int,
) -> list[Decimal]:
    period_count = min(3, history_days // 30)
    newest_first: list[Decimal] = []
    for offset in range(period_count):
        period_end = as_of_date - timedelta(days=offset * 30)
        period_start = period_end - timedelta(days=29)
        total = sum(
            (
                txn.amount
                for txn in transactions
                if period_start <= txn.txn_date <= period_end
                and txn.direction == "debit"
                and txn.recurring_id is None
                and txn.category_id in category_map
                and category_map[txn.category_id].type in ("variable", "discretionary")
            ),
            ZERO,
        )
        newest_first.append(total)
    return list(reversed(newest_first))


def _trend_factor(period_totals: Sequence[Decimal]) -> Decimal:
    if len(period_totals) < 3:
        return Decimal("1.00")
    previous_average = (period_totals[0] + period_totals[1]) / Decimal("2")
    if previous_average <= ZERO:
        return Decimal("1.00")
    raw_factor = period_totals[2] / previous_average
    cap = config.FORECAST_TREND_CAP_PCT / Decimal("100")
    return min(Decimal("1") + cap, max(Decimal("1") - cap, raw_factor))


def _monthly_obligation(recurring: RecurringTransaction) -> Decimal:
    multipliers = {
        "weekly": Decimal("52") / Decimal("12"),
        "biweekly": Decimal("26") / Decimal("12"),
        "monthly": Decimal("1"),
        "quarterly": Decimal("1") / Decimal("3"),
        "yearly": Decimal("1") / Decimal("12"),
        "annual": Decimal("1") / Decimal("12"),
    }
    return recurring.expected_amount * multipliers.get(recurring.frequency.lower(), ZERO)


def _recurring_coverage(
    transactions: Sequence[Transaction],
    category_map: dict[UUID, Category],
    recurring: Sequence[RecurringTransaction],
    loans: Sequence[Loan],
    history_days: int,
) -> Decimal:
    total_expenses = sum(
        (
            txn.amount
            for txn in transactions
            if txn.direction == "debit"
            and not (txn.category_id in category_map and category_map[txn.category_id].type == "transfer")
        ),
        ZERO,
    )
    if total_expenses <= ZERO:
        return ZERO
    monthly_scheduled = sum(
        (_monthly_obligation(item) for item in recurring if item.status == "confirmed"), ZERO
    ) + sum((loan.monthly_installment for loan in loans), ZERO)
    scheduled_for_window = monthly_scheduled * Decimal(history_days) / Decimal("30")
    return min(Decimal("100"), scheduled_for_window / total_expenses * Decimal("100"))


def _scheduled_flows(
    as_of_date: date,
    horizon_days: int,
    recurring: Sequence[RecurringTransaction],
    income_sources: Sequence[IncomeSource],
    loans: Sequence[Loan],
    extra_inflows: Sequence[tuple[date, Decimal]] = (),
    extra_outflows: Sequence[tuple[date, Decimal]] = (),
    income_multiplier: Decimal | None = None,
    income_amount_override: Decimal | None = None,
    income_effective_date: date | None = None,
) -> tuple[dict[date, Decimal], dict[date, Decimal]]:
    inflows: dict[date, Decimal] = {}
    outflows: dict[date, Decimal] = {}
    horizon_end = as_of_date + timedelta(days=horizon_days)

    def add(target: dict[date, Decimal], occurrence: date, amount: Decimal) -> None:
        target[occurrence] = target.get(occurrence, ZERO) + amount

    for item in recurring:
        if item.status != "confirmed":
            continue
        occurrence = next_occurrence(item.next_expected_date, item.frequency, as_of_date)
        while occurrence is not None and occurrence <= horizon_end:
            add(outflows, occurrence, item.expected_amount)
            occurrence = advance_occurrence(occurrence, item.frequency)

    for source in income_sources:
        occurrence = next_occurrence(source.last_received_date, source.frequency, as_of_date)
        while occurrence is not None and occurrence <= horizon_end:
            amount = source.amount
            if income_effective_date is None or occurrence >= income_effective_date:
                if income_amount_override is not None:
                    amount = income_amount_override
                elif income_multiplier is not None:
                    amount *= income_multiplier
            add(inflows, occurrence, amount)
            occurrence = advance_occurrence(occurrence, source.frequency)

    for loan in loans:
        occurrence = next_occurrence(loan.start_date, "monthly", as_of_date)
        while occurrence is not None and occurrence <= horizon_end:
            add(outflows, occurrence, loan.monthly_installment)
            occurrence = add_calendar_months(occurrence)

    for occurrence, amount in extra_inflows:
        if as_of_date < occurrence <= horizon_end:
            add(inflows, occurrence, amount)
    for occurrence, amount in extra_outflows:
        if as_of_date < occurrence <= horizon_end:
            add(outflows, occurrence, amount)

    return inflows, outflows


def generate_forecast(
    accounts: Sequence[Account],
    transactions: Sequence[Transaction],
    recurring: Sequence[RecurringTransaction],
    income_sources: Sequence[IncomeSource],
    category_map: dict[UUID, Category],
    loans: Sequence[Loan],
    horizon_days: int = config.FORECAST_HORIZON_DEFAULT_DAYS,
    *,
    category_monthly_spend_overrides: dict[str, Decimal] | None = None,
    extra_scheduled_outflows: Sequence[tuple[date, Decimal]] = (),
    extra_scheduled_inflows: Sequence[tuple[date, Decimal]] = (),
    income_multiplier: Decimal | None = None,
    income_amount_override: Decimal | None = None,
    income_effective_date: date | None = None,
    maximum_horizon_days: int = config.FORECAST_HORIZON_MAX_DAYS,
) -> ForecastResult:
    if not 1 <= horizon_days <= maximum_horizon_days:
        raise ValueError("horizon_days is outside the supported range")
    if not transactions:
        raise ValueError("transactions are required to generate a forecast")

    as_of_date = max(txn.txn_date for txn in transactions)
    first_date = min(txn.txn_date for txn in transactions)
    available_history_days = (as_of_date - first_date).days + 1
    history_days = min(90, available_history_days)
    history_start = as_of_date - timedelta(days=history_days - 1)
    history_transactions = [txn for txn in transactions if history_start <= txn.txn_date <= as_of_date]

    unscheduled_transactions = [
        txn
        for txn in history_transactions
        if txn.direction == "debit"
        and txn.recurring_id is None
        and txn.category_id in category_map
        and category_map[txn.category_id].type in ("variable", "discretionary")
    ]
    unscheduled_total = sum((txn.amount for txn in unscheduled_transactions), ZERO)
    rolling_average_daily = unscheduled_total / Decimal(history_days)

    # Simulation-only overrides express a target monthly total for a category.
    # Replace that category's recent 30-day daily rate in the aggregate rather
    # than mutating historical transactions.
    for category_name, target_monthly_total in (category_monthly_spend_overrides or {}).items():
        recent_days = min(30, history_days)
        recent_start = as_of_date - timedelta(days=recent_days - 1)
        recent_total = sum(
            (
                txn.amount
                for txn in history_transactions
                if txn.direction == "debit"
                and txn.recurring_id is None
                and txn.txn_date >= recent_start
                and txn.category_id in category_map
                and category_map[txn.category_id].name == category_name
            ),
            ZERO,
        )
        rolling_average_daily += max(ZERO, target_monthly_total) / Decimal("30") - recent_total / Decimal(
            recent_days
        )
    rolling_average_daily = max(ZERO, rolling_average_daily)

    period_totals = _full_period_totals(history_transactions, category_map, as_of_date, history_days)
    spending_cv = coefficient_of_variation(period_totals)
    trend_factor = _trend_factor(period_totals)
    adjusted_daily_spend = rolling_average_daily * trend_factor
    recurring_coverage_pct = _recurring_coverage(
        history_transactions, category_map, recurring, loans, history_days
    )
    confidence = classify_forecast_confidence(history_days, spending_cv, recurring_coverage_pct)

    inflows, outflows = _scheduled_flows(
        as_of_date,
        horizon_days,
        recurring,
        income_sources,
        loans,
        extra_inflows=extra_scheduled_inflows,
        extra_outflows=extra_scheduled_outflows,
        income_multiplier=income_multiplier,
        income_amount_override=income_amount_override,
        income_effective_date=income_effective_date,
    )
    balance = sum(
        (account.balance for account in accounts if account.type in ("checking", "savings")),
        ZERO,
    )
    projections: list[ProjectionPoint] = []
    for day_number in range(1, horizon_days + 1):
        projection_date = as_of_date + timedelta(days=day_number)
        scheduled_inflow = inflows.get(projection_date, ZERO)
        scheduled_outflow = outflows.get(projection_date, ZERO)
        balance += scheduled_inflow - scheduled_outflow - adjusted_daily_spend
        bound_width = spending_cv * rolling_average_daily * Decimal(day_number).sqrt()
        projections.append(
            ProjectionPoint(
                date=projection_date,
                projected_balance=quantize_money(balance),
                lower_bound=quantize_money(balance - bound_width),
                upper_bound=quantize_money(balance + bound_width),
                scheduled_inflow=quantize_money(scheduled_inflow),
                scheduled_outflow=quantize_money(scheduled_outflow),
                unscheduled_spend=quantize_money(adjusted_daily_spend),
            )
        )

    return ForecastResult(
        as_of_date=as_of_date,
        horizon_days=horizon_days,
        daily_projection=projections,
        confidence=confidence,
        history_days=history_days,
        spending_cv=spending_cv.quantize(TWO_PLACES, rounding=ROUND_HALF_UP),
        recurring_coverage_pct=recurring_coverage_pct.quantize(TWO_PLACES, rounding=ROUND_HALF_UP),
        rolling_average_daily_spend=quantize_money(rolling_average_daily),
        trend_factor=trend_factor.quantize(TWO_PLACES, rounding=ROUND_HALF_UP),
    )
