from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint(
            "type IN ('checking','savings','credit_card','loan','investment')",
            name="ck_accounts_type",
        ),
        UniqueConstraint("user_id", "id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String, nullable=False, default="INR")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        CheckConstraint(
            "type IN ('fixed','variable','discretionary','income','transfer')",
            name="ck_categories_type",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Merchant(Base):
    __tablename__ = "merchants"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    raw_pattern: Mapped[str] = mapped_column(String, nullable=False)
    normalized_name: Mapped[str] = mapped_column(String, nullable=False)
    default_category_id: Mapped[UUID | None] = mapped_column(ForeignKey("categories.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RecurringTransaction(Base):
    __tablename__ = "recurring_transactions"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    merchant_id: Mapped[UUID | None] = mapped_column(ForeignKey("merchants.id"))
    expected_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    amount_variance_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    frequency: Mapped[str] = mapped_column(String, nullable=False)
    next_expected_date: Mapped[date | None] = mapped_column(Date)
    confirmed_cycles: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (UniqueConstraint("account_id", "dedup_hash"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    txn_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    direction: Mapped[str] = mapped_column(String, nullable=False)
    raw_description: Mapped[str] = mapped_column(String, nullable=False)
    merchant_id: Mapped[UUID | None] = mapped_column(ForeignKey("merchants.id"))
    category_id: Mapped[UUID | None] = mapped_column(ForeignKey("categories.id"), index=True)
    recurring_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("recurring_transactions.id", ondelete="SET NULL")
    )
    is_manual_override: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    dedup_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Loan(Base):
    __tablename__ = "loans"
    __table_args__ = (ForeignKeyConstraint(["user_id", "account_id"], ["accounts.user_id", "accounts.id"]),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    account_id: Mapped[UUID | None] = mapped_column(nullable=True)
    principal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    interest_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    term_months: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    monthly_installment: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    outstanding_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CreditCard(Base):
    __tablename__ = "credit_cards"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    current_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    statement_date: Mapped[int] = mapped_column(Integer, nullable=False)
    minimum_due: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    apr: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class IncomeSource(Base):
    __tablename__ = "income_sources"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    frequency: Mapped[str] = mapped_column(String, nullable=False)
    is_variable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_received_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Investment(Base):
    __tablename__ = "investments"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    holding_type: Mapped[str] = mapped_column(String, nullable=False)
    current_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MerchantCategoryOverride(Base):
    __tablename__ = "merchant_category_overrides"
    __table_args__ = (UniqueConstraint("user_id", "merchant_id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    merchant_id: Mapped[UUID] = mapped_column(ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False)
    category_id: Mapped[UUID] = mapped_column(ForeignKey("categories.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class FinancialSnapshot(Base):
    __tablename__ = "financial_snapshots"
    __table_args__ = (CheckConstraint("metric_period_end >= metric_period_start", name="ck_snapshot_period"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    snapshot_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    total_income: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    total_expenses: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    fixed_expenses: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    variable_expenses: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    discretionary_expenses: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    savings: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    savings_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    debt_to_income: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    debt_service_ratio: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    cash_buffer_days: Mapped[Decimal | None] = mapped_column(Numeric(6, 1))
    health_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    metric_period_start: Mapped[date | None] = mapped_column(Date)
    metric_period_end: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
