"""Owner-scoped adapters from the AI layer to the real Phase 1–4 services."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Callable
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.schemas import Intent
from app.analytics.repository import AnalyticsRepository
from app.analytics.router import (
    get_debt_summary as phase4_debt_summary,
)
from app.analytics.router import (
    get_financial_summary as phase4_financial_summary,
)
from app.analytics.router import (
    get_spending_by_category as phase4_spending_by_category,
)
from app.core import config
from app.core.errors import APIError
from app.db.models import Account, Category, Merchant, Transaction
from app.db.user import User
from app.forecast.router import get_cash_flow_forecast as phase4_cash_flow_forecast
from app.recommendations.router import get_recommendations as phase4_recommendations
from app.recurring.router import get_recurring_expenses as phase4_recurring_expenses
from app.risks.router import get_risks as phase4_risks
from app.simulation.router import affordability_check as phase4_affordability
from app.simulation.router import run_simulation as phase4_simulation
from app.simulation.schemas import AffordabilityRequest, SimulateRequest


class ToolError(ValueError):
    def __init__(self, code: str, message: str):
        self.code, self.message = code, message
        super().__init__(message)


class PeriodArgs(BaseModel):
    model_config = {"extra": "forbid"}
    start_date: date | None = None
    end_date: date | None = None

    @field_validator("end_date")
    @classmethod
    def valid_range(cls, value, info):
        start = info.data.get("start_date")
        if start and value and value < start:
            raise ValueError("end_date must be on or after start_date")
        return value


class TransactionsArgs(PeriodArgs):
    category: str | None = Field(default=None, max_length=80)
    merchant: str | None = Field(default=None, max_length=120)
    min_amount: Decimal | None = Field(default=None, gt=0)
    max_amount: Decimal | None = Field(default=None, gt=0)
    limit: int = Field(default=20, ge=1, le=100)


class ForecastArgs(BaseModel):
    model_config = {"extra": "forbid"}
    horizon_days: int = Field(
        default=config.FORECAST_HORIZON_DEFAULT_DAYS,
        ge=1,
        le=config.FORECAST_HORIZON_MAX_DAYS,
    )


class RiskStatusArgs(BaseModel):
    model_config = {"extra": "forbid"}
    status: str = Field(default="active", pattern="^(active|resolved|all)$")


class RecommendationStatusArgs(BaseModel):
    model_config = {"extra": "forbid"}
    status: str = Field(default="active", pattern="^(active|superseded|dismissed|all)$")


class RecurringArgs(BaseModel):
    model_config = {"extra": "forbid"}
    status: str = Field(default="all", pattern="^(confirmed|candidate|all)$")


class EmptyArgs(BaseModel):
    model_config = {"extra": "forbid"}


class AffordabilityArgs(BaseModel):
    model_config = {"extra": "forbid"}
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    target_date: date | None = None


class SimulationArgs(BaseModel):
    model_config = {"extra": "forbid"}
    action_type: str | None = Field(
        default=None,
        pattern="^(reduce_spending|increase_savings|extra_debt_payment|delay_purchase|modify_recurring|change_income)$",
    )
    params: dict[str, Any] = Field(default_factory=dict)
    horizon_days: int = Field(default=90, ge=1, le=config.SIMULATION_HORIZON_MAX_DAYS)


class ToolSpec:
    def __init__(self, name: str, description: str, args_model: type[BaseModel], fn: Callable):
        self.name, self.description, self.args_model, self.fn = name, description, args_model, fn

    def run(self, db: Session, user_id: UUID, raw_args: dict[str, Any]) -> dict[str, Any]:
        try:
            args = self.args_model.model_validate(raw_args)
        except ValidationError as exc:
            raise ToolError(
                "invalid_tool_arguments", "The financial question needs more or different details."
            ) from exc
        return self.fn(db, user_id, args)


def _user(db: Session, user_id: UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise ToolError("user_not_found", "The authenticated user was not found.")
    return user


def _dump(value: Any) -> dict[str, Any]:
    return value.model_dump(mode="json") if hasattr(value, "model_dump") else dict(value)


def _insufficient(reason: str, missing: list[str], **extra: Any) -> dict[str, Any]:
    return {"status": "insufficient_data", "reason": reason, "missing_information": missing, **extra}


def _service(call: Callable[[], Any], missing: list[str]) -> dict[str, Any]:
    try:
        payload = _dump(call())
        return {"status": "ok", **payload}
    except APIError as exc:
        if exc.status == 404 or exc.code in {"no_data", "no_debt_data"}:
            return _insufficient(exc.message, missing)
        return {"status": "error", "code": exc.code, "reason": exc.message}


def financial_summary(db: Session, user_id: UUID, args: PeriodArgs) -> dict[str, Any]:
    user = _user(db, user_id)
    return _service(
        lambda: phase4_financial_summary(args.start_date, args.end_date, user, db),
        ["transactions"],
    )


def spending_by_category(db: Session, user_id: UUID, args: PeriodArgs) -> dict[str, Any]:
    user = _user(db, user_id)
    return _service(
        lambda: phase4_spending_by_category(args.start_date, args.end_date, user, db),
        ["expense transactions"],
    )


def debt_summary(db: Session, user_id: UUID, _args: EmptyArgs) -> dict[str, Any]:
    user = _user(db, user_id)
    return _service(lambda: phase4_debt_summary(user, db), ["loan or credit-card data"])


def cash_flow_forecast(db: Session, user_id: UUID, args: ForecastArgs) -> dict[str, Any]:
    user = _user(db, user_id)
    return _service(
        lambda: phase4_cash_flow_forecast(args.horizon_days, user, db),
        ["transactions", "account balances", "income or recurring obligations"],
    )


def recurring_expenses(db: Session, user_id: UUID, args: RecurringArgs) -> dict[str, Any]:
    user = _user(db, user_id)
    result = _service(lambda: phase4_recurring_expenses(user, db), ["transaction history"])
    if result.get("status") == "ok" and args.status != "all":
        result["recurring"] = [row for row in result["recurring"] if row["status"] == args.status]
    return result


def transactions(db: Session, user_id: UUID, args: TransactionsArgs) -> dict[str, Any]:
    query = (
        select(Transaction, Category.name, Merchant.normalized_name)
        .join(Account, Account.id == Transaction.account_id)
        .outerjoin(Category, Category.id == Transaction.category_id)
        .outerjoin(Merchant, Merchant.id == Transaction.merchant_id)
        .where(Account.user_id == user_id)
    )
    if args.start_date:
        query = query.where(Transaction.txn_date >= args.start_date)
    if args.end_date:
        query = query.where(Transaction.txn_date <= args.end_date)
    if args.category:
        query = query.where(func.lower(Category.name) == args.category.lower())
    if args.merchant:
        query = query.where(func.lower(Merchant.normalized_name).contains(args.merchant.lower()))
    if args.min_amount is not None:
        query = query.where(Transaction.amount >= args.min_amount)
    if args.max_amount is not None:
        query = query.where(Transaction.amount <= args.max_amount)
    rows = db.execute(query.order_by(Transaction.txn_date.desc()).limit(args.limit)).all()
    return {
        "status": "ok",
        "count": len(rows),
        "transactions": [
            {
                "date": txn.txn_date.isoformat(),
                "amount": f"{txn.amount:.2f}",
                "direction": txn.direction,
                "merchant": merchant or txn.raw_description,
                "category": category or "Uncategorized",
            }
            for txn, category, merchant in rows
        ],
    }


def risk_events(db: Session, user_id: UUID, args: RiskStatusArgs) -> dict[str, Any]:
    user = _user(db, user_id)
    result = _service(lambda: phase4_risks(args.status, user, db), ["transactions"])
    if result.get("status") == "ok" and not result.get("risks"):
        result["summary"] = "No matching risk events were detected."
    return result


def recommendations(db: Session, user_id: UUID, args: RecommendationStatusArgs) -> dict[str, Any]:
    user = _user(db, user_id)
    result = _service(lambda: phase4_recommendations(args.status, user, db), ["transactions"])
    if result.get("status") == "ok" and not result.get("recommendations"):
        result["summary"] = "No matching recommendations were generated."
    return result


def _latest_transaction_date(db: Session, user_id: UUID) -> date | None:
    return db.scalar(
        select(func.max(Transaction.txn_date))
        .join(Account, Account.id == Transaction.account_id)
        .where(Account.user_id == user_id)
    )


def affordability(db: Session, user_id: UUID, args: AffordabilityArgs) -> dict[str, Any]:
    user = _user(db, user_id)
    target = args.target_date or ((_latest_transaction_date(db, user_id) or date.today()) + timedelta(days=7))
    return _service(
        lambda: phase4_affordability(
            AffordabilityRequest(amount=str(args.amount), target_date=target), user, db
        ),
        ["transactions", "account balances", "purchase date"],
    )


def simulate_action(db: Session, user_id: UUID, args: SimulationArgs) -> dict[str, Any]:
    user = _user(db, user_id)
    if args.action_type is None:
        return _insufficient(
            "Please describe the change you want to simulate.",
            ["action type and amount"],
        )
    params = dict(args.params)
    if args.action_type == "extra_debt_payment" and not (params.get("loan_id") or params.get("account_id")):
        loans = AnalyticsRepository(db).get_loans(user_id)
        if len(loans) != 1:
            return _insufficient(
                "Please specify which debt should receive the extra payment.",
                ["loan or card selection"],
            )
        params["loan_id"] = str(loans[0].id)
    if args.action_type == "modify_recurring" and not params.get("recurring_id"):
        recurring = _dump(phase4_recurring_expenses(user, db)).get("recurring", [])
        if len(recurring) != 1:
            return _insufficient(
                "Please specify which recurring payment should be changed.",
                ["recurring payment selection"],
            )
        params["recurring_id"] = recurring[0]["id"]
    return _service(
        lambda: phase4_simulation(
            SimulateRequest(
                action_type=args.action_type,
                params=params,
                horizon_days=args.horizon_days,
            ),
            user,
            db,
        ),
        ["transactions", "account balances", "complete action details"],
    )


TOOL_SPECS: dict[str, ToolSpec] = {
    "get_financial_summary": ToolSpec(
        "get_financial_summary",
        "Return the canonical Phase 2 financial summary.",
        PeriodArgs,
        financial_summary,
    ),
    "get_transactions": ToolSpec(
        "get_transactions",
        "Return owner-scoped transactions matching safe filters.",
        TransactionsArgs,
        transactions,
    ),
    "get_spending_by_category": ToolSpec(
        "get_spending_by_category",
        "Return canonical Phase 2 spending by category.",
        PeriodArgs,
        spending_by_category,
    ),
    "get_recurring_expenses": ToolSpec(
        "get_recurring_expenses",
        "Run and return Phase 3 recurring detection.",
        RecurringArgs,
        recurring_expenses,
    ),
    "get_debt_summary": ToolSpec(
        "get_debt_summary", "Return the canonical Phase 2 debt summary.", EmptyArgs, debt_summary
    ),
    "get_cash_flow_forecast": ToolSpec(
        "get_cash_flow_forecast", "Run the canonical Phase 3 forecast.", ForecastArgs, cash_flow_forecast
    ),
    "get_risk_events": ToolSpec(
        "get_risk_events", "Run the Phase 4 risk engine.", RiskStatusArgs, risk_events
    ),
    "calculate_affordability": ToolSpec(
        "calculate_affordability",
        "Run the Phase 4 affordability simulation.",
        AffordabilityArgs,
        affordability,
    ),
    "simulate_action": ToolSpec(
        "simulate_action",
        "Run a typed action through the Phase 4 simulation engine.",
        SimulationArgs,
        simulate_action,
    ),
    "get_recommendations": ToolSpec(
        "get_recommendations",
        "Run the Phase 4 recommendation pipeline.",
        RecommendationStatusArgs,
        recommendations,
    ),
}


INTENT_TOOLS: dict[Intent, list[str]] = {
    Intent.SPENDING: ["get_spending_by_category"],
    Intent.SAVINGS: ["get_financial_summary"],
    Intent.DEBT: ["get_debt_summary"],
    Intent.CASH_FLOW: ["get_cash_flow_forecast"],
    Intent.AFFORDABILITY: ["calculate_affordability"],
    Intent.RECOMMENDATION: ["get_recommendations"],
    Intent.WHAT_IF: ["simulate_action"],
    Intent.RISK: ["get_risk_events"],
    Intent.GENERAL: ["get_financial_summary", "get_risk_events"],
    Intent.UNCLEAR: ["get_financial_summary", "get_risk_events"],
}
