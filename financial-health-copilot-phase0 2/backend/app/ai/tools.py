"""Allowlisted deterministic data tools used by the chat orchestrator.

The tools receive an authenticated database session, never a model-supplied
user_id. They return JSON-safe values and an explicit status for incomplete
data. Phase 1-4 services can replace the query implementations behind these
stable names without changing the agent contract.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Callable
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.ai.schemas import Intent
from app.core import config


class ToolError(ValueError):
    def __init__(self, code: str, message: str):
        self.code, self.message = code, message
        super().__init__(message)


class PeriodArgs(BaseModel):
    start_date: date | None = None
    end_date: date | None = None

    @field_validator("end_date")
    @classmethod
    def valid_range(cls, value, info):
        start = info.data.get("start_date")
        if start and value < start:
            raise ValueError("end_date must be on or after start_date")
        return value


class TransactionsArgs(PeriodArgs):
    category: str | None = Field(default=None, max_length=80)
    merchant: str | None = Field(default=None, max_length=120)
    min_amount: Decimal | None = Field(default=None, gt=0)
    max_amount: Decimal | None = Field(default=None, gt=0)
    limit: int = Field(default=20, ge=1, le=100)


class ForecastArgs(BaseModel):
    horizon_days: int = Field(
        default=config.FORECAST_HORIZON_DEFAULT_DAYS, ge=1, le=config.FORECAST_HORIZON_MAX_DAYS
    )


class StatusArgs(BaseModel):
    status: str = Field(default="active", pattern="^(active|resolved|confirmed|candidate|all)$")


class EmptyArgs(BaseModel):
    """Explicit empty argument object; abstract BaseModel cannot be instantiated."""

    model_config = {"extra": "forbid"}


class AffordabilityArgs(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    target_date: date | None = None


class SimulationArgs(BaseModel):
    action_type: str = Field(min_length=1, max_length=60)
    params: dict[str, Any] = Field(default_factory=dict)


class ToolSpec:
    def __init__(self, name: str, description: str, args_model: type[BaseModel], fn: Callable):
        self.name, self.description, self.args_model, self.fn = name, description, args_model, fn

    def run(self, db: Session, user_id: UUID, raw_args: dict[str, Any]) -> dict[str, Any]:
        try:
            args = self.args_model.model_validate(raw_args)
        except ValidationError as exc:
            raise ToolError(
                "invalid_tool_arguments", "The requested financial query has invalid arguments."
            ) from exc
        return self.fn(db, user_id, args)


def _json_money(value: Decimal | int | float | None) -> str | None:
    if value is None:
        return None
    return f"{Decimal(str(value)).quantize(Decimal('0.01')):.2f}"


def _period(args: PeriodArgs) -> tuple[date, date]:
    end = args.end_date or date.today()
    start = args.start_date or end - timedelta(days=29)
    if (end - start).days > 366:
        raise ToolError("period_too_large", "Choose a period of at most 366 days.")
    return start, end


def _insufficient(reason: str, missing: list[str], **extra: Any) -> dict[str, Any]:
    return {"status": "insufficient_data", "reason": reason, "missing_information": missing, **extra}


def financial_summary(db: Session, user_id: UUID, args: PeriodArgs) -> dict[str, Any]:
    start, end = _period(args)
    rows = (
        db.execute(
            text("""
        SELECT t.amount, t.direction, COALESCE(c.type, 'uncategorized') AS category_type,
               COALESCE(c.name, 'Uncategorized') AS category_name
        FROM transactions t
        JOIN accounts a ON a.id = t.account_id
        LEFT JOIN categories c ON c.id = t.category_id
        WHERE a.user_id = :user_id AND t.txn_date BETWEEN :start AND :end
    """),
            {"user_id": user_id, "start": start, "end": end},
        )
        .mappings()
        .all()
    )
    if not rows:
        return _insufficient(
            "No posted transactions are available for this period.",
            ["transactions", "period coverage"],
            period={"start": start.isoformat(), "end": end.isoformat()},
        )
    income = sum(
        (
            Decimal(str(r["amount"]))
            for r in rows
            if r["direction"] == "credit" and r["category_type"] == "income"
        ),
        Decimal(),
    )
    expenses = sum(
        (
            Decimal(str(r["amount"]))
            for r in rows
            if r["direction"] == "debit" and r["category_type"] not in {"transfer", "income"}
        ),
        Decimal(),
    )
    surplus = income - expenses
    facts = {
        "total_income": _json_money(income),
        "total_expenses": _json_money(expenses),
        "operating_surplus": _json_money(surplus),
        "savings_rate": _json_money((surplus / income * 100) if income else None),
        "transaction_count": len(rows),
    }
    return {
        "status": "ok",
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "facts": facts,
        "confidence": {
            "label": "medium",
            "basis": "Computed from posted transactions; account balances and debt splits are not included in this Phase 5 tool.",
        },
    }


def transactions(db: Session, user_id: UUID, args: TransactionsArgs) -> dict[str, Any]:
    start, end = _period(args)
    clauses = ["a.user_id = :user_id", "t.txn_date BETWEEN :start AND :end"]
    values: dict[str, Any] = {"user_id": user_id, "start": start, "end": end, "limit": args.limit}
    if args.category:
        clauses.append("LOWER(COALESCE(c.name, 'Uncategorized')) = LOWER(:category)")
        values["category"] = args.category
    if args.merchant:
        clauses.append("LOWER(COALESCE(m.normalized_name, t.raw_description)) LIKE LOWER(:merchant)")
        values["merchant"] = f"%{args.merchant}%"
    if args.min_amount is not None:
        clauses.append("t.amount >= :min_amount")
        values["min_amount"] = args.min_amount
    if args.max_amount is not None:
        clauses.append("t.amount <= :max_amount")
        values["max_amount"] = args.max_amount
    rows = (
        db.execute(
            text(f"""
        SELECT t.id, t.txn_date, t.amount, t.direction, t.raw_description,
               COALESCE(m.normalized_name, 'Uncategorized') merchant,
               COALESCE(c.name, 'Uncategorized') category
        FROM transactions t JOIN accounts a ON a.id=t.account_id
        LEFT JOIN merchants m ON m.id=t.merchant_id LEFT JOIN categories c ON c.id=t.category_id
        WHERE {" AND ".join(clauses)} ORDER BY t.txn_date DESC LIMIT :limit
    """),
            values,
        )
        .mappings()
        .all()
    )
    return {
        "status": "ok",
        "count": len(rows),
        "transactions": [
            {
                "id": str(r["id"]),
                "date": r["txn_date"].isoformat(),
                "amount": _json_money(r["amount"]),
                "direction": r["direction"],
                "merchant": r["merchant"],
                "category": r["category"],
            }
            for r in rows
        ],
        "period": {"start": start.isoformat(), "end": end.isoformat()},
    }


def spending_by_category(db: Session, user_id: UUID, args: PeriodArgs) -> dict[str, Any]:
    start, end = _period(args)
    rows = (
        db.execute(
            text("""
        SELECT COALESCE(c.name, 'Uncategorized') name, COALESCE(c.type, 'uncategorized') type, SUM(t.amount) amount
        FROM transactions t JOIN accounts a ON a.id=t.account_id LEFT JOIN categories c ON c.id=t.category_id
        WHERE a.user_id=:user_id AND t.txn_date BETWEEN :start AND :end AND t.direction='debit'
          AND COALESCE(c.type, 'uncategorized') NOT IN ('transfer','income')
        GROUP BY c.name, c.type ORDER BY amount DESC
    """),
            {"user_id": user_id, "start": start, "end": end},
        )
        .mappings()
        .all()
    )
    if not rows:
        return _insufficient(
            "No categorized or uncategorized expense transactions are available.", ["expense transactions"]
        )
    total = sum((Decimal(str(r["amount"])) for r in rows), Decimal())
    return {
        "status": "ok",
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "categories": [
            {
                "name": r["name"],
                "type": r["type"],
                "amount": _json_money(r["amount"]),
                "pct_of_total": _json_money(Decimal(str(r["amount"])) / total * 100 if total else None),
            }
            for r in rows
        ],
    }


def recurring_expenses(db: Session, user_id: UUID, args: StatusArgs) -> dict[str, Any]:
    where = "r.user_id=:user_id" if args.status == "all" else "r.user_id=:user_id AND r.status=:status"
    values = {"user_id": user_id, "status": args.status}
    rows = (
        db.execute(
            text(f"""
        SELECT r.id, COALESCE(m.normalized_name, 'Unnamed recurring payment') merchant,
               r.expected_amount, r.frequency, r.next_expected_date, r.status
        FROM recurring_transactions r LEFT JOIN merchants m ON m.id=r.merchant_id WHERE {where}
        ORDER BY r.next_expected_date NULLS LAST
    """),
            values,
        )
        .mappings()
        .all()
    )
    if not rows:
        return _insufficient("No recurring payment records are available.", ["recurring payments"])
    return {
        "status": "ok",
        "recurring": [
            {
                "id": str(r["id"]),
                "merchant": r["merchant"],
                "amount": _json_money(r["expected_amount"]),
                "frequency": r["frequency"],
                "next_expected_date": r["next_expected_date"].isoformat()
                if r["next_expected_date"]
                else None,
                "status": r["status"],
            }
            for r in rows
        ],
    }


def debt_summary(db: Session, user_id: UUID, _args: BaseModel) -> dict[str, Any]:
    rows = (
        db.execute(
            text("""
        SELECT a.id, a.name, a.type, a.balance, l.interest_rate, l.monthly_installment, l.outstanding_balance,
               cc.credit_limit, cc.current_balance, cc.minimum_due, cc.apr
        FROM accounts a LEFT JOIN loans l ON l.account_id=a.id LEFT JOIN credit_cards cc ON cc.account_id=a.id
        WHERE a.user_id=:user_id AND a.type IN ('loan','credit_card') ORDER BY a.name
    """),
            {"user_id": user_id},
        )
        .mappings()
        .all()
    )
    if not rows:
        return _insufficient(
            "No debt accounts have been supplied; this is not proof of zero debt.",
            ["loan or credit-card data"],
        )
    loans, cards = [], []
    total = Decimal()
    for r in rows:
        balance = Decimal(
            str(
                r["outstanding_balance"]
                if r["type"] == "loan" and r["outstanding_balance"] is not None
                else r["current_balance"]
                if r["type"] == "credit_card" and r["current_balance"] is not None
                else r["balance"] or 0
            )
        )
        total += balance
        item = {"id": str(r["id"]), "name": r["name"], "balance": _json_money(balance)}
        if r["type"] == "loan":
            item.update(
                interest_rate=_json_money(r["interest_rate"]),
                monthly_installment=_json_money(r["monthly_installment"]),
            )
            loans.append(item)
        else:
            item.update(
                credit_limit=_json_money(r["credit_limit"]),
                minimum_due=_json_money(r["minimum_due"]),
                apr=_json_money(r["apr"]),
            )
            cards.append(item)
    return {
        "status": "ok",
        "total_debt": _json_money(total),
        "loans": loans,
        "credit_cards": cards,
        "confidence": {"label": "medium", "basis": "Current supplied account and debt rows."},
    }


def cash_flow_forecast(db: Session, user_id: UUID, args: ForecastArgs) -> dict[str, Any]:
    row = (
        db.execute(
            text(
                "SELECT daily_projection, horizon_days, method, confidence, generated_at FROM cash_flow_forecasts WHERE user_id=:user_id ORDER BY generated_at DESC LIMIT 1"
            ),
            {"user_id": user_id},
        )
        .mappings()
        .first()
    )
    if not row:
        return _insufficient(
            "No cash-flow forecast has been generated yet.",
            ["account balance anchor", "future obligations", "forecast run"],
        )
    projection = row["daily_projection"]
    if isinstance(projection, str):
        import json

        projection = json.loads(projection)
    return {
        "status": "ok",
        "daily_projection": projection[: args.horizon_days],
        "horizon_days": min(args.horizon_days, row["horizon_days"]),
        "method": row["method"],
        "confidence": row["confidence"],
    }


def risk_events(db: Session, user_id: UUID, args: StatusArgs) -> dict[str, Any]:
    where = "user_id=:user_id" if args.status == "all" else "user_id=:user_id AND status=:status"
    rows = (
        db.execute(
            text(
                f"SELECT id, risk_type, severity, evidence, confidence, detected_at, status FROM risk_events WHERE {where} ORDER BY detected_at DESC"
            ),
            {"user_id": user_id, "status": args.status},
        )
        .mappings()
        .all()
    )
    if not rows:
        return _insufficient("No risk events are available for this workspace.", ["risk analysis run"])
    return {
        "status": "ok",
        "risks": [
            {
                "id": str(r["id"]),
                "risk_type": r["risk_type"],
                "severity": r["severity"],
                "evidence": r["evidence"],
                "confidence": str(r["confidence"]),
                "detected_at": r["detected_at"].isoformat(),
                "status": r["status"],
            }
            for r in rows
        ],
    }


def recommendations(db: Session, user_id: UUID, args: StatusArgs) -> dict[str, Any]:
    where = "user_id=:user_id" if args.status == "all" else "user_id=:user_id AND status=:status"
    rows = (
        db.execute(
            text(
                f"SELECT id, title, reason, evidence, action, confidence, priority, assumptions, status, generated_at FROM recommendations WHERE {where} ORDER BY priority, generated_at DESC"
            ),
            {"user_id": user_id, "status": args.status},
        )
        .mappings()
        .all()
    )
    if not rows:
        return _insufficient(
            "No recommendation run is available for this workspace.", ["risk and recommendation analysis"]
        )
    return {
        "status": "ok",
        "recommendations": [
            {
                "id": str(r["id"]),
                "title": r["title"],
                "reason": r["reason"],
                "evidence": r["evidence"],
                "action": r["action"],
                "confidence": str(r["confidence"]),
                "priority": r["priority"],
                "assumptions": r["assumptions"],
                "status": r["status"],
                "generated_at": r["generated_at"].isoformat(),
            }
            for r in rows
        ],
    }


def affordability(db: Session, user_id: UUID, args: AffordabilityArgs) -> dict[str, Any]:
    target = args.target_date or date.today()
    rows = (
        db.execute(
            text("SELECT balance FROM accounts WHERE user_id=:user_id AND type IN ('checking','savings')"),
            {"user_id": user_id},
        )
        .scalars()
        .all()
    )
    if not rows:
        return _insufficient(
            "I need a current liquid-account balance before checking affordability.",
            ["checking or savings balance", "purchase date"],
        )
    cash = sum((Decimal(str(v)) for v in rows), Decimal())
    buffer = db.execute(
        text("SELECT preferred_buffer_days FROM users WHERE id=:user_id"), {"user_id": user_id}
    ).scalar_one_or_none()
    # A full forecast is preferred; this conservative Phase 5 check is explicit about its limitation.
    verdict = "yes" if cash - args.amount > 0 else "no"
    return {
        "status": "ok",
        "verdict": verdict,
        "amount": _json_money(args.amount),
        "target_date": target.isoformat(),
        "current_liquid_cash": _json_money(cash),
        "resulting_liquid_cash": _json_money(cash - args.amount),
        "preferred_buffer_days": buffer,
        "confidence": "low",
        "reasoning_basis": [
            "Current supplied checking/savings balances only; future obligations were not available in the affordability tool."
        ],
    }


def simulate_action(_db: Session, _user_id: UUID, args: SimulationArgs) -> dict[str, Any]:
    return _insufficient(
        "The scenario engine is not available until the Phase 4 analytics services are installed.",
        ["completed baseline analysis", "scenario engine"],
        requested_action={"type": args.action_type, "params": args.params},
    )


TOOL_SPECS: dict[str, ToolSpec] = {
    "get_financial_summary": ToolSpec(
        "get_financial_summary",
        "Return posted income, expenses and operating surplus for a period.",
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
        "Return expense totals grouped by category.",
        PeriodArgs,
        spending_by_category,
    ),
    "get_recurring_expenses": ToolSpec(
        "get_recurring_expenses",
        "Return recurring payment records and their statuses.",
        StatusArgs,
        recurring_expenses,
    ),
    "get_debt_summary": ToolSpec(
        "get_debt_summary", "Return supplied loan and card debt.", EmptyArgs, debt_summary
    ),
    "get_cash_flow_forecast": ToolSpec(
        "get_cash_flow_forecast",
        "Return the latest deterministic forecast.",
        ForecastArgs,
        cash_flow_forecast,
    ),
    "get_risk_events": ToolSpec(
        "get_risk_events", "Return owner-scoped risk events.", StatusArgs, risk_events
    ),
    "calculate_affordability": ToolSpec(
        "calculate_affordability",
        "Check a purchase against current liquid cash.",
        AffordabilityArgs,
        affordability,
    ),
    "simulate_action": ToolSpec(
        "simulate_action",
        "Run a typed what-if scenario through the scenario engine.",
        SimulationArgs,
        simulate_action,
    ),
    "get_recommendations": ToolSpec(
        "get_recommendations",
        "Return ranked recommendations for the current analysis.",
        StatusArgs,
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
    Intent.GENERAL: ["get_financial_summary", "get_risk_events"],
    Intent.UNCLEAR: ["get_financial_summary", "get_risk_events"],
}
