from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Sequence
from uuid import UUID

from app.core import config
from app.db.models import Category, CreditCard, IncomeSource, RecurringTransaction, Transaction

TWO_PLACES = Decimal("0.01")
ONE_PLACE = Decimal("0.1")


def quantize_2(val: Decimal) -> Decimal:
    return val.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def quantize_1(val: Decimal) -> Decimal:
    return val.quantize(ONE_PLACE, rounding=ROUND_HALF_UP)


def calculate_total_income(
    transactions: Sequence[Transaction],
    category_map: dict[UUID, Category],
    income_sources: Sequence[IncomeSource] | None = None,
) -> Decimal:
    """total_income = Σ(credit transactions classified as income in period).
    Falls back to declared income sources if no credit income transactions in period.
    """
    total = Decimal("0.00")
    has_income_txns = False
    for txn in transactions:
        if txn.direction == "credit":
            cat = category_map.get(txn.category_id) if txn.category_id else None
            if cat and cat.type == "income":
                total += txn.amount
                has_income_txns = True

    if not has_income_txns and income_sources:
        for source in income_sources:
            if source.frequency == "monthly":
                total += source.amount
            elif source.frequency == "biweekly":
                total += source.amount * Decimal("26") / Decimal("12")
            else:
                total += source.amount

    return quantize_2(total)


def calculate_total_expenses(
    transactions: Sequence[Transaction],
    category_map: dict[UUID, Category],
) -> Decimal:
    """total_expenses = Σ(debit transactions in period, excluding transfers)."""
    total = Decimal("0.00")
    for txn in transactions:
        if txn.direction == "debit":
            cat = category_map.get(txn.category_id) if txn.category_id else None
            if cat and cat.type == "transfer":
                continue
            total += txn.amount
    return quantize_2(total)


def calculate_fixed_expenses(
    transactions: Sequence[Transaction],
    category_map: dict[UUID, Category],
) -> Decimal:
    """fixed_expenses = Σ(debit transactions where category.type = 'fixed')."""
    total = Decimal("0.00")
    for txn in transactions:
        if txn.direction == "debit":
            cat = category_map.get(txn.category_id) if txn.category_id else None
            if cat and cat.type == "fixed":
                total += txn.amount
    return quantize_2(total)


def calculate_variable_expenses(
    transactions: Sequence[Transaction],
    category_map: dict[UUID, Category],
) -> Decimal:
    """variable_expenses = Σ(debit transactions where category.type = 'variable')."""
    total = Decimal("0.00")
    for txn in transactions:
        if txn.direction == "debit":
            cat = category_map.get(txn.category_id) if txn.category_id else None
            if cat and cat.type == "variable":
                total += txn.amount
    return quantize_2(total)


def calculate_discretionary_expenses(
    transactions: Sequence[Transaction],
    category_map: dict[UUID, Category],
) -> Decimal:
    """discretionary_expenses = Σ(debit transactions where category.type = 'discretionary')."""
    total = Decimal("0.00")
    for txn in transactions:
        if txn.direction == "debit":
            cat = category_map.get(txn.category_id) if txn.category_id else None
            if cat and cat.type == "discretionary":
                total += txn.amount
    return quantize_2(total)


def calculate_savings(total_income: Decimal, total_expenses: Decimal) -> Decimal:
    """savings = total_income - total_expenses."""
    return quantize_2(total_income - total_expenses)


def calculate_savings_rate(total_income: Decimal, total_expenses: Decimal) -> Decimal:
    """savings_rate = savings / total_income * 100."""
    if total_income <= Decimal("0"):
        return Decimal("0.00")
    savings = total_income - total_expenses
    rate = (savings / total_income) * Decimal("100")
    return quantize_2(rate)


def calculate_expense_to_income(total_expenses: Decimal, total_income: Decimal) -> Decimal:
    """expense_to_income = total_expenses / total_income * 100."""
    if total_income <= Decimal("0"):
        return Decimal("0.00")
    return quantize_2((total_expenses / total_income) * Decimal("100"))


def calculate_debt_to_income(monthly_debt_payments: Decimal, monthly_income: Decimal) -> Decimal:
    """debt_to_income = total_monthly_debt_payments / total_monthly_income * 100."""
    if monthly_income <= Decimal("0"):
        return Decimal("0.00")
    return quantize_2((monthly_debt_payments / monthly_income) * Decimal("100"))


def calculate_debt_service_ratio(
    monthly_debt_payments: Decimal, monthly_take_home_income: Decimal
) -> Decimal:
    """debt_service_ratio = total_monthly_debt_payments / total_monthly_take_home_income * 100."""
    if monthly_take_home_income <= Decimal("0"):
        return Decimal("0.00")
    return quantize_2((monthly_debt_payments / monthly_take_home_income) * Decimal("100"))


def calculate_monthly_burn(total_expenses: Decimal, days_in_period: int) -> Decimal:
    """monthly_burn = total_expenses / number_of_days_in_period * 30."""
    if days_in_period <= 0:
        return Decimal("0.00")
    return quantize_2((total_expenses / Decimal(days_in_period)) * Decimal("30"))


def calculate_cash_buffer_days(
    current_liquid_balance: Decimal, average_daily_expense: Decimal
) -> Decimal | None:
    """cash_buffer_days = current_liquid_balance / average_daily_expense.
    average_daily_expense = trailing_30_day_expenses / 30.
    """
    if average_daily_expense <= Decimal("0"):
        return None
    return quantize_1(current_liquid_balance / average_daily_expense)


def calculate_emergency_fund_months(
    liquid_savings_balance: Decimal, average_monthly_expense: Decimal
) -> Decimal | None:
    """emergency_fund_months = liquid_savings_balance / average_monthly_expense."""
    if average_monthly_expense <= Decimal("0"):
        return None
    return quantize_1(liquid_savings_balance / average_monthly_expense)


def calculate_recurring_burden_pct(
    total_recurring_monthly_obligations: Decimal, total_monthly_income: Decimal
) -> Decimal:
    """recurring_burden_pct = total_recurring_monthly_obligations / total_monthly_income * 100."""
    if total_monthly_income <= Decimal("0"):
        return Decimal("0.00")
    return quantize_2((total_recurring_monthly_obligations / total_monthly_income) * Decimal("100"))


def calculate_credit_utilization(credit_cards: Sequence[CreditCard]) -> Decimal:
    """credit_utilization_pct = Σ current_credit_card_balance / Σ credit_limit * 100."""
    total_balance = Decimal("0.00")
    total_limit = Decimal("0.00")
    for card in credit_cards:
        total_balance += card.current_balance
        total_limit += card.credit_limit
    if total_limit <= Decimal("0"):
        return Decimal("0.00")
    return quantize_2((total_balance / total_limit) * Decimal("100"))


def calculate_coefficient_of_variation(values: Sequence[Decimal]) -> Decimal:
    """CV = stddev(values) / mean(values). Uses sample standard deviation."""
    if len(values) < 2:
        return Decimal("0.00")
    mean_val = sum(values, Decimal("0.00")) / Decimal(len(values))
    if mean_val == Decimal("0.00"):
        return Decimal("0.00")
    variance = sum(((value - mean_val) ** 2 for value in values), Decimal("0.00")) / Decimal(len(values) - 1)
    stddev = variance.sqrt()
    cv = stddev / mean_val
    return quantize_2(cv)


def calculate_income_volatility(monthly_incomes: Sequence[Decimal]) -> Decimal:
    return calculate_coefficient_of_variation(monthly_incomes)


def calculate_spending_volatility(monthly_discretionary_spends: Sequence[Decimal]) -> Decimal:
    return calculate_coefficient_of_variation(monthly_discretionary_spends)


def calculate_monthly_history(
    transactions: Sequence[Transaction],
    category_map: dict[UUID, Category],
    end_date: date,
    max_periods: int = 6,
) -> tuple[list[Decimal], list[Decimal]]:
    """Return aligned monthly income and discretionary-spend series.

    Months with transactions but no value for one of the metrics are represented
    by zero. Empty months between the first and last observed month are also kept,
    because skipping them would understate volatility for irregular earners.
    """
    if max_periods <= 0:
        return [], []

    eligible = [txn for txn in transactions if txn.txn_date <= end_date]
    if not eligible:
        return [], []

    end_index = end_date.year * 12 + end_date.month - 1
    first_txn = min(eligible, key=lambda txn: txn.txn_date).txn_date
    first_index = first_txn.year * 12 + first_txn.month - 1
    start_index = max(first_index, end_index - max_periods + 1)

    income_by_month: dict[int, Decimal] = defaultdict(lambda: Decimal("0.00"))
    discretionary_by_month: dict[int, Decimal] = defaultdict(lambda: Decimal("0.00"))
    for txn in eligible:
        month_index = txn.txn_date.year * 12 + txn.txn_date.month - 1
        if month_index < start_index:
            continue
        category = category_map.get(txn.category_id) if txn.category_id else None
        if txn.direction == "credit" and category and category.type == "income":
            income_by_month[month_index] += txn.amount
        elif txn.direction == "debit" and category and category.type == "discretionary":
            discretionary_by_month[month_index] += txn.amount

    month_indexes = range(start_index, end_index + 1)
    return (
        [quantize_2(income_by_month[index]) for index in month_indexes],
        [quantize_2(discretionary_by_month[index]) for index in month_indexes],
    )


def calculate_monthly_recurring_obligations(
    recurring_transactions: Sequence[RecurringTransaction],
) -> Decimal:
    """Normalize confirmed recurring obligations to a monthly amount."""
    frequency_multipliers = {
        "weekly": Decimal("52") / Decimal("12"),
        "biweekly": Decimal("26") / Decimal("12"),
        "monthly": Decimal("1"),
        "quarterly": Decimal("1") / Decimal("3"),
        "yearly": Decimal("1") / Decimal("12"),
        "annual": Decimal("1") / Decimal("12"),
    }
    total = Decimal("0.00")
    for recurring in recurring_transactions:
        if recurring.status != "confirmed":
            continue
        multiplier = frequency_multipliers.get(recurring.frequency.lower())
        if multiplier is not None:
            total += recurring.expected_amount * multiplier
    return quantize_2(total)


def calculate_health_score(
    savings_rate: Decimal,
    debt_to_income: Decimal,
    credit_utilization: Decimal,
    cash_buffer_days: Decimal | None,
    preferred_buffer_days: int = config.PREFERRED_BUFFER_DAYS,
    recurring_burden_pct: Decimal = Decimal("0.00"),
) -> int:
    """Transparent weighted composite financial health score (0-100).
    Weights:
      Savings Rate: 25%
      Debt to Income: 25%
      Credit Utilization: 15%
      Cash Buffer Days: 20%
      Recurring Burden: 15%
    """
    # 1. Savings Rate component (0-100)
    sr = float(savings_rate)
    if sr >= 30.0:
        savings_score = 100.0
    elif sr >= 20.0:
        savings_score = 70.0 + (sr - 20.0) * 3.0
    elif sr >= 0.0:
        savings_score = (sr / 20.0) * 70.0
    else:
        savings_score = max(0.0, 35.0 + sr * 2.0)

    # 2. Debt to Income component (0-100)
    dti = float(debt_to_income)
    if dti <= 0.0:
        dti_score = 100.0
    elif dti <= 20.0:
        dti_score = 90.0 + (20.0 - dti) * 0.5
    elif dti <= 36.0:
        dti_score = 75.0 + ((36.0 - dti) / 16.0) * 15.0
    elif dti <= 43.0:
        dti_score = 50.0 + ((43.0 - dti) / 7.0) * 25.0
    else:
        dti_score = max(0.0, 50.0 - (dti - 43.0) * 1.5)

    # 3. Credit Utilization component (0-100)
    cu = float(credit_utilization)
    if cu <= 0.0:
        cu_score = 100.0
    elif cu <= 30.0:
        cu_score = 85.0 + (30.0 - cu) * 0.5
    elif cu <= 70.0:
        cu_score = 50.0 + ((70.0 - cu) / 40.0) * 35.0
    else:
        cu_score = max(0.0, 50.0 - (cu - 70.0) * 1.5)

    # 4. Cash Buffer Days component (0-100)
    if cash_buffer_days is None:
        buffer_score = 50.0
    else:
        buf = float(cash_buffer_days)
        pref = float(preferred_buffer_days) if preferred_buffer_days > 0 else 7.0
        if buf >= 30.0:
            buffer_score = 100.0
        elif buf >= pref:
            buffer_score = 60.0 + ((buf - pref) / (30.0 - pref)) * 40.0
        else:
            buffer_score = (buf / pref) * 50.0

    # 5. Recurring Burden component (0-100)
    rb = float(recurring_burden_pct)
    if rb <= 30.0:
        burden_score = 100.0
    elif rb <= 50.0:
        burden_score = 50.0 + ((50.0 - rb) / 20.0) * 50.0
    else:
        burden_score = max(0.0, 50.0 - (rb - 50.0) * 1.5)

    weighted = (
        0.25 * savings_score + 0.25 * dti_score + 0.15 * cu_score + 0.20 * buffer_score + 0.15 * burden_score
    )
    return int(round(weighted))


def calculate_confidence_score(
    data_completeness: Decimal = Decimal("1.0"),
    data_freshness: Decimal = Decimal("1.0"),
    historical_consistency: Decimal = Decimal("1.0"),
    forecast_uncertainty: Decimal = Decimal("0.8"),
    observation_count_periods: int = 3,
) -> Decimal:
    """Return the transparent 0-1 confidence score from the design spec."""
    inputs = (
        data_completeness,
        data_freshness,
        historical_consistency,
        forecast_uncertainty,
    )
    if any(value < Decimal("0") or value > Decimal("1") for value in inputs):
        raise ValueError("confidence inputs must be between 0 and 1")
    if observation_count_periods < 0:
        raise ValueError("observation_count_periods must not be negative")
    obs_score = min(
        Decimal("1.0"), Decimal(observation_count_periods) / Decimal(config.OBSERVATION_COUNT_CAP_PERIODS)
    )
    score = (
        config.WEIGHT_DATA_COMPLETENESS * data_completeness
        + config.WEIGHT_DATA_FRESHNESS * data_freshness
        + config.WEIGHT_HISTORICAL_CONSISTENCY * historical_consistency
        + config.WEIGHT_FORECAST_UNCERTAINTY * forecast_uncertainty
        + config.WEIGHT_OBSERVATION_COUNT * obs_score
    )
    return score


def calculate_confidence(
    data_completeness: Decimal = Decimal("1.0"),
    data_freshness: Decimal = Decimal("1.0"),
    historical_consistency: Decimal = Decimal("1.0"),
    forecast_uncertainty: Decimal = Decimal("0.8"),
    observation_count_periods: int = 3,
) -> str:
    """Map the transparent confidence score to its documented label."""
    score = calculate_confidence_score(
        data_completeness=data_completeness,
        data_freshness=data_freshness,
        historical_consistency=historical_consistency,
        forecast_uncertainty=forecast_uncertainty,
        observation_count_periods=observation_count_periods,
    )
    if score >= config.CONFIDENCE_HIGH_MIN:
        return "high"
    elif score >= config.CONFIDENCE_MEDIUM_MIN:
        return "medium"
    return "low"


def calculate_spending_by_category(
    transactions: Sequence[Transaction],
    category_map: dict[UUID, Category],
) -> list[dict]:
    """Computes spend amount and percentage of total by category."""
    totals_by_cat_id: dict[UUID | None, Decimal] = {}
    total_debits = Decimal("0.00")

    for txn in transactions:
        if txn.direction == "debit":
            cat = category_map.get(txn.category_id) if txn.category_id else None
            if cat and cat.type == "transfer":
                continue
            total_debits += txn.amount
            totals_by_cat_id[txn.category_id] = (
                totals_by_cat_id.get(txn.category_id, Decimal("0.00")) + txn.amount
            )

    items = []
    for cat_id, amount in totals_by_cat_id.items():
        cat = category_map.get(cat_id) if cat_id else None
        name = cat.name if cat else "Uncategorized"
        cat_type = cat.type if cat else "variable"
        pct = (amount / total_debits * Decimal("100")) if total_debits > Decimal("0") else Decimal("0.00")
        items.append(
            {
                "name": name,
                "amount": str(quantize_2(amount)),
                "pct_of_total": str(quantize_2(pct)),
                "type": cat_type,
                "_raw_amount": amount,
            }
        )

    items.sort(key=lambda x: x["_raw_amount"], reverse=True)
    for it in items:
        del it["_raw_amount"]
    return items


def calculate_loan_amortization(
    principal: Decimal,
    interest_rate: Decimal,
    term_months: int,
    monthly_installment: Decimal,
    start_date: date,
) -> list[dict]:
    """Calculates loan amortization schedule for a given loan."""
    if principal <= 0 or interest_rate < 0 or term_months <= 0 or monthly_installment <= 0:
        raise ValueError("loan values must be positive and interest_rate must not be negative")
    schedule = []
    balance = principal
    monthly_rate = (interest_rate / Decimal("100")) / Decimal("12")
    cur_year = start_date.year
    cur_month = start_date.month

    for month_num in range(1, term_months + 1):
        # Calculate date for this installment
        installment_month = (cur_month + month_num - 1) % 12 + 1
        installment_year = cur_year + (cur_month + month_num - 1) // 12
        installment_date = date(installment_year, installment_month, min(start_date.day, 28))

        interest = balance * monthly_rate
        if month_num == term_months or monthly_installment >= balance + interest:
            # Final payment settles remaining balance
            principal_comp = balance
            interest_comp = interest
            balance = Decimal("0.00")
        else:
            interest_comp = interest
            principal_comp = monthly_installment - interest_comp
            balance = balance - principal_comp

        schedule.append(
            {
                "date": installment_date.isoformat(),
                "principal_component": str(quantize_2(principal_comp)),
                "interest_component": str(quantize_2(interest_comp)),
                "remaining_balance": str(quantize_2(max(Decimal("0.00"), balance))),
            }
        )
        if balance <= Decimal("0.00"):
            break

    return schedule
