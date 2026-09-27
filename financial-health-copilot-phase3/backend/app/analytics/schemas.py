from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PeriodSchema(BaseModel):
    start: date
    end: date


class FactsSchema(BaseModel):
    total_income: str
    total_expenses: str
    savings: str
    savings_rate: str
    fixed_expenses: str | None = None
    variable_expenses: str | None = None
    discretionary_expenses: str | None = None
    monthly_burn: str | None = None
    cash_buffer_days: str | None = None
    emergency_fund_months: str | None = None


class RatiosSchema(BaseModel):
    debt_to_income: str
    recurring_burden_pct: str
    credit_utilization: str
    debt_service_ratio: str | None = None
    expense_to_income: str | None = None


class HealthScoreSchema(BaseModel):
    value: int
    confidence: str


class FinancialSummaryResponse(BaseModel):
    period: PeriodSchema
    facts: FactsSchema
    ratios: RatiosSchema
    health_score: HealthScoreSchema


class CategorySpendingItem(BaseModel):
    name: str
    amount: str
    pct_of_total: str
    type: str


class CategorySpendingResponse(BaseModel):
    categories: list[CategorySpendingItem]


class LoanSummaryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    principal: str
    interest_rate: str
    term_months: int
    monthly_installment: str
    outstanding_balance: str


class CreditCardSummaryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    credit_limit: str
    current_balance: str
    statement_date: int
    minimum_due: str
    apr: str | None = None


class DebtSummaryResponse(BaseModel):
    total_debt: str
    dti: str
    debt_service_ratio: str
    credit_utilization: str
    loans: list[LoanSummaryItem]
    credit_cards: list[CreditCardSummaryItem]


class AmortizationScheduleItem(BaseModel):
    date: str
    principal_component: str
    interest_component: str
    remaining_balance: str


class AmortizationScheduleResponse(BaseModel):
    schedule: list[AmortizationScheduleItem]
