import uuid
from datetime import date, timedelta
from decimal import Decimal

from app.db.models import Account, Category, Transaction
from app.forecast.service import generate_forecast


def test_confidence_degrades_on_truncated_history():
    acc = Account(id=uuid.uuid4(), balance=Decimal("1000.00"), type="checking")
    cat = Category(id=uuid.uuid4(), type="discretionary")
    cat_map = {cat.id: cat}

    today = date.today()
    txns_full = []
    for i in range(120):
        t_date = today - timedelta(days=i)
        txns_full.append(Transaction(
            id=uuid.uuid4(),
            amount=Decimal("10.00"),
            txn_date=t_date,
            direction="debit",
            category_id=cat.id
        ))

    # Full history
    res_full = generate_forecast([acc], txns_full, [], [], cat_map, [])
    assert res_full.confidence == "high"

    # Truncated history (45 days)
    txns_trunc = [t for t in txns_full if t.txn_date >= (today - timedelta(days=45))]
    res_trunc = generate_forecast([acc], txns_trunc, [], [], cat_map, [])
    assert res_trunc.confidence == "medium"

    # Short history (15 days)
    txns_short = [t for t in txns_full if t.txn_date >= (today - timedelta(days=15))]
    res_short = generate_forecast([acc], txns_short, [], [], cat_map, [])
    assert res_short.confidence == "low"
