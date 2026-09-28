"""Small, deterministic intent extractor used when no model is configured.

The classifier is deliberately conservative. It extracts only entities needed
by safe tools and never executes a financial operation itself.
"""

import re
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from app.ai.schemas import Intent

AMOUNT_RE = re.compile(r"(?:₹|rs\.?|inr\s*)\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", re.I)


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


def classify(message: str) -> tuple[Intent, dict[str, object]]:
    text = message.lower()
    entities: dict[str, object] = {}
    amount = extract_amount(message)
    if amount is not None:
        entities["amount"] = amount
    target = extract_target_date(message)
    if target:
        entities["target_date"] = target
    if any(w in text for w in ("what if", "if i", "cancel", "reduce", "extra payment", "pay extra")):
        return Intent.WHAT_IF, entities
    if any(w in text for w in ("afford", "buy", "purchase", "laptop", "phone")):
        return Intent.AFFORDABILITY, entities
    if any(w in text for w in ("debt", "loan", "emi", "credit card", "utilization", "interest")):
        return Intent.DEBT, entities
    if any(
        w in text for w in ("cash flow", "cashflow", "balance", "bill", "payday", "run out", "enough money")
    ):
        return Intent.CASH_FLOW, entities
    if any(w in text for w in ("save", "saving", "savings", "surplus")):
        return Intent.SAVINGS, entities
    if any(w in text for w in ("spend", "spent", "spending", "category", "merchant", "expense")):
        return Intent.SPENDING, entities
    if any(w in text for w in ("recommend", "should i", "focus", "next step", "action")):
        return Intent.RECOMMENDATION, entities
    return Intent.GENERAL, entities
