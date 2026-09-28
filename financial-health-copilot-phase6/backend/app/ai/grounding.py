"""Lightweight post-check for unsupported numeric claims."""

import re
from decimal import Decimal, InvalidOperation
from typing import Any

NUMBER_RE = re.compile(r"(?<![A-Za-z])(?:₹|INR\s*)?(-?\d[\d,]*(?:\.\d+)?)")


def _numbers(value: Any) -> set[Decimal]:
    if isinstance(value, dict):
        return set().union(*(_numbers(v) for v in value.values())) if value else set()
    if isinstance(value, (list, tuple)):
        return set().union(*(_numbers(v) for v in value)) if value else set()
    if isinstance(value, (int, float, Decimal)):
        try:
            return {Decimal(str(value))}
        except InvalidOperation:
            return set()
    if isinstance(value, str):
        values = set()
        for match in NUMBER_RE.finditer(value):
            try:
                values.add(Decimal(match.group(1).replace(",", "")))
            except InvalidOperation:
                pass
        return values
    return set()


def numeric_claims_grounded(answer_text: str, tool_results: list[dict[str, Any]]) -> bool:
    allowed = _numbers(tool_results)
    mentioned = _numbers(answer_text)
    # Ignore years and ordinal/bullet numbers; all currency/decimal values must be present.
    for value in mentioned:
        if value >= 1900 and value <= 2100 and value == value.to_integral_value():
            continue
        if value not in allowed:
            return False
    return True
