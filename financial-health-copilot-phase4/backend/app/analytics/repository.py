from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Account,
    Category,
    CreditCard,
    FinancialSnapshot,
    IncomeSource,
    Loan,
    RecurringTransaction,
    Transaction,
)


class AnalyticsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_categories_map(self) -> dict[UUID, Category]:
        cats = self.db.scalars(select(Category)).all()
        return {cat.id: cat for cat in cats}

    def get_user_transactions(self, user_id: UUID) -> list[Transaction]:
        stmt = (
            select(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .where(Account.user_id == user_id)
            .order_by(Transaction.txn_date.asc())
        )
        return list(self.db.scalars(stmt).all())

    def get_transactions_in_period(
        self, user_id: UUID, start_date: date, end_date: date
    ) -> list[Transaction]:
        stmt = (
            select(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .where(
                Account.user_id == user_id,
                Transaction.txn_date >= start_date,
                Transaction.txn_date <= end_date,
            )
            .order_by(Transaction.txn_date.asc())
        )
        return list(self.db.scalars(stmt).all())

    def get_accounts(self, user_id: UUID) -> list[Account]:
        stmt = select(Account).where(Account.user_id == user_id)
        return list(self.db.scalars(stmt).all())

    def get_loans(self, user_id: UUID) -> list[Loan]:
        stmt = select(Loan).where(Loan.user_id == user_id)
        return list(self.db.scalars(stmt).all())

    def get_loan_by_id(self, user_id: UUID, loan_id: UUID) -> Loan | None:
        stmt = select(Loan).where(Loan.user_id == user_id, Loan.id == loan_id)
        return self.db.scalar(stmt)

    def get_credit_cards(self, user_id: UUID) -> list[CreditCard]:
        stmt = (
            select(CreditCard)
            .join(Account, CreditCard.account_id == Account.id)
            .where(Account.user_id == user_id)
        )
        return list(self.db.scalars(stmt).all())

    def get_income_sources(self, user_id: UUID) -> list[IncomeSource]:
        stmt = select(IncomeSource).where(IncomeSource.user_id == user_id)
        return list(self.db.scalars(stmt).all())

    def get_recurring_transactions(self, user_id: UUID) -> list[RecurringTransaction]:
        stmt = select(RecurringTransaction).where(RecurringTransaction.user_id == user_id)
        return list(self.db.scalars(stmt).all())

    def save_snapshot(
        self,
        user_id: UUID,
        total_income: Decimal,
        total_expenses: Decimal,
        fixed_expenses: Decimal,
        variable_expenses: Decimal,
        discretionary_expenses: Decimal,
        savings: Decimal,
        savings_rate: Decimal,
        debt_to_income: Decimal,
        debt_service_ratio: Decimal,
        cash_buffer_days: Decimal | None,
        health_score: Decimal,
        metric_period_start: date,
        metric_period_end: date,
    ) -> FinancialSnapshot:
        snapshot = FinancialSnapshot(
            user_id=user_id,
            total_income=total_income,
            total_expenses=total_expenses,
            fixed_expenses=fixed_expenses,
            variable_expenses=variable_expenses,
            discretionary_expenses=discretionary_expenses,
            savings=savings,
            savings_rate=savings_rate,
            debt_to_income=debt_to_income,
            debt_service_ratio=debt_service_ratio,
            cash_buffer_days=cash_buffer_days,
            health_score=health_score,
            metric_period_start=metric_period_start,
            metric_period_end=metric_period_end,
        )
        self.db.add(snapshot)
        self.db.flush()
        return snapshot

    def get_latest_snapshot(self, user_id: UUID) -> FinancialSnapshot | None:
        stmt = (
            select(FinancialSnapshot)
            .where(FinancialSnapshot.user_id == user_id)
            .order_by(FinancialSnapshot.snapshot_time.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)
