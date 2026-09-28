"""Impact Simulation Engine implementing IMPACT_SIMULATION.md.

Every simulation is deterministic — runs the same forecasting engine with
a modified FinancialState and compares baseline vs proposed projections.
The LLM's only role (Phase 5) is parsing natural-language what-if into an
action object. Here we only handle the computation.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal
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
from app.forecast.service import ForecastResult, add_calendar_months, generate_forecast

ZERO = Decimal("0.00")
TWO = Decimal("0.01")


def _q(value: Decimal) -> Decimal:
    return value.quantize(TWO)


ActionType = Literal[
    "reduce_spending",
    "increase_savings",
    "extra_debt_payment",
    "delay_purchase",
    "modify_recurring",
    "change_income",
]


@dataclass
class SimulationAction:
    type: ActionType
    # reduce_spending
    category: str | None = None
    amount: Decimal | None = None
    period: str | None = None
    # increase_savings
    # (reuses amount)
    # extra_debt_payment
    loan_id: UUID | None = None
    account_id: UUID | None = None
    date_of_payment: date | None = None
    # delay_purchase
    original_date: date | None = None
    new_date: date | None = None
    # modify_recurring
    recurring_id: UUID | None = None
    new_amount: Decimal | None = None
    cancel: bool = False
    # change_income
    income_amount: Decimal | None = None
    income_percent: Decimal | None = None
    effective_date: date | None = None


@dataclass
class FinancialState:
    """Mutable snapshot of user financial state for simulation."""

    accounts: list[Account]
    transactions: list[Transaction]
    recurring: list[RecurringTransaction]
    income_sources: list[IncomeSource]
    category_map: dict[UUID, Category]
    loans: list[Loan]
    credit_cards: list[CreditCard]
    # Category-level rolling-avg overrides (for reduce_spending)
    category_spend_overrides: dict[str, Decimal] = field(default_factory=dict)
    extra_scheduled_outflows: list[tuple[date, Decimal]] = field(default_factory=list)
    extra_scheduled_inflows: list[tuple[date, Decimal]] = field(default_factory=list)
    savings_bucket: Decimal = ZERO
    income_multiplier: Decimal | None = None
    income_amount_override: Decimal | None = None
    income_effective_date: date | None = None


def _copy_state(state: FinancialState) -> FinancialState:
    """Shallow-copy the mutable parts of state for simulation."""
    return FinancialState(
        accounts=list(state.accounts),
        transactions=list(state.transactions),
        recurring=list(state.recurring),
        income_sources=list(state.income_sources),
        category_map=dict(state.category_map),
        loans=list(state.loans),
        credit_cards=list(state.credit_cards),
        category_spend_overrides=dict(state.category_spend_overrides),
        extra_scheduled_outflows=list(state.extra_scheduled_outflows),
        extra_scheduled_inflows=list(state.extra_scheduled_inflows),
        savings_bucket=state.savings_bucket,
        income_multiplier=state.income_multiplier,
        income_amount_override=state.income_amount_override,
        income_effective_date=state.income_effective_date,
    )


def _amortize_with_extra_payment(loan: Loan, extra_amount: Decimal) -> Loan:
    """Return a copy of the loan with reduced outstanding balance."""
    new_loan = copy.copy(loan)
    new_balance = max(ZERO, loan.outstanding_balance - extra_amount)
    new_loan.outstanding_balance = new_balance
    return new_loan


def apply_action(state: FinancialState, action: SimulationAction) -> FinancialState:
    """Pure function: apply one action to state, return a modified copy."""
    new_state = _copy_state(state)

    if action.type == "reduce_spending":
        if not action.category or action.amount is None or action.amount <= ZERO:
            raise ValueError("reduce_spending requires a category and positive amount")
        as_of = max(txn.txn_date for txn in state.transactions)
        recent_start = as_of - timedelta(days=29)
        current = sum(
            (
                txn.amount
                for txn in state.transactions
                if txn.direction == "debit"
                and txn.txn_date >= recent_start
                and txn.category_id in state.category_map
                and state.category_map[txn.category_id].name == action.category
            ),
            ZERO,
        )
        if current <= ZERO:
            raise ValueError(f"no recent spending found for category '{action.category}'")
        if action.amount > current:
            raise ValueError(f"amount ({action.amount}) exceeds recent {action.category} spend ({current})")
        new_state.category_spend_overrides[action.category] = current - action.amount

    elif action.type == "increase_savings":
        if action.amount is None or action.amount <= ZERO:
            raise ValueError("increase_savings requires a positive amount")
        new_state.savings_bucket += action.amount
        as_of = max(txn.txn_date for txn in state.transactions)
        for month_offset in range(1, 7):
            new_state.extra_scheduled_outflows.append(
                (add_calendar_months(as_of, month_offset), action.amount)
            )

    elif action.type == "extra_debt_payment":
        if action.amount is None or action.amount <= ZERO:
            raise ValueError("extra_debt_payment requires a positive amount")
        as_of = max(txn.txn_date for txn in state.transactions)
        payment_date = action.date_of_payment or as_of + timedelta(days=1)
        if payment_date <= as_of:
            raise ValueError("extra debt payment date must be after the latest transaction date")
        if action.loan_id:
            loan_to_update = next((loan for loan in new_state.loans if loan.id == action.loan_id), None)
            if loan_to_update is None:
                raise ValueError("loan not found")
            if action.amount > loan_to_update.outstanding_balance:
                raise ValueError("extra payment exceeds outstanding loan balance")
            updated = _amortize_with_extra_payment(loan_to_update, action.amount)
            new_state.loans = [updated if loan.id == loan_to_update.id else loan for loan in new_state.loans]
        elif action.account_id:
            card = next(
                (card for card in new_state.credit_cards if card.account_id == action.account_id),
                None,
            )
            if card is None:
                raise ValueError("credit card account not found")
            if action.amount > card.current_balance:
                raise ValueError("extra payment exceeds credit card balance")
            updated_card = copy.copy(card)
            updated_card.current_balance -= action.amount
            new_state.credit_cards = [
                updated_card if item.account_id == card.account_id else item
                for item in new_state.credit_cards
            ]
        else:
            raise ValueError("extra_debt_payment requires loan_id or account_id")
        new_state.extra_scheduled_outflows.append((payment_date, action.amount))

    elif action.type == "delay_purchase":
        if action.amount is None or action.amount <= ZERO or action.new_date is None:
            raise ValueError("delay_purchase requires a positive amount and new_date")
        as_of = max(txn.txn_date for txn in state.transactions)
        if action.new_date <= as_of:
            raise ValueError("new_date must be after the latest transaction date")
        if action.original_date:
            new_state.extra_scheduled_outflows = [
                o
                for o in new_state.extra_scheduled_outflows
                if not (o[0] == action.original_date and o[1] == action.amount)
            ]
        new_state.extra_scheduled_outflows.append((action.new_date, action.amount))

    elif action.type == "modify_recurring":
        if not action.recurring_id:
            raise ValueError("modify_recurring requires recurring_id")
        matching = next((r for r in new_state.recurring if r.id == action.recurring_id), None)
        if matching is None:
            raise ValueError("recurring transaction not found")
        if not action.cancel and (action.new_amount is None or action.new_amount <= ZERO):
            raise ValueError("modify_recurring requires cancel=true or a positive new_amount")
        if action.recurring_id:
            if action.cancel:
                new_state.recurring = [r for r in new_state.recurring if r.id != action.recurring_id]
            elif action.new_amount is not None:
                new_recurring = []
                for r in new_state.recurring:
                    if r.id == action.recurring_id:
                        updated = copy.copy(r)
                        updated.expected_amount = action.new_amount
                        new_recurring.append(updated)
                    else:
                        new_recurring.append(r)
                new_state.recurring = new_recurring

    elif action.type == "change_income":
        if not new_state.income_sources:
            raise ValueError("no income sources found")
        if action.income_percent is None and action.income_amount is None:
            raise ValueError("change_income requires amount or percent")
        if action.income_percent is not None and action.income_amount is not None:
            raise ValueError("change_income accepts either amount or percent, not both")
        if action.income_percent is not None:
            if action.income_percent <= Decimal("-100"):
                raise ValueError("income percent must be greater than -100")
            new_state.income_multiplier = Decimal("1") + action.income_percent / Decimal("100")
        elif action.income_amount is not None:
            if action.income_amount <= ZERO:
                raise ValueError("income amount must be positive")
            new_state.income_amount_override = action.income_amount
        as_of = max(txn.txn_date for txn in state.transactions)
        new_state.income_effective_date = action.effective_date or as_of + timedelta(days=1)

    return new_state


def _run_forecast_on_state(state: FinancialState, horizon_days: int) -> ForecastResult:
    """Run the canonical forecasting engine against a (possibly modified) state."""
    return generate_forecast(
        accounts=state.accounts,
        transactions=state.transactions,
        recurring=state.recurring,
        income_sources=state.income_sources,
        category_map=state.category_map,
        loans=state.loans,
        horizon_days=horizon_days,
        category_monthly_spend_overrides=state.category_spend_overrides,
        extra_scheduled_outflows=state.extra_scheduled_outflows,
        extra_scheduled_inflows=state.extra_scheduled_inflows,
        income_multiplier=state.income_multiplier,
        income_amount_override=state.income_amount_override,
        income_effective_date=state.income_effective_date,
        maximum_horizon_days=config.SIMULATION_HORIZON_MAX_DAYS,
    )


def _loan_summary(loans: list[Loan]) -> tuple[int | None, Decimal | None]:
    if not loans:
        return None, None
    max_months = 0
    total_interest = ZERO
    for loan in loans:
        balance = loan.outstanding_balance
        monthly_rate = loan.interest_rate / Decimal("1200")
        months = 0
        interest_paid = ZERO
        while balance > ZERO and months < 1200:
            interest = balance * monthly_rate
            principal = loan.monthly_installment - interest
            if principal <= ZERO:
                return None, None
            payment = min(balance + interest, loan.monthly_installment)
            principal = payment - interest
            balance = max(ZERO, balance - principal)
            interest_paid += interest
            months += 1
        max_months = max(max_months, months)
        total_interest += interest_paid
    return max_months, _q(total_interest)


def _summarize_forecast(result: ForecastResult, loans: list[Loan], savings_bucket: Decimal = ZERO) -> dict:
    """Produce a comparable summary dict from a ForecastResult."""
    balances = [p.projected_balance for p in result.daily_projection]
    min_balance = min(balances) if balances else ZERO
    month_end_balance = balances[-1] if balances else ZERO
    avg_daily = result.rolling_average_daily_spend * result.trend_factor
    min_buffer_days = min_balance / avg_daily if avg_daily > ZERO else Decimal("999")
    loan_payoff_months, total_interest_remaining = _loan_summary(loans)

    return {
        "projected_balance_series": [
            {"date": p.date.isoformat(), "balance": f"{p.projected_balance:.2f}"}
            for p in result.daily_projection
        ],
        "loan_payoff_months": loan_payoff_months,
        "total_interest_remaining": str(_q(total_interest_remaining)) if total_interest_remaining else None,
        "cash_buffer_days_min": str(_q(min_buffer_days)),
        "minimum_projected_balance": str(_q(min_balance)),
        "month_end_balance": str(_q(month_end_balance)),
        "savings_accumulated": str(_q(savings_bucket)),
        "affordability_status": "not_affordable" if min_balance < ZERO else "affordable",
        "confidence": result.confidence,
    }


def _compute_delta(baseline: dict, proposed: dict) -> dict:
    delta: dict = {}
    for key in ("loan_payoff_months",):
        b = baseline.get(key)
        p = proposed.get(key)
        if b is not None and p is not None:
            delta[key] = p - b

    for key in (
        "total_interest_remaining",
        "cash_buffer_days_min",
        "minimum_projected_balance",
        "month_end_balance",
        "savings_accumulated",
    ):
        b = baseline.get(key)
        p = proposed.get(key)
        if b is not None and p is not None:
            try:
                delta[key] = str(_q(Decimal(str(p)) - Decimal(str(b))))
            except Exception:
                pass
    return delta


def _trade_off_note(delta: dict, action: SimulationAction) -> str:
    notes = []
    buffer_delta_raw = delta.get("cash_buffer_days_min")
    if buffer_delta_raw is not None:
        try:
            bd = Decimal(str(buffer_delta_raw))
            if bd < ZERO:
                notes.append(f"Minimum cash buffer decreases by {abs(bd):.2f} day(s).")
        except Exception:
            pass
    payoff_delta = delta.get("loan_payoff_months")
    if payoff_delta is not None and payoff_delta < 0:
        notes.append(f"Loan payoff shortens by {abs(payoff_delta)} month(s).")
    interest_delta_raw = delta.get("total_interest_remaining")
    if interest_delta_raw is not None:
        try:
            id_ = Decimal(str(interest_delta_raw))
            if id_ < ZERO:
                notes.append(f"Total interest saved: ₹{abs(id_):,.2f}.")
        except Exception:
            pass
    if not notes:
        return "No significant trade-offs detected for this action."
    return " ".join(notes)


@dataclass
class SimulationResult:
    action: dict
    baseline: dict
    proposed: dict
    delta: dict
    confidence: str
    trade_off_note: str


def simulate_action(
    state: FinancialState, action: SimulationAction, horizon_days: int = 90
) -> SimulationResult:
    """Run the what-if simulation per IMPACT_SIMULATION.md pseudocode."""
    if not 1 <= horizon_days <= config.SIMULATION_HORIZON_MAX_DAYS:
        raise ValueError(f"horizon_days must be 1–{config.SIMULATION_HORIZON_MAX_DAYS}")

    if not state.transactions:
        raise ValueError("transactions are required to run a simulation")

    baseline_state = state
    if action.type == "delay_purchase" and action.original_date and action.amount is not None:
        baseline_state = _copy_state(state)
        baseline_state.extra_scheduled_outflows.append((action.original_date, action.amount))

    baseline_forecast = _run_forecast_on_state(baseline_state, horizon_days)
    modified_state = apply_action(baseline_state, action)
    proposed_forecast = _run_forecast_on_state(modified_state, horizon_days)

    baseline_summary = _summarize_forecast(
        baseline_forecast, baseline_state.loans, baseline_state.savings_bucket
    )
    proposed_summary = _summarize_forecast(
        proposed_forecast, modified_state.loans, modified_state.savings_bucket
    )
    delta = _compute_delta(baseline_summary, proposed_summary)

    confidence_order = {"high": 2, "medium": 1, "low": 0}
    combined_confidence = min(
        (baseline_forecast.confidence, proposed_forecast.confidence),
        key=lambda c: confidence_order.get(c, 0),
    )

    return SimulationResult(
        action={
            "type": action.type,
            "category": action.category,
            "amount": str(action.amount) if action.amount is not None else None,
            "loan_id": str(action.loan_id) if action.loan_id else None,
            "account_id": str(action.account_id) if action.account_id else None,
            "recurring_id": str(action.recurring_id) if action.recurring_id else None,
            "original_date": action.original_date.isoformat() if action.original_date else None,
            "new_date": action.new_date.isoformat() if action.new_date else None,
            "effective_date": action.effective_date.isoformat() if action.effective_date else None,
            "cancel": action.cancel if action.type == "modify_recurring" else None,
        },
        baseline=baseline_summary,
        proposed=proposed_summary,
        delta=delta,
        confidence=combined_confidence,
        trade_off_note=_trade_off_note(delta, action),
    )
