from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from statistics import median
from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import config
from app.db.models import Category, RecurringTransaction, Transaction
from app.forecast.service import advance_occurrence

TWO_PLACES = Decimal("0.01")


@dataclass(frozen=True)
class RecurringPattern:
    merchant_id: UUID
    expected_amount: Decimal
    amount_variance_pct: Decimal
    frequency: str
    next_expected_date: date
    confirmed_cycles: int
    status: str
    transaction_ids: tuple[UUID, ...]


def _frequency_for_dates(dates: Sequence[date]) -> str | None:
    if len(dates) < config.RECURRING_MIN_CONFIRMED_CYCLES:
        return None
    intervals = [(right - left).days for left, right in zip(dates, dates[1:])]
    typical_interval = Decimal(str(median(intervals)))
    candidates = (
        (
            "weekly",
            Decimal("7"),
            Decimal(config.RECURRING_INTERVAL_TOLERANCE_DAYS_WEEKLY),
        ),
        (
            "monthly",
            Decimal("30"),
            Decimal(config.RECURRING_INTERVAL_TOLERANCE_DAYS_MONTHLY),
        ),
        (
            "yearly",
            Decimal("365"),
            Decimal(config.RECURRING_INTERVAL_TOLERANCE_DAYS_YEARLY),
        ),
    )
    for frequency, expected, tolerance in candidates:
        if abs(typical_interval - expected) <= tolerance:
            return frequency
    return None


def _amount_clusters(transactions: Sequence[Transaction]) -> list[list[Transaction]]:
    clusters: list[list[Transaction]] = []
    tolerance = config.RECURRING_AMOUNT_TOLERANCE_PCT / Decimal("100")
    for transaction in sorted(transactions, key=lambda item: (item.amount, item.txn_date)):
        placed = False
        for cluster in clusters:
            mean = sum((item.amount for item in cluster), Decimal("0")) / Decimal(len(cluster))
            if mean > 0 and abs(transaction.amount - mean) / mean <= tolerance:
                cluster.append(transaction)
                placed = True
                break
        if not placed:
            clusters.append([transaction])
    return clusters


def detect_recurring_patterns(
    transactions: Sequence[Transaction],
    category_map: dict[UUID, Category],
) -> list[RecurringPattern]:
    """Detect repeat debit patterns without mutating database state."""
    if not transactions:
        return []
    as_of_date = max(transaction.txn_date for transaction in transactions)
    by_merchant: dict[UUID, list[Transaction]] = {}
    for transaction in transactions:
        category = category_map.get(transaction.category_id) if transaction.category_id else None
        if (
            transaction.direction != "debit"
            or transaction.merchant_id is None
            or category is None
            or category.type in ("income", "transfer")
            or category.name == "Debt Payment"
        ):
            continue
        by_merchant.setdefault(transaction.merchant_id, []).append(transaction)

    patterns: list[RecurringPattern] = []
    for merchant_id, merchant_transactions in by_merchant.items():
        for cluster in _amount_clusters(merchant_transactions):
            ordered = sorted(cluster, key=lambda item: item.txn_date)
            dates = [item.txn_date for item in ordered]
            frequency = _frequency_for_dates(dates)
            status = "confirmed" if frequency else "candidate"
            if frequency is None:
                category = category_map.get(ordered[0].category_id)
                if len(ordered) != 1 or category is None or category.type != "fixed":
                    continue
                frequency = "monthly"

            mean_amount = sum((item.amount for item in ordered), Decimal("0")) / Decimal(len(ordered))
            max_deviation = max(abs(item.amount - mean_amount) for item in ordered)
            variance_pct = max_deviation / mean_amount * Decimal("100") if mean_amount > 0 else Decimal("0")
            next_date = advance_occurrence(dates[-1], frequency)
            while next_date is not None and next_date <= as_of_date:
                next_date = advance_occurrence(next_date, frequency)
            if next_date is None:
                continue
            patterns.append(
                RecurringPattern(
                    merchant_id=merchant_id,
                    expected_amount=mean_amount.quantize(TWO_PLACES, rounding=ROUND_HALF_UP),
                    amount_variance_pct=variance_pct.quantize(TWO_PLACES, rounding=ROUND_HALF_UP),
                    frequency=frequency,
                    next_expected_date=next_date,
                    confirmed_cycles=len(ordered),
                    status=status,
                    transaction_ids=tuple(item.id for item in ordered),
                )
            )
    return sorted(patterns, key=lambda item: (str(item.merchant_id), item.frequency))


def detect_and_persist_recurring(
    db: Session,
    user_id: UUID,
    transactions: Sequence[Transaction],
    category_map: dict[UUID, Category],
) -> list[RecurringTransaction]:
    patterns = detect_recurring_patterns(transactions, category_map)
    existing_items = list(
        db.scalars(select(RecurringTransaction).where(RecurringTransaction.user_id == user_id)).all()
    )
    by_key = {(item.merchant_id, item.frequency): item for item in existing_items}
    transaction_by_id = {transaction.id: transaction for transaction in transactions}

    for pattern in patterns:
        key = (pattern.merchant_id, pattern.frequency)
        item = by_key.get(key)
        if item is None:
            item = RecurringTransaction(
                user_id=user_id,
                merchant_id=pattern.merchant_id,
                expected_amount=pattern.expected_amount,
                amount_variance_pct=pattern.amount_variance_pct,
                frequency=pattern.frequency,
                next_expected_date=pattern.next_expected_date,
                confirmed_cycles=pattern.confirmed_cycles,
                status=pattern.status,
            )
            db.add(item)
            db.flush()
            existing_items.append(item)
            by_key[key] = item
        elif pattern.status == "confirmed" or item.status != "confirmed":
            item.expected_amount = pattern.expected_amount
            item.amount_variance_pct = pattern.amount_variance_pct
            item.next_expected_date = pattern.next_expected_date
            item.confirmed_cycles = pattern.confirmed_cycles
            item.status = pattern.status

        for transaction_id in pattern.transaction_ids:
            transaction_by_id[transaction_id].recurring_id = item.id

    db.flush()
    return existing_items
