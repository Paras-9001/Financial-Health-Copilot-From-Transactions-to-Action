"""Risk rule engine implementing all seven rules from FORECASTING_AND_RISK.md.

Each rule is a pure function that returns a RiskCandidate or None.
The engine runs all rules and returns a deduplicated, sorted list of risk candidates.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal, Sequence
from uuid import UUID

from app.core import config
from app.db.models import (
    Account,
    Category,
    CreditCard,
    IncomeSource,
    Loan,
    RecurringTransaction,
    Transaction,
)
from app.forecast.service import ForecastResult, ProjectionPoint

ZERO = Decimal("0.00")
TWO = Decimal("0.01")

RiskType = Literal[
    "low_cash_buffer",
    "upcoming_cash_flow_gap",
    "unusually_high_spending",
    "recurring_payment_burden",
    "debt_pressure",
    "income_volatility",
    "unusual_transaction",
]


@dataclass(frozen=True)
class RiskCandidate:
    risk_type: RiskType
    severity: Literal["low", "medium", "high"]
    evidence: dict
    confidence: Decimal
    # dedup key: same type + same primary evidence key => same risk
    dedup_key: str


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(TWO)


def _coefficient_of_variation(values: Sequence[Decimal]) -> Decimal:
    if len(values) < 2:
        return ZERO
    mean = sum(values, ZERO) / Decimal(len(values))
    if mean <= ZERO:
        return ZERO
    variance = sum(((v - mean) ** 2 for v in values), ZERO) / Decimal(len(values) - 1)
    return variance.sqrt() / mean


def _avg_daily_expense(
    transactions: Sequence[Transaction],
    category_map: dict[UUID, Category],
    history_days: int,
) -> Decimal:
    """Trailing daily expense (all debit non-transfer transactions)."""
    if not transactions or history_days <= 0:
        return ZERO
    expense_total = sum(
        (
            txn.amount
            for txn in transactions
            if txn.direction == "debit"
            and txn.category_id in category_map
            and category_map[txn.category_id].type != "transfer"
        ),
        ZERO,
    )
    return expense_total / Decimal(history_days)


# ---------------------------------------------------------------------------
# Rule 1: Low cash buffer
# ---------------------------------------------------------------------------


def rule_low_cash_buffer(
    accounts: Sequence[Account],
    transactions: Sequence[Transaction],
    category_map: dict[UUID, Category],
    history_days: int,
) -> RiskCandidate | None:
    """cash_buffer_days < LOW_BUFFER_DAYS_MEDIUM (5) triggers risk."""
    liquid = sum(
        (a.balance for a in accounts if a.type in ("checking", "savings")),
        ZERO,
    )
    avg_daily = _avg_daily_expense(transactions, category_map, history_days)
    if avg_daily <= ZERO:
        return None

    buffer_days = liquid / avg_daily
    threshold = Decimal(str(config.LOW_BUFFER_DAYS_MEDIUM))
    if buffer_days >= threshold:
        return None

    severity: Literal["high", "medium"] = (
        "high" if buffer_days < Decimal(str(config.LOW_BUFFER_DAYS_HIGH)) else "medium"
    )
    confidence = Decimal("0.90") if history_days >= 30 else Decimal("0.60")
    return RiskCandidate(
        risk_type="low_cash_buffer",
        severity=severity,
        evidence={
            "current_balance": f"{_quantize(liquid):.2f}",
            "avg_daily_expense": f"{_quantize(avg_daily):.2f}",
            "cash_buffer_days": f"{_quantize(buffer_days):.2f}",
            "threshold_days": config.LOW_BUFFER_DAYS_MEDIUM,
        },
        confidence=_quantize(confidence),
        dedup_key="low_cash_buffer",
    )


# ---------------------------------------------------------------------------
# Rule 2: Upcoming cash-flow gap
# ---------------------------------------------------------------------------


def rule_upcoming_cash_flow_gap(
    forecast: ForecastResult,
    preferred_buffer: Decimal,
) -> RiskCandidate | None:
    """Forecast shows projected_balance < 0 (or < preferred_buffer) within horizon."""
    breach_point: ProjectionPoint | None = None
    for point in forecast.daily_projection:
        if point.projected_balance < preferred_buffer:
            breach_point = point
            break

    if breach_point is None:
        return None

    # contributing flows on that date — outflows dominate
    contributing = []
    if breach_point.scheduled_outflow > ZERO:
        contributing.append(f"Scheduled outflow -{breach_point.scheduled_outflow:.2f}")
    if breach_point.unscheduled_spend > ZERO:
        contributing.append(f"Avg daily spend -{breach_point.unscheduled_spend:.2f}")

    severity: Literal["high", "medium"] = "high" if breach_point.projected_balance < ZERO else "medium"
    confidence_map = {"high": Decimal("0.85"), "medium": Decimal("0.65"), "low": Decimal("0.45")}
    return RiskCandidate(
        risk_type="upcoming_cash_flow_gap",
        severity=severity,
        evidence={
            "breach_date": breach_point.date.isoformat(),
            "projected_balance": f"{_quantize(breach_point.projected_balance):.2f}",
            "contributing_flows": contributing,
        },
        confidence=_quantize(confidence_map[forecast.confidence]),
        dedup_key=f"upcoming_cash_flow_gap:{breach_point.date.isoformat()}",
    )


# ---------------------------------------------------------------------------
# Rule 3: Unusually high spending by category
# ---------------------------------------------------------------------------


def rule_unusually_high_spending(
    transactions: Sequence[Transaction],
    category_map: dict[UUID, Category],
    as_of_date: date,
    history_days: int,
) -> list[RiskCandidate]:
    """Category spend this period > 130% of trailing-3-period average."""
    if history_days < 30:
        return []

    # Current period = most recent 30 days
    period_start = as_of_date - timedelta(days=29)
    current: dict[str, Decimal] = {}
    for txn in transactions:
        if (
            txn.direction == "debit"
            and txn.txn_date >= period_start
            and txn.category_id in category_map
            and category_map[txn.category_id].type in ("variable", "discretionary")
        ):
            cat_name = category_map[txn.category_id].name
            current[cat_name] = current.get(cat_name, ZERO) + txn.amount

    if not current:
        return []

    # Trailing 3-period average (periods 1-3 months ago)
    averages: dict[str, Decimal] = {}
    num_periods = min(3, history_days // 30)
    for cat_name in current:
        period_totals = []
        for offset in range(1, num_periods + 1):
            p_end = as_of_date - timedelta(days=offset * 30)
            p_start = p_end - timedelta(days=29)
            total = sum(
                (
                    txn.amount
                    for txn in transactions
                    if txn.direction == "debit"
                    and p_start <= txn.txn_date <= p_end
                    and txn.category_id in category_map
                    and category_map[txn.category_id].name == cat_name
                ),
                ZERO,
            )
            period_totals.append(total)
        if period_totals:
            averages[cat_name] = sum(period_totals, ZERO) / Decimal(len(period_totals))

    spike_threshold = Decimal("1") + config.SPENDING_SPIKE_PCT / Decimal("100")
    candidates = []
    for cat_name, current_amount in current.items():
        avg = averages.get(cat_name, ZERO)
        if avg <= ZERO:
            continue
        ratio = current_amount / avg
        if ratio > spike_threshold:
            confidence = Decimal("0.75") if history_days >= 60 else Decimal("0.55")
            candidates.append(
                RiskCandidate(
                    risk_type="unusually_high_spending",
                    severity="medium",
                    evidence={
                        "category": cat_name,
                        "current_period_amount": f"{_quantize(current_amount):.2f}",
                        "trailing_average": f"{_quantize(avg):.2f}",
                        "ratio_pct": f"{_quantize((ratio - Decimal('1')) * Decimal('100')):.1f}%",
                    },
                    confidence=_quantize(confidence),
                    dedup_key=f"unusually_high_spending:{cat_name}",
                )
            )
    return candidates


# ---------------------------------------------------------------------------
# Rule 4: Recurring payment burden
# ---------------------------------------------------------------------------


def rule_recurring_payment_burden(
    recurring: Sequence[RecurringTransaction],
    loans: Sequence[Loan],
    income_sources: Sequence[IncomeSource],
    transactions: Sequence[Transaction],
    category_map: dict[UUID, Category],
) -> RiskCandidate | None:
    """recurring_burden_pct > 50% of monthly income."""
    monthly_income = _estimate_monthly_income(income_sources, transactions, category_map)
    if monthly_income <= ZERO:
        return None

    monthly_recurring = _monthly_recurring_total(recurring, loans)
    burden_pct = monthly_recurring / monthly_income * Decimal("100")

    threshold = config.RECURRING_BURDEN_PCT
    if burden_pct <= threshold:
        return None

    obligations = []
    for item in recurring:
        if item.status == "confirmed":
            obligations.append(
                {
                    "description": f"Recurring ({item.frequency})",
                    "monthly_amount": f"{_quantize(_monthly_obligation(item)):.2f}",
                }
            )
    for loan in loans:
        obligations.append(
            {
                "description": "Loan EMI",
                "monthly_amount": f"{_quantize(loan.monthly_installment):.2f}",
            }
        )

    return RiskCandidate(
        risk_type="recurring_payment_burden",
        severity="medium",
        evidence={
            "recurring_burden_pct": f"{_quantize(burden_pct):.2f}%",
            "monthly_recurring_total": f"{_quantize(monthly_recurring):.2f}",
            "monthly_income": f"{_quantize(monthly_income):.2f}",
            "obligations": obligations,
        },
        confidence=_quantize(Decimal("0.88")),
        dedup_key="recurring_payment_burden",
    )


def _monthly_obligation(item: RecurringTransaction) -> Decimal:
    multipliers = {
        "weekly": Decimal("52") / Decimal("12"),
        "biweekly": Decimal("26") / Decimal("12"),
        "monthly": Decimal("1"),
        "quarterly": Decimal("1") / Decimal("3"),
        "yearly": Decimal("1") / Decimal("12"),
        "annual": Decimal("1") / Decimal("12"),
    }
    return item.expected_amount * multipliers.get(item.frequency.lower(), ZERO)


def _monthly_recurring_total(
    recurring: Sequence[RecurringTransaction],
    loans: Sequence[Loan],
) -> Decimal:
    from_recurring = sum((_monthly_obligation(r) for r in recurring if r.status == "confirmed"), ZERO)
    from_loans = sum((loan.monthly_installment for loan in loans), ZERO)
    return from_recurring + from_loans


def _estimate_monthly_income(
    income_sources: Sequence[IncomeSource],
    transactions: Sequence[Transaction],
    category_map: dict[UUID, Category],
) -> Decimal:
    if income_sources:
        monthly = ZERO
        for s in income_sources:
            if s.frequency == "monthly":
                monthly += s.amount
            elif s.frequency == "biweekly":
                monthly += s.amount * Decimal("26") / Decimal("12")
            else:
                monthly += s.amount
        return monthly
    # Fallback: sum income-category transactions over last 30 days
    income_total = sum(
        (
            txn.amount
            for txn in transactions
            if txn.direction == "credit"
            and txn.category_id in category_map
            and category_map[txn.category_id].type == "income"
        ),
        ZERO,
    )
    return income_total


# ---------------------------------------------------------------------------
# Rule 5: Debt pressure
# ---------------------------------------------------------------------------


def rule_debt_pressure(
    loans: Sequence[Loan],
    credit_cards: Sequence[CreditCard],
    income_sources: Sequence[IncomeSource],
    transactions: Sequence[Transaction],
    category_map: dict[UUID, Category],
) -> RiskCandidate | None:
    """debt_service_ratio > 40% OR credit_utilization > 70%."""
    monthly_income = _estimate_monthly_income(income_sources, transactions, category_map)

    monthly_debt = sum((loan.monthly_installment for loan in loans), ZERO) + sum(
        (cc.minimum_due for cc in credit_cards), ZERO
    )
    debt_service_ratio = monthly_debt / monthly_income * Decimal("100") if monthly_income > ZERO else ZERO

    total_limit = sum((cc.credit_limit for cc in credit_cards), ZERO)
    total_balance = sum((cc.current_balance for cc in credit_cards), ZERO)
    credit_util = total_balance / total_limit * Decimal("100") if total_limit > ZERO else ZERO

    dsr_breach = debt_service_ratio > config.DEBT_SERVICE_RATIO_HIGH
    util_breach = credit_util > config.CREDIT_UTILIZATION_HIGH

    if not dsr_breach and not util_breach:
        return None

    severity: Literal["high", "medium"] = "high"
    evidence: dict = {
        "debt_service_ratio_pct": f"{_quantize(debt_service_ratio):.2f}%",
        "credit_utilization_pct": f"{_quantize(credit_util):.2f}%",
        "monthly_debt_payments": f"{_quantize(monthly_debt):.2f}",
        "monthly_income": f"{_quantize(monthly_income):.2f}",
        "triggers": [],
    }
    if dsr_breach:
        evidence["triggers"].append(  # type: ignore[union-attr]
            f"Debt service ratio {_quantize(debt_service_ratio):.1f}% > {config.DEBT_SERVICE_RATIO_HIGH}% threshold"
        )
    if util_breach:
        evidence["triggers"].append(  # type: ignore[union-attr]
            f"Credit utilization {_quantize(credit_util):.1f}% > {config.CREDIT_UTILIZATION_HIGH}% threshold"
        )

    return RiskCandidate(
        risk_type="debt_pressure",
        severity=severity,
        evidence=evidence,
        confidence=_quantize(Decimal("0.92")),
        dedup_key="debt_pressure",
    )


# ---------------------------------------------------------------------------
# Rule 6: Income volatility
# ---------------------------------------------------------------------------


def rule_income_volatility(
    transactions: Sequence[Transaction],
    category_map: dict[UUID, Category],
    as_of_date: date,
) -> RiskCandidate | None:
    """income_cv > 0.3 over >= 3 periods."""
    # Collect monthly income totals (up to last 6 months)
    monthly_totals = []
    for offset in range(6):
        p_end = as_of_date - timedelta(days=offset * 30)
        p_start = p_end - timedelta(days=29)
        total = sum(
            (
                txn.amount
                for txn in transactions
                if txn.direction == "credit"
                and p_start <= txn.txn_date <= p_end
                and txn.category_id in category_map
                and category_map[txn.category_id].type == "income"
            ),
            ZERO,
        )
        if total > ZERO:
            monthly_totals.append(total)

    if len(monthly_totals) < config.MIN_PERIODS_FOR_VOLATILITY:
        return None  # Not enough data; suppressed per spec

    cv = _coefficient_of_variation(monthly_totals)
    if cv <= config.INCOME_CV_HIGH:
        return None

    return RiskCandidate(
        risk_type="income_volatility",
        severity="medium",
        evidence={
            "income_cv": f"{_quantize(cv):.4f}",
            "periods_analysed": len(monthly_totals),
            "monthly_income_series": [f"{_quantize(v):.2f}" for v in monthly_totals],
        },
        confidence=_quantize(Decimal("0.70")),
        dedup_key="income_volatility",
    )


# ---------------------------------------------------------------------------
# Rule 7: Unusual transaction
# ---------------------------------------------------------------------------


def rule_unusual_transactions(
    transactions: Sequence[Transaction],
    category_map: dict[UUID, Category],
    as_of_date: date,
    lookback_days: int = 90,
) -> list[RiskCandidate]:
    """Single transaction > 3× category average transaction size."""
    window_start = as_of_date - timedelta(days=lookback_days - 1)
    window_txns = [t for t in transactions if t.txn_date >= window_start and t.direction == "debit"]

    if not window_txns:
        return []

    # Build per-category average transaction size
    cat_txns: dict[str, list[Decimal]] = {}
    for txn in window_txns:
        if txn.category_id in category_map and category_map[txn.category_id].type != "transfer":
            name = category_map[txn.category_id].name
            cat_txns.setdefault(name, []).append(txn.amount)

    cat_avg: dict[str, Decimal] = {
        name: sum(amounts, ZERO) / Decimal(len(amounts)) for name, amounts in cat_txns.items() if amounts
    }

    # Scan recent transactions (last 30 days) for spikes
    recent_start = as_of_date - timedelta(days=29)
    multiplier = config.UNUSUAL_TXN_MULTIPLIER
    candidates = []
    seen_txns: set[str] = set()
    for txn in transactions:
        if txn.txn_date < recent_start or txn.direction != "debit" or txn.category_id not in category_map:
            continue
        cat_name = category_map[txn.category_id].name
        avg = cat_avg.get(cat_name)
        if avg is None or avg <= ZERO:
            continue
        if txn.amount > avg * multiplier:
            key = f"unusual_transaction:{str(txn.id)}"
            if key in seen_txns:
                continue
            seen_txns.add(key)
            severity: Literal["low", "medium"] = "medium" if txn.amount > avg * Decimal("5") else "low"
            candidates.append(
                RiskCandidate(
                    risk_type="unusual_transaction",
                    severity=severity,
                    evidence={
                        "transaction_id": str(txn.id),
                        "txn_date": txn.txn_date.isoformat(),
                        "amount": f"{_quantize(txn.amount):.2f}",
                        "category": cat_name,
                        "category_avg_transaction": f"{_quantize(avg):.2f}",
                        "multiplier": f"{_quantize(txn.amount / avg):.2f}x",
                    },
                    confidence=_quantize(Decimal("0.92")),
                    dedup_key=key,
                )
            )
    return candidates


# ---------------------------------------------------------------------------
# Engine entry point
# ---------------------------------------------------------------------------


def run_risk_engine(
    accounts: Sequence[Account],
    transactions: Sequence[Transaction],
    category_map: dict[UUID, Category],
    recurring: Sequence[RecurringTransaction],
    income_sources: Sequence[IncomeSource],
    loans: Sequence[Loan],
    credit_cards: Sequence[CreditCard],
    forecast: ForecastResult,
    as_of_date: date,
    preferred_buffer_days: int,
) -> list[RiskCandidate]:
    """Run all risk rules and return deduplicated candidates ordered by severity."""
    history_days = forecast.history_days
    preferred_buffer = Decimal(str(preferred_buffer_days))

    candidates: list[RiskCandidate] = []
    seen_keys: set[str] = set()

    def add(c: RiskCandidate | None) -> None:
        if c is not None and c.dedup_key not in seen_keys:
            seen_keys.add(c.dedup_key)
            candidates.append(c)

    def add_list(cs: list[RiskCandidate]) -> None:
        for c in cs:
            add(c)

    add(rule_low_cash_buffer(accounts, transactions, category_map, history_days))
    add(rule_upcoming_cash_flow_gap(forecast, preferred_buffer))
    add_list(rule_unusually_high_spending(transactions, category_map, as_of_date, history_days))
    add(rule_recurring_payment_burden(recurring, loans, income_sources, transactions, category_map))
    add(rule_debt_pressure(loans, credit_cards, income_sources, transactions, category_map))
    add(rule_income_volatility(transactions, category_map, as_of_date))
    add_list(rule_unusual_transactions(transactions, category_map, as_of_date))

    severity_order = {"high": 0, "medium": 1, "low": 2}
    candidates.sort(key=lambda c: severity_order.get(c.severity, 3))
    return candidates
