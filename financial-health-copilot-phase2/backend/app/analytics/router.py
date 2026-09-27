from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analytics.repository import AnalyticsRepository
from app.analytics.schemas import (
    AmortizationScheduleResponse,
    CategorySpendingResponse,
    DebtSummaryResponse,
    FactsSchema,
    FinancialSummaryResponse,
    HealthScoreSchema,
    PeriodSchema,
    RatiosSchema,
)
from app.analytics.service import (
    calculate_cash_buffer_days,
    calculate_confidence,
    calculate_credit_utilization,
    calculate_debt_service_ratio,
    calculate_debt_to_income,
    calculate_discretionary_expenses,
    calculate_emergency_fund_months,
    calculate_expense_to_income,
    calculate_fixed_expenses,
    calculate_health_score,
    calculate_loan_amortization,
    calculate_monthly_burn,
    calculate_recurring_burden_pct,
    calculate_savings,
    calculate_savings_rate,
    calculate_spending_by_category,
    calculate_total_expenses,
    calculate_total_income,
    calculate_variable_expenses,
    quantize_1,
    quantize_2,
)
from app.core.database import get_db
from app.core.errors import APIError
from app.core.security import current_user
from app.db.user import User

router = APIRouter(tags=["Financial Analytics"])


def resolve_period(
    repo: AnalyticsRepository,
    user_id: UUID,
    start_date: date | None,
    end_date: date | None,
) -> tuple[date, date]:
    all_txns = repo.get_user_transactions(user_id)
    if not all_txns:
        raise APIError(status=404, code="no_data", message="No transactions found for user")

    if start_date is not None and end_date is not None:
        if end_date < start_date:
            raise APIError(
                status=422,
                code="validation_error",
                message="end_date must be on or after start_date",
            )
        return start_date, end_date

    latest_date = all_txns[-1].txn_date
    resolved_end = end_date or latest_date
    resolved_start = start_date or (resolved_end - timedelta(days=30))
    return resolved_start, resolved_end


@router.get("/financial-summary", response_model=FinancialSummaryResponse)
def get_financial_summary(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    repo = AnalyticsRepository(db)
    resolved_start, resolved_end = resolve_period(repo, user.id, start_date, end_date)

    txns = repo.get_transactions_in_period(user.id, resolved_start, resolved_end)
    cat_map = repo.get_categories_map()
    accounts = repo.get_accounts(user.id)
    loans = repo.get_loans(user.id)
    credit_cards = repo.get_credit_cards(user.id)
    income_sources = repo.get_income_sources(user.id)
    recurring = repo.get_recurring_transactions(user.id)

    total_income = calculate_total_income(txns, cat_map, income_sources)
    total_expenses = calculate_total_expenses(txns, cat_map)
    fixed_expenses = calculate_fixed_expenses(txns, cat_map)
    variable_expenses = calculate_variable_expenses(txns, cat_map)
    discretionary_expenses = calculate_discretionary_expenses(txns, cat_map)

    savings = calculate_savings(total_income, total_expenses)
    savings_rate = calculate_savings_rate(total_income, total_expenses)
    expense_to_income = calculate_expense_to_income(total_expenses, total_income)

    days_in_period = max(1, (resolved_end - resolved_start).days)
    monthly_burn = calculate_monthly_burn(total_expenses, days_in_period)

    # Debt payments
    monthly_debt_payments = sum((loan.monthly_installment for loan in loans), Decimal("0.00")) + sum(
        (c.minimum_due for c in credit_cards), Decimal("0.00")
    )
    dti = calculate_debt_to_income(monthly_debt_payments, total_income)
    debt_service_ratio = calculate_debt_service_ratio(monthly_debt_payments, total_income)
    credit_util = calculate_credit_utilization(credit_cards)

    # Cash buffer & liquid accounts
    liquid_balance = sum((a.balance for a in accounts if a.type in ("checking", "savings")), Decimal("0.00"))
    savings_balance = sum((a.balance for a in accounts if a.type == "savings"), Decimal("0.00"))
    avg_daily_expense = total_expenses / Decimal(days_in_period) if days_in_period > 0 else Decimal("0.00")
    cash_buffer = calculate_cash_buffer_days(liquid_balance, avg_daily_expense)
    emergency_fund = calculate_emergency_fund_months(
        savings_balance if savings_balance > Decimal("0") else liquid_balance,
        avg_daily_expense * Decimal("30"),
    )

    # Recurring obligations
    recurring_total = sum(
        (r.expected_amount for r in recurring if r.status == "confirmed"), Decimal("0.00")
    ) + sum((loan.monthly_installment for loan in loans), Decimal("0.00"))
    recurring_burden = calculate_recurring_burden_pct(recurring_total, total_income)

    health_score_val = calculate_health_score(
        savings_rate=savings_rate,
        debt_to_income=dti,
        credit_utilization=credit_util,
        cash_buffer_days=cash_buffer,
        preferred_buffer_days=user.preferred_buffer_days,
        recurring_burden_pct=recurring_burden,
    )
    confidence_val = calculate_confidence(
        data_completeness=Decimal("1.0"),
        data_freshness=Decimal("1.0"),
        historical_consistency=Decimal("0.98"),
        forecast_uncertainty=Decimal("0.8"),
        observation_count_periods=3,
    )

    # Record snapshot in background / audit table
    repo.save_snapshot(
        user_id=user.id,
        total_income=total_income,
        total_expenses=total_expenses,
        fixed_expenses=fixed_expenses,
        variable_expenses=variable_expenses,
        discretionary_expenses=discretionary_expenses,
        savings=savings,
        savings_rate=savings_rate,
        debt_to_income=dti,
        debt_service_ratio=debt_service_ratio,
        cash_buffer_days=cash_buffer,
        health_score=Decimal(str(health_score_val)),
        metric_period_start=resolved_start,
        metric_period_end=resolved_end,
    )

    return FinancialSummaryResponse(
        period=PeriodSchema(start=resolved_start, end=resolved_end),
        facts=FactsSchema(
            total_income=str(quantize_2(total_income)),
            total_expenses=str(quantize_2(total_expenses)),
            savings=str(quantize_2(savings)),
            savings_rate=str(quantize_2(savings_rate)),
            fixed_expenses=str(quantize_2(fixed_expenses)),
            variable_expenses=str(quantize_2(variable_expenses)),
            discretionary_expenses=str(quantize_2(discretionary_expenses)),
            monthly_burn=str(quantize_2(monthly_burn)),
            cash_buffer_days=str(quantize_1(cash_buffer)) if cash_buffer is not None else None,
            emergency_fund_months=str(quantize_1(emergency_fund)) if emergency_fund is not None else None,
        ),
        ratios=RatiosSchema(
            debt_to_income=str(quantize_2(dti)),
            recurring_burden_pct=str(quantize_2(recurring_burden)),
            credit_utilization=str(quantize_2(credit_util)),
            debt_service_ratio=str(quantize_2(debt_service_ratio)),
            expense_to_income=str(quantize_2(expense_to_income)),
        ),
        health_score=HealthScoreSchema(value=health_score_val, confidence=confidence_val),
    )


@router.get("/spending/by-category", response_model=CategorySpendingResponse)
def get_spending_by_category(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    repo = AnalyticsRepository(db)
    resolved_start, resolved_end = resolve_period(repo, user.id, start_date, end_date)
    txns = repo.get_transactions_in_period(user.id, resolved_start, resolved_end)
    cat_map = repo.get_categories_map()
    items = calculate_spending_by_category(txns, cat_map)
    return CategorySpendingResponse(categories=items)


@router.get("/debt/summary", response_model=DebtSummaryResponse)
def get_debt_summary(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    repo = AnalyticsRepository(db)
    loans = repo.get_loans(user.id)
    credit_cards = repo.get_credit_cards(user.id)

    if not loans and not credit_cards:
        raise APIError(status=404, code="no_debt_data", message="No debt accounts found for user")

    # Income for DTI calculation
    income_sources = repo.get_income_sources(user.id)
    monthly_income = sum(
        (
            s.amount
            if s.frequency == "monthly"
            else s.amount * Decimal("26") / Decimal("12")
            if s.frequency == "biweekly"
            else s.amount
            for s in income_sources
        ),
        Decimal("0.00"),
    )
    if monthly_income == Decimal("0.00"):
        # Check recent income transactions
        txns = repo.get_user_transactions(user.id)
        cat_map = repo.get_categories_map()
        monthly_income = calculate_total_income(txns, cat_map, income_sources)

    total_debt = sum((loan.outstanding_balance for loan in loans), Decimal("0.00")) + sum(
        (c.current_balance for c in credit_cards), Decimal("0.00")
    )
    monthly_debt_payments = sum((loan.monthly_installment for loan in loans), Decimal("0.00")) + sum(
        (c.minimum_due for c in credit_cards), Decimal("0.00")
    )
    dti = calculate_debt_to_income(monthly_debt_payments, monthly_income)
    debt_service = calculate_debt_service_ratio(monthly_debt_payments, monthly_income)
    credit_util = calculate_credit_utilization(credit_cards)

    return DebtSummaryResponse(
        total_debt=str(quantize_2(total_debt)),
        dti=str(quantize_2(dti)),
        debt_service_ratio=str(quantize_2(debt_service)),
        credit_utilization=str(quantize_2(credit_util)),
        loans=[
            {
                "id": loan.id,
                "principal": str(quantize_2(loan.principal)),
                "interest_rate": str(quantize_2(loan.interest_rate)),
                "term_months": loan.term_months,
                "monthly_installment": str(quantize_2(loan.monthly_installment)),
                "outstanding_balance": str(quantize_2(loan.outstanding_balance)),
            }
            for loan in loans
        ],
        credit_cards=[
            {
                "id": c.id,
                "credit_limit": str(quantize_2(c.credit_limit)),
                "current_balance": str(quantize_2(c.current_balance)),
                "statement_date": c.statement_date,
                "minimum_due": str(quantize_2(c.minimum_due)),
                "apr": str(quantize_2(c.apr)) if c.apr is not None else None,
            }
            for c in credit_cards
        ],
    )


@router.get("/debt/loans/{id}/amortization", response_model=AmortizationScheduleResponse)
def get_loan_amortization(
    id: UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    repo = AnalyticsRepository(db)
    loan = repo.get_loan_by_id(user.id, id)
    if loan is None:
        raise APIError(status=404, code="loan_not_found", message="Loan not found")

    schedule = calculate_loan_amortization(
        principal=loan.principal,
        interest_rate=loan.interest_rate,
        term_months=loan.term_months,
        monthly_installment=loan.monthly_installment,
        start_date=loan.start_date,
    )
    return AmortizationScheduleResponse(schedule=schedule)
