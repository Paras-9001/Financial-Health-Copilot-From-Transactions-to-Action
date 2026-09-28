from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.analytics.repository import AnalyticsRepository
from app.core.database import get_db
from app.core.errors import APIError
from app.core.security import current_user
from app.db.user import User
from app.forecast.service import generate_forecast
from app.recurring.service import detect_and_persist_recurring
from app.simulation.schemas import (
    AffordabilityRequest,
    AffordabilityResponse,
    SimulateRequest,
    SimulateResponse,
)
from app.simulation.service import (
    FinancialState,
    SimulationAction,
    simulate_action,
)

router = APIRouter(tags=["Simulation"])

ZERO = Decimal("0.00")
TWO = Decimal("0.01")


def _build_state(user: User, db: Session) -> tuple[FinancialState, int]:
    """Load all financial data and return a FinancialState + history_days."""
    analytics = AnalyticsRepository(db)
    transactions = analytics.get_user_transactions(user.id)
    if not transactions:
        raise APIError(404, "no_data", "No transactions found for user")

    category_map = analytics.get_categories_map()
    detect_and_persist_recurring(db, user.id, transactions, category_map)
    recurring = analytics.get_recurring_transactions(user.id)
    accounts = analytics.get_accounts(user.id)
    income_sources = analytics.get_income_sources(user.id)
    loans = analytics.get_loans(user.id)
    credit_cards = analytics.get_credit_cards(user.id)

    # Run forecast to get history_days
    forecast = generate_forecast(
        accounts=accounts,
        transactions=transactions,
        recurring=recurring,
        income_sources=income_sources,
        category_map=category_map,
        loans=loans,
    )

    state = FinancialState(
        accounts=accounts,
        transactions=transactions,
        recurring=recurring,
        income_sources=income_sources,
        category_map=category_map,
        loans=loans,
        credit_cards=credit_cards,
    )
    return state, forecast.history_days


def _parse_action(action_type: str, params: dict) -> SimulationAction:
    """Parse the request params into a SimulationAction, with validation."""
    try:
        amount = Decimal(str(params["amount"])) if "amount" in params else None
    except (InvalidOperation, TypeError):
        raise APIError(422, "invalid_action", "amount must be a valid number")

    if action_type == "reduce_spending":
        if not params.get("category"):
            raise APIError(422, "invalid_action", "reduce_spending requires 'category'")
        if amount is None or amount <= ZERO:
            raise APIError(422, "invalid_action", "reduce_spending requires positive 'amount'")
        return SimulationAction(type="reduce_spending", category=params["category"], amount=amount)

    if action_type == "increase_savings":
        if amount is None or amount <= ZERO:
            raise APIError(422, "invalid_action", "increase_savings requires positive 'amount'")
        return SimulationAction(type="increase_savings", amount=amount)

    if action_type == "extra_debt_payment":
        if amount is None or amount <= ZERO:
            raise APIError(422, "invalid_action", "extra_debt_payment requires positive 'amount'")
        try:
            loan_id = UUID(params["loan_id"]) if params.get("loan_id") else None
            account_id = UUID(params["account_id"]) if params.get("account_id") else None
            payment_date = date.fromisoformat(params["date"]) if params.get("date") else None
        except (ValueError, TypeError) as exc:
            raise APIError(422, "invalid_action", "loan_id/account_id/date is invalid") from exc
        if loan_id is None and account_id is None:
            raise APIError(
                422,
                "invalid_action",
                "extra_debt_payment requires 'loan_id' or 'account_id'",
            )
        return SimulationAction(
            type="extra_debt_payment",
            loan_id=loan_id,
            account_id=account_id,
            amount=amount,
            date_of_payment=payment_date,
        )

    if action_type == "delay_purchase":
        if amount is None or amount <= ZERO:
            raise APIError(422, "invalid_action", "delay_purchase requires positive 'amount'")
        try:
            orig = date.fromisoformat(params["original_date"]) if params.get("original_date") else None
            new = date.fromisoformat(params["new_date"]) if params.get("new_date") else None
        except (ValueError, TypeError) as exc:
            raise APIError(422, "invalid_action", "purchase dates must use YYYY-MM-DD") from exc
        if new is None:
            raise APIError(422, "invalid_action", "delay_purchase requires 'new_date'")
        return SimulationAction(type="delay_purchase", amount=amount, original_date=orig, new_date=new)

    if action_type == "modify_recurring":
        try:
            recurring_id = UUID(params["recurring_id"]) if params.get("recurring_id") else None
        except (ValueError, TypeError) as exc:
            raise APIError(422, "invalid_action", "recurring_id is invalid") from exc
        if recurring_id is None:
            raise APIError(422, "invalid_action", "modify_recurring requires 'recurring_id'")
        cancel = params.get("cancel", False)
        if not isinstance(cancel, bool):
            raise APIError(422, "invalid_action", "cancel must be a boolean")
        try:
            new_amount = Decimal(str(params["new_amount"])) if params.get("new_amount") else None
        except (InvalidOperation, TypeError) as exc:
            raise APIError(422, "invalid_action", "new_amount must be a valid number") from exc
        if not cancel and (new_amount is None or new_amount <= ZERO):
            raise APIError(
                422,
                "invalid_action",
                "modify_recurring requires cancel=true or positive 'new_amount'",
            )
        return SimulationAction(
            type="modify_recurring",
            recurring_id=recurring_id,
            cancel=cancel,
            new_amount=new_amount,
        )

    if action_type == "change_income":
        try:
            income_pct = Decimal(str(params["percent"])) if "percent" in params else None
            income_amt = Decimal(str(params["amount"])) if "amount" in params else None
            effective = date.fromisoformat(params["effective_date"]) if params.get("effective_date") else None
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise APIError(422, "invalid_action", "income parameters are invalid") from exc
        if (income_pct is None) == (income_amt is None):
            raise APIError(422, "invalid_action", "provide exactly one of 'percent' or 'amount'")
        return SimulationAction(
            type="change_income",
            income_percent=income_pct,
            income_amount=income_amt,
            effective_date=effective,
        )

    raise APIError(422, "invalid_action", f"Unknown action_type: {action_type}")


@router.post("/simulate", response_model=SimulateResponse)
def run_simulation(
    request: SimulateRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Run a what-if simulation and return baseline vs. proposed comparison."""
    state, _ = _build_state(user, db)
    action = _parse_action(request.action_type, request.params)

    # Validate extra_debt_payment against actual loan balance
    if action.type == "extra_debt_payment" and action.loan_id and action.amount:
        loan = next((item for item in state.loans if item.id == action.loan_id), None)
        if loan is None:
            raise APIError(404, "loan_not_found", "Loan not found for this user")
        if action.amount > loan.outstanding_balance:
            raise APIError(
                422,
                "invalid_action",
                f"amount ({action.amount}) exceeds outstanding loan balance ({loan.outstanding_balance})",
            )

    if action.type == "extra_debt_payment" and action.account_id and action.amount:
        card = next(
            (item for item in state.credit_cards if item.account_id == action.account_id),
            None,
        )
        if card is None:
            raise APIError(404, "credit_card_not_found", "Credit card not found for this user")
        if action.amount > card.current_balance:
            raise APIError(422, "invalid_action", "amount exceeds credit card balance")

    try:
        result = simulate_action(state, action, horizon_days=request.horizon_days)
    except ValueError as exc:
        raise APIError(422, "invalid_action", str(exc)) from exc

    return SimulateResponse(
        action=result.action,
        baseline=result.baseline,
        proposed=result.proposed,
        delta=result.delta,
        confidence=result.confidence,
        trade_off_note=result.trade_off_note,
    )


@router.post("/affordability/check", response_model=AffordabilityResponse)
def affordability_check(
    request: AffordabilityRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Check whether a one-off purchase is affordable by simulating it as a delay_purchase."""
    try:
        amount = Decimal(str(request.amount))
    except (InvalidOperation, TypeError):
        raise APIError(422, "invalid_amount", "amount must be a valid number")

    if amount <= ZERO:
        raise APIError(422, "invalid_amount", "amount must be positive")

    state, history_days = _build_state(user, db)

    action = SimulationAction(
        type="delay_purchase",
        amount=amount,
        original_date=None,
        new_date=request.target_date,
    )

    try:
        result = simulate_action(state, action)
    except ValueError as exc:
        raise APIError(422, "invalid_action", str(exc)) from exc

    proposed_buffer_str = result.proposed.get("cash_buffer_days_min", "0")
    try:
        proposed_buffer = Decimal(str(proposed_buffer_str))
    except InvalidOperation:
        proposed_buffer = ZERO

    preferred = Decimal(str(user.preferred_buffer_days))
    if proposed_buffer < ZERO:
        verdict = "not_affordable"
    elif proposed_buffer < preferred:
        verdict = "caution"
    else:
        verdict = "affordable"

    return AffordabilityResponse(
        verdict=verdict,
        resulting_buffer_days=f"{proposed_buffer:.2f}",
        confidence=result.confidence,
        reasoning_basis=[
            f"Purchase of ₹{amount:,.2f} scheduled on {request.target_date}.",
            f"Projected minimum cash balance after purchase: ₹{result.proposed.get('minimum_projected_balance', '?')}.",
            f"Preferred buffer: {user.preferred_buffer_days} days.",
            result.trade_off_note,
        ],
    )
