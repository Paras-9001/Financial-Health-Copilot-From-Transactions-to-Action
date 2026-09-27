from datetime import date, timedelta
from decimal import Decimal
import math
from typing import List

from app.db.models import Account, Transaction, RecurringTransaction, IncomeSource, Loan
from app.forecast.schemas import ForecastResponse, DailyProjection

def quantize_2(val: Decimal) -> Decimal:
    if val is None:
        return Decimal("0.00")
    return val.quantize(Decimal("0.01"))

def generate_forecast(
    accounts: List[Account],
    txns: List[Transaction],
    recurring: List[RecurringTransaction],
    income_sources: List[IncomeSource],
    cat_map: dict,
    loans: List[Loan],
    horizon_days: int = 30
) -> ForecastResponse:
    # 1. Starting balance
    current_balance = sum((a.balance for a in accounts if a.type in ("checking", "savings")), Decimal("0.00"))
    
    # 2. Historical unscheduled spend (trailing 90 days)
    today = date.today()
    if txns:
        last_txn_date = max(t.txn_date for t in txns)
        today = last_txn_date
        
    start_history = today - timedelta(days=90)
    historical_txns = [t for t in txns if start_history <= t.txn_date <= today]
    
    # Filter to discretionary and variable
    unscheduled_txns = []
    for t in historical_txns:
        if t.direction == "debit" and t.category_id in cat_map:
            cat = cat_map[t.category_id]
            if cat.type in ("variable", "discretionary"):
                unscheduled_txns.append(t)
                
    # Calculate rolling average daily unscheduled spend
    history_days = max(1, (today - start_history).days)
    total_unscheduled = sum(t.amount for t in unscheduled_txns)
    rolling_avg_daily = total_unscheduled / Decimal(history_days)
    
    # Trend adjustment
    last_30_start = today - timedelta(days=30)
    prev_30_start = today - timedelta(days=60)
    
    recent_total = sum(t.amount for t in unscheduled_txns if t.txn_date > last_30_start)
    prev_total = sum(t.amount for t in unscheduled_txns if prev_30_start < t.txn_date <= last_30_start)
    
    trend_factor = Decimal("1.0")
    if prev_total > 0:
        ratio = recent_total / prev_total
        ratio = min(Decimal("1.15"), max(Decimal("0.85"), ratio))
        trend_factor = ratio
        
    adjusted_daily_spend = rolling_avg_daily * trend_factor
    
    # Confidence score calculation
    monthly_totals = []
    for i in range(3):
        m_start = today - timedelta(days=30 * (i + 1))
        m_end = today - timedelta(days=30 * i)
        m_total = sum(t.amount for t in unscheduled_txns if m_start < t.txn_date <= m_end)
        monthly_totals.append(m_total)
        
    if len(monthly_totals) >= 2 and history_days >= 60:
        mean_spend = sum(monthly_totals) / Decimal(len(monthly_totals))
        if mean_spend > 0:
            variance = sum((m - mean_spend)**2 for m in monthly_totals) / Decimal(len(monthly_totals))
            stddev = Decimal(math.sqrt(float(variance)))
            spending_cv = stddev / mean_spend
        else:
            spending_cv = Decimal("0.0")
    else:
        spending_cv = Decimal("0.4")
        
    if history_days >= 90 and spending_cv < Decimal("0.15"):
        confidence = "high"
    elif history_days >= 30 and spending_cv <= Decimal("0.35"):
        confidence = "medium"
    else:
        confidence = "low"
        
    daily_projection = []
    current_proj = current_balance
    
    for day_idx in range(1, horizon_days + 1):
        proj_date = today + timedelta(days=day_idx)
        flows = Decimal("0.0")
        
        for r in recurring:
            if r.status == "confirmed":
                curr_date = r.next_expected_date
                while curr_date and curr_date <= proj_date:
                    if curr_date == proj_date:
                        flows -= r.expected_amount
                    if r.frequency == "monthly":
                        curr_date += timedelta(days=30)
                    elif r.frequency == "weekly":
                        curr_date += timedelta(days=7)
                    else:
                        break
                        
        for inc in income_sources:
            curr_date = inc.last_received_date
            if not curr_date:
                curr_date = today
            while curr_date <= proj_date:
                if inc.frequency == "monthly":
                    curr_date += timedelta(days=30)
                elif inc.frequency == "biweekly":
                    curr_date += timedelta(days=14)
                elif inc.frequency == "weekly":
                    curr_date += timedelta(days=7)
                else:
                    break
                if curr_date == proj_date:
                    flows += inc.amount
                    
        for loan in loans:
            curr_date = loan.start_date
            while curr_date <= proj_date:
                curr_date += timedelta(days=30)
                if curr_date == proj_date:
                    flows -= loan.monthly_installment
        
        if flows == Decimal("0.0"):
            current_proj -= adjusted_daily_spend
        else:
            current_proj += flows
            
        bound_width = spending_cv * rolling_avg_daily * Decimal(math.sqrt(day_idx))
        
        daily_projection.append(DailyProjection(
            date=proj_date,
            projected_balance=str(quantize_2(current_proj)),
            lower_bound=str(quantize_2(current_proj - bound_width)),
            upper_bound=str(quantize_2(current_proj + bound_width))
        ))
        
    return ForecastResponse(
        daily_projection=daily_projection,
        confidence=confidence,
        method="rolling_average_v1"
    )
