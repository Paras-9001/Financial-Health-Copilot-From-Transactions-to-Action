"""Small, deterministic intent extractor used when no model is configured.

The classifier is deliberately conservative. It extracts only entities needed
by safe tools and never executes a financial operation itself.
"""

import re
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from app.ai.schemas import Intent

AMOUNT_RE = re.compile(r"(?:₹|rs\.?|inr\s*)\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", re.I)
PERCENT_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*%", re.I)
CATEGORIES = (
    "dining",
    "groceries",
    "transport",
    "shopping",
    "entertainment",
    "utilities",
    "rent",
    "healthcare",
    "education",
)


def extract_amount(text: str) -> Decimal | None:
    match = AMOUNT_RE.search(text)
    if not match:
        return None
    try:
        amount = Decimal(match.group(1).replace(",", ""))
    except InvalidOperation:
        return None
    return amount if amount > 0 else None


def extract_target_date(text: str, today: date | None = None) -> date | None:
    today = today or date.today()
    explicit = re.search(r"\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b", text)
    if explicit:
        try:
            return date(int(explicit.group(1)), int(explicit.group(2)), int(explicit.group(3)))
        except ValueError:
            return None
    if re.search(r"\b(today|tonight)\b", text, re.I):
        return today
    if re.search(r"\btomorrow\b", text, re.I):
        return today + timedelta(days=1)
    if re.search(r"\bnext\s+week\b", text, re.I):
        return today + timedelta(days=7)
    return None


def extract_percent(text: str) -> Decimal | None:
    match = PERCENT_RE.search(text)
    if not match:
        return None
    try:
        value = Decimal(match.group(1))
    except InvalidOperation:
        return None
    lowered = text.lower()
    if value > 0 and any(word in lowered for word in ("fall", "drop", "decrease", "reduce", "cut")):
        value = -value
    return value


def classify(message: str) -> tuple[Intent, dict[str, object]]:
    text = message.lower()
    entities: dict[str, object] = {}
    if any(word in text for word in ("investment", "portfolio", "stocks", "mutual fund")):
        return Intent.UNCLEAR, {"unsupported_area": "investment data"}
    amount = extract_amount(message)
    if amount is not None:
        entities["amount"] = amount
    target = extract_target_date(message)
    if target:
        entities["target_date"] = target
    percent = extract_percent(message)
    if percent is not None:
        entities["percent"] = percent
    category = next((name for name in CATEGORIES if name in text), None)
    if category:
        entities["category"] = category.title()

    if any(w in text for w in ("extra payment", "pay extra", "extra on my loan")):
        entities["action_type"] = "extra_debt_payment"
        return Intent.WHAT_IF, entities
    if "cancel" in text and any(w in text for w in ("subscription", "recurring", "membership", "bill")):
        entities["action_type"] = "modify_recurring"
        entities["cancel"] = True
        return Intent.WHAT_IF, entities
    if "reduce" in text or "cut" in text:
        entities["action_type"] = "reduce_spending"
        return Intent.WHAT_IF, entities
    if "income" in text and any(w in text for w in ("fall", "drop", "change", "increase", "decrease")):
        entities["action_type"] = "change_income"
        return Intent.WHAT_IF, entities
    if amount is not None and re.search(r"\bsave\b.*\b(monthly|every month|per month)\b", text):
        entities["action_type"] = "increase_savings"
        return Intent.WHAT_IF, entities
    if "delay" in text and any(w in text for w in ("purchase", "buy", "payment")):
        entities["action_type"] = "delay_purchase"
        return Intent.WHAT_IF, entities
    if any(w in text for w in ("what if", "if i")):
        return Intent.WHAT_IF, entities
    if any(w in text for w in ("afford", "buy", "purchase", "laptop", "phone")):
        return Intent.AFFORDABILITY, entities
    if any(w in text for w in ("debt", "loan", "emi", "credit card", "utilization", "interest")):
        return Intent.DEBT, entities
    if any(
        w in text for w in ("cash flow", "cashflow", "balance", "bill", "payday", "run out", "enough money")
    ):
        if any(w in text for w in ("bill", "recurring", "subscription", "upcoming payment")):
            entities["cash_flow_mode"] = "recurring"
        return Intent.CASH_FLOW, entities
    if amount is not None and any(w in text for w in ("how can i save", "how do i save")):
        entities["savings_goal"] = amount
        return Intent.SPENDING, entities
    if any(w in text for w in ("save", "saving", "savings", "surplus")):
        return Intent.SAVINGS, entities
    if any(w in text for w in ("spend", "spent", "spending", "category", "merchant", "expense")):
        return Intent.SPENDING, entities
    if any(w in text for w in ("recommend", "should i", "focus", "next step", "action")):
        return Intent.RECOMMENDATION, entities
    if any(w in text for w in ("risk", "warning", "danger", "problem")):
        return Intent.RISK, entities
    return Intent.GENERAL, entities
