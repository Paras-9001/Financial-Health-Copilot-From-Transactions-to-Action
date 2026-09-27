"""Recommendation generation, parameterization, ranking and deduplication.

Implements the pipeline from RECOMMENDATION_ENGINE.md:
1. Input: active risk events
2. Candidate generation: risk_type -> action templates
3. Parameterization: derive numeric params from evidence
4. Impact calculation: via simulation engine
5. Confidence: combine risk confidence + data completeness
6. Deduplication: risk_event_id + action.type
7. Conflict awareness: shared-assumption disclosure
8. Insufficient-data filter: confidence < 0.40 suppressed
"""

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from app.core import config
from app.db.models import (
    Account,
    Category,
    CreditCard,
    IncomeSource,
    Loan,
    RecurringTransaction,
    RiskEvent,
    Transaction,
)
from app.simulation.service import FinancialState, SimulationAction, simulate_action

ZERO = Decimal("0.00")
TWO = Decimal("0.01")


def _q(value: Decimal) -> Decimal:
    return value.quantize(TWO)


@dataclass
class RecommendationCandidate:
    risk_event_id: UUID | None
    risk_type: str
    title: str
    reason: str
    evidence: list[dict]
    action: dict
    expected_impact: dict
    confidence: Decimal
    priority: str
    assumptions: list[str]
    # internal dedup key: risk_event_id + action.type
    dedup_key: str


def _severity_weight(severity: str) -> int:
    return {"high": config.SEVERITY_WEIGHT_HIGH, "medium": config.SEVERITY_WEIGHT_MEDIUM}.get(
        severity, config.SEVERITY_WEIGHT_LOW
    )


def _priority_label(score: Decimal) -> str:
    if score >= config.PRIORITY_SCORE_P0_MIN:
        return "P0"
    if score >= config.PRIORITY_SCORE_P1_MIN:
        return "P1"
    return "P2"


def _impact_magnitude(expected_impact: dict) -> Decimal:
    """Normalized impact magnitude: change in buffer_days scaled 0-1 (cap at 30 days = 1.0)."""
    buffer = expected_impact.get("buffer_days", {})
    before = Decimal(str(buffer.get("before", 0)))
    after = Decimal(str(buffer.get("after", 0)))
    delta = max(ZERO, after - before)
    return min(Decimal("1.0"), delta / Decimal("30"))


# ---------------------------------------------------------------------------
# Impact estimation helpers (simplified deterministic versions of the simulation)
# ---------------------------------------------------------------------------


def _avg_daily_expense_no_cat(
    transactions: list[Transaction],
    category_map: dict[UUID, Category],
    history_days: int,
) -> Decimal:
    if not transactions or history_days <= 0:
        return ZERO
    total = sum(
        (
            txn.amount
            for txn in transactions
            if txn.direction == "debit"
            and txn.category_id in category_map
            and category_map[txn.category_id].type != "transfer"
        ),
        ZERO,
    )
    return total / Decimal(history_days)


def _liquid_balance(accounts: list[Account]) -> Decimal:
    return sum((a.balance for a in accounts if a.type in ("checking", "savings")), ZERO)


def _buffer_days(liquid: Decimal, avg_daily: Decimal) -> Decimal:
    if avg_daily <= ZERO:
        return Decimal("999")
    return liquid / avg_daily


# ---------------------------------------------------------------------------
# Generator: low_cash_buffer
# ---------------------------------------------------------------------------


def _gen_low_cash_buffer(
    risk: RiskEvent,
    accounts: list[Account],
    transactions: list[Transaction],
    category_map: dict[UUID, Category],
    history_days: int,
) -> list[RecommendationCandidate]:
    evidence_data = risk.evidence
    avg_daily = Decimal(str(evidence_data.get("avg_daily_expense", "0")))
    liquid = _liquid_balance(accounts)
    buffer_before = _q(liquid / avg_daily) if avg_daily > ZERO else ZERO

    # Find top discretionary category for reduction recommendation
    cat_totals: dict[str, Decimal] = {}
    as_of = max(txn.txn_date for txn in transactions)
    recent_start = as_of - timedelta(days=29)
    for txn in transactions:
        if (
            txn.direction == "debit"
            and txn.txn_date >= recent_start
            and txn.category_id in category_map
            and category_map[txn.category_id].type == "discretionary"
        ):
            name = category_map[txn.category_id].name
            cat_totals[name] = cat_totals.get(name, ZERO) + txn.amount

    if not cat_totals:
        return []

    top_cat = max(cat_totals, key=lambda k: cat_totals[k])
    top_amount = cat_totals[top_cat]
    # Reduce by 20% of top category, capped to meaningful amount
    reduce_by = _q(min(top_amount * Decimal("0.20"), top_amount))
    if reduce_by <= ZERO:
        return []

    new_avg_daily = max(ZERO, avg_daily - reduce_by / Decimal("30"))
    buffer_after = _q(liquid / new_avg_daily) if new_avg_daily > ZERO else buffer_before

    evidence = [
        {"type": "fact", "label": "Current cash balance", "value": f"₹{_q(liquid):,.2f}"},
        {"type": "fact", "label": "Avg daily expense", "value": f"₹{_q(avg_daily):,.2f}"},
        {
            "type": "prediction",
            "label": "Buffer before action",
            "value": f"{buffer_before:.1f} days",
            "confidence": risk.severity,
        },
    ]
    confidence = _q(risk.confidence * Decimal("0.9"))
    if confidence < config.MIN_RECOMMENDATION_CONFIDENCE:
        return []

    score = (
        Decimal(str(_severity_weight(risk.severity)))
        * confidence
        * _impact_magnitude({"buffer_days": {"before": float(buffer_before), "after": float(buffer_after)}})
    )
    return [
        RecommendationCandidate(
            risk_event_id=risk.id,
            risk_type=risk.risk_type,
            title=f"Reduce {top_cat} spending by ₹{_q(reduce_by):,.0f} this month",
            reason=(
                f"Your cash buffer is critically low at {buffer_before:.1f} days. "
                f"{top_cat} is your largest discretionary category. "
                f"Reducing it by ₹{_q(reduce_by):,.0f} is projected to raise your buffer by "
                f"{_q(buffer_after - buffer_before):.1f} days."
            ),
            evidence=evidence,
            action={
                "type": "reduce_spending",
                "category": top_cat,
                "amount": float(reduce_by),
                "period": "this_month",
            },
            expected_impact={
                "buffer_days": {"before": float(buffer_before), "after": float(buffer_after)},
            },
            confidence=confidence,
            priority=_priority_label(score),
            assumptions=[
                f"Reducing {top_cat} spend is achievable without substituting to another discretionary category.",
                "No other large unscheduled expenses occur this month.",
            ],
            dedup_key=f"{risk.id}:reduce_spending",
        )
    ]


# ---------------------------------------------------------------------------
# Generator: upcoming_cash_flow_gap
# ---------------------------------------------------------------------------


def _gen_upcoming_cash_flow_gap(
    risk: RiskEvent,
    accounts: list[Account],
    transactions: list[Transaction],
    category_map: dict[UUID, Category],
    history_days: int,
) -> list[RecommendationCandidate]:
    evidence_data = risk.evidence
    projected_balance = Decimal(str(evidence_data.get("projected_balance", "0")))
    breach_date = evidence_data.get("breach_date", "unknown")

    liquid = _liquid_balance(accounts)
    avg_daily = _avg_daily_expense_no_cat(transactions, category_map, history_days)
    buffer_before = _q(liquid / avg_daily) if avg_daily > ZERO else ZERO

    # Candidate 1: reduce top discretionary
    cat_totals: dict[str, Decimal] = {}
    as_of = max(txn.txn_date for txn in transactions)
    recent_start = as_of - timedelta(days=29)
    for txn in transactions:
        if (
            txn.direction == "debit"
            and txn.txn_date >= recent_start
            and txn.category_id in category_map
            and category_map[txn.category_id].type in ("variable", "discretionary")
        ):
            name = category_map[txn.category_id].name
            cat_totals[name] = cat_totals.get(name, ZERO) + txn.amount

    candidates = []
    if cat_totals:
        top_cat = max(cat_totals, key=lambda k: cat_totals[k])
        top_amount = cat_totals[top_cat]
        gap = abs(projected_balance)
        reduce_by = _q(min(gap, top_amount))

        if reduce_by > ZERO:
            new_avg = max(ZERO, avg_daily - reduce_by / Decimal("30"))
            buffer_after = _q(liquid / new_avg) if new_avg > ZERO else buffer_before

            confidence = _q(risk.confidence * Decimal("0.85"))
            if confidence >= config.MIN_RECOMMENDATION_CONFIDENCE:
                score = (
                    Decimal(str(_severity_weight(risk.severity)))
                    * confidence
                    * _impact_magnitude(
                        {"buffer_days": {"before": float(buffer_before), "after": float(buffer_after)}}
                    )
                )
                candidates.append(
                    RecommendationCandidate(
                        risk_event_id=risk.id,
                        risk_type=risk.risk_type,
                        title=f"Reduce {top_cat} spending by ₹{_q(reduce_by):,.0f} to avoid cash gap",
                        reason=(
                            f"{top_cat} spend is your largest variable outflow. "
                            f"A projected balance of ₹{_q(projected_balance):,.2f} on {breach_date} "
                            f"indicates a cash gap. Reducing {top_cat} by ₹{_q(reduce_by):,.0f} is projected "
                            f"to close this gap."
                        ),
                        evidence=[
                            {
                                "type": "fact",
                                "label": f"{top_cat} spend (last 30d)",
                                "value": f"₹{_q(top_amount):,.2f}",
                            },
                            {
                                "type": "prediction",
                                "label": "Projected cash gap",
                                "value": f"₹{_q(projected_balance):,.2f} on {breach_date}",
                                "confidence": risk.severity,
                            },
                        ],
                        action={
                            "type": "reduce_spending",
                            "category": top_cat,
                            "amount": float(reduce_by),
                            "period": "this_month",
                        },
                        expected_impact={
                            "buffer_days": {"before": float(buffer_before), "after": float(buffer_after)},
                            "projected_gap_closed": True,
                        },
                        confidence=confidence,
                        priority=_priority_label(score),
                        assumptions=[
                            f"Assumes no other large unscheduled expenses between now and {breach_date}.",
                            f"Assumes reducing {top_cat} spend is feasible without substitution.",
                        ],
                        dedup_key=f"{risk.id}:reduce_spending",
                    )
                )

    return candidates


def _gen_unusually_high_spending(
    risk: RiskEvent,
    accounts: list[Account],
    transactions: list[Transaction],
    category_map: dict[UUID, Category],
    history_days: int,
) -> list[RecommendationCandidate]:
    category = str(risk.evidence.get("category", ""))
    current = Decimal(str(risk.evidence.get("current_period_amount", "0")))
    average = Decimal(str(risk.evidence.get("trailing_average", "0")))
    reduction = _q(min(current, max(ZERO, current - average)))
    if not category or reduction <= ZERO:
        return []

    liquid = _liquid_balance(accounts)
    avg_daily = _avg_daily_expense_no_cat(transactions, category_map, history_days)
    before = _buffer_days(liquid, avg_daily)
    after_daily = max(ZERO, avg_daily - reduction / Decimal("30"))
    after = _buffer_days(liquid, after_daily)
    confidence = _q(risk.confidence * Decimal("0.90"))
    impact = {"buffer_days": {"before": float(_q(before)), "after": float(_q(after))}}
    score = Decimal(str(_severity_weight(risk.severity))) * confidence * _impact_magnitude(impact)
    return [
        RecommendationCandidate(
            risk_event_id=risk.id,
            risk_type=risk.risk_type,
            title=f"Bring {category} spending toward its usual level by ₹{reduction:,.0f}",
            reason=(
                f"{category} spending is ₹{current:,.2f} this period versus a "
                f"₹{average:,.2f} trailing average. Reducing the excess is projected "
                "to improve the cash-flow buffer."
            ),
            evidence=[
                {"type": "fact", "label": "Current-period spend", "value": f"₹{current:,.2f}"},
                {"type": "fact", "label": "Trailing average", "value": f"₹{average:,.2f}"},
            ],
            action={
                "type": "reduce_spending",
                "category": category,
                "amount": float(reduction),
                "period": "this_month",
            },
            expected_impact=impact,
            confidence=confidence,
            priority=_priority_label(score),
            assumptions=[
                f"Assumes reducing {category} does not shift spending to another category.",
                "Assumes no other large unscheduled expenses occur this month.",
            ],
            dedup_key=f"{risk.id}:reduce_spending",
        )
    ]


# ---------------------------------------------------------------------------
# Generator: recurring_payment_burden
# ---------------------------------------------------------------------------


def _gen_recurring_payment_burden(
    risk: RiskEvent,
    recurring: list[RecurringTransaction],
    accounts: list[Account],
    transactions: list[Transaction],
    category_map: dict[UUID, Category],
    history_days: int,
) -> list[RecommendationCandidate]:
    evidence_data = risk.evidence
    obligations = evidence_data.get("obligations", [])
    if not obligations:
        return []

    liquid = _liquid_balance(accounts)
    avg_daily = _avg_daily_expense_no_cat(transactions, category_map, history_days)
    buffer_before = _q(liquid / avg_daily) if avg_daily > ZERO else ZERO

    # Recommend reviewing/cancelling the smallest non-essential recurring
    smallest: RecurringTransaction | None = None
    for item in recurring:
        if item.status == "confirmed":
            if smallest is None or item.expected_amount < smallest.expected_amount:
                smallest = item

    if smallest is None:
        return []

    save_monthly = _q(smallest.expected_amount)
    new_avg = max(ZERO, avg_daily - save_monthly / Decimal("30"))
    buffer_after = _q(liquid / new_avg) if new_avg > ZERO else buffer_before

    confidence = _q(risk.confidence * Decimal("0.95"))
    if confidence < config.MIN_RECOMMENDATION_CONFIDENCE:
        return []

    score = (
        Decimal(str(_severity_weight(risk.severity)))
        * confidence
        * _impact_magnitude({"buffer_days": {"before": float(buffer_before), "after": float(buffer_after)}})
    )
    return [
        RecommendationCandidate(
            risk_event_id=risk.id,
            risk_type=risk.risk_type,
            title=f"Review recurring obligations — burden at {evidence_data.get('recurring_burden_pct', '?')} of income",
            reason=(
                f"Your recurring obligations total ₹{evidence_data.get('monthly_recurring_total', '?')}/month, "
                f"exceeding {config.RECURRING_BURDEN_PCT}% of income. "
                f"Cancelling the smallest non-essential subscription (₹{_q(smallest.expected_amount):,.2f}/month) "
                f"saves ₹{save_monthly:,.2f}/month."
            ),
            evidence=[
                {
                    "type": "fact",
                    "label": "Monthly recurring total",
                    "value": f"₹{evidence_data.get('monthly_recurring_total', '?')}",
                },
                {
                    "type": "fact",
                    "label": "Recurring burden",
                    "value": evidence_data.get("recurring_burden_pct", "?"),
                },
                {
                    "type": "fact",
                    "label": "Suggested cancellation",
                    "value": f"₹{_q(smallest.expected_amount):,.2f}/month",
                },
            ],
            action={"type": "modify_recurring", "recurring_id": str(smallest.id), "cancel": True},
            expected_impact={
                "buffer_days": {"before": float(buffer_before), "after": float(buffer_after)},
                "monthly_savings": float(save_monthly),
            },
            confidence=confidence,
            priority=_priority_label(score),
            assumptions=[
                "Assumes this recurring obligation is non-essential and can be cancelled.",
                "Recurring savings are not reallocated to another discretionary category.",
            ],
            dedup_key=f"{risk.id}:modify_recurring",
        )
    ]


# ---------------------------------------------------------------------------
# Generator: debt_pressure
# ---------------------------------------------------------------------------


def _gen_debt_pressure(
    risk: RiskEvent,
    loans: list[Loan],
    credit_cards: list[CreditCard],
    accounts: list[Account],
    transactions: list[Transaction],
    category_map: dict[UUID, Category],
    history_days: int,
) -> list[RecommendationCandidate]:
    liquid = _liquid_balance(accounts)
    avg_daily = _avg_daily_expense_no_cat(transactions, category_map, history_days)
    buffer_before = _q(liquid / avg_daily) if avg_daily > ZERO else ZERO
    evidence_data = risk.evidence

    candidates = []

    # Credit card balance paydown recommendation
    high_util_cards = [cc for cc in credit_cards if cc.current_balance > ZERO]
    if high_util_cards:
        worst = max(high_util_cards, key=lambda c: c.current_balance / c.credit_limit)
        paydown = _q(min(worst.current_balance, liquid * Decimal("0.25")))  # Use up to 25% of liquid
        if paydown > ZERO:
            new_liquid = liquid - paydown
            buffer_after = _q(new_liquid / avg_daily) if avg_daily > ZERO else buffer_before

            confidence = _q(risk.confidence * Decimal("0.90"))
            if confidence >= config.MIN_RECOMMENDATION_CONFIDENCE:
                new_util = _q((worst.current_balance - paydown) / worst.credit_limit * Decimal("100"))
                score = Decimal(str(_severity_weight(risk.severity))) * confidence * Decimal("0.5")
                candidates.append(
                    RecommendationCandidate(
                        risk_event_id=risk.id,
                        risk_type=risk.risk_type,
                        title=f"Pay down ₹{_q(paydown):,.0f} of credit card balance to reduce utilization",
                        reason=(
                            f"Credit utilization at {evidence_data.get('credit_utilization_pct', '?')} "
                            f"is flagged as high risk. A ₹{_q(paydown):,.0f} payment reduces "
                            f"utilization to approximately {new_util:.1f}%."
                        ),
                        evidence=[
                            {
                                "type": "fact",
                                "label": "Credit utilization",
                                "value": evidence_data.get("credit_utilization_pct", "?"),
                            },
                            {
                                "type": "fact",
                                "label": "CC balance",
                                "value": f"₹{_q(worst.current_balance):,.2f}",
                            },
                            {"type": "fact", "label": "CC limit", "value": f"₹{_q(worst.credit_limit):,.2f}"},
                        ],
                        action={
                            "type": "extra_debt_payment",
                            "account_id": str(worst.account_id),
                            "amount": float(paydown),
                        },
                        expected_impact={
                            "buffer_days": {"before": float(buffer_before), "after": float(buffer_after)},
                            "credit_utilization_after_pct": float(new_util),
                        },
                        confidence=confidence,
                        priority=_priority_label(score),
                        assumptions=[
                            f"Assumes ₹{_q(paydown):,.0f} is available as surplus after essential expenses.",
                            "Assumes no new credit card charges are made during this period.",
                        ],
                        dedup_key=f"{risk.id}:extra_debt_payment",
                    )
                )

    return candidates


# ---------------------------------------------------------------------------
# Generator: income_volatility
# ---------------------------------------------------------------------------


def _gen_income_volatility(
    risk: RiskEvent,
    accounts: list[Account],
    transactions: list[Transaction],
    category_map: dict[UUID, Category],
    history_days: int,
) -> list[RecommendationCandidate]:
    liquid = _liquid_balance(accounts)
    avg_daily = _avg_daily_expense_no_cat(transactions, category_map, history_days)
    buffer_before = _q(liquid / avg_daily) if avg_daily > ZERO else ZERO
    evidence_data = risk.evidence

    # Suggest building an emergency buffer
    target_buffer_days = Decimal("30")
    target_amount = _q(avg_daily * target_buffer_days)
    current_gap = max(ZERO, target_amount - liquid)

    confidence = _q(risk.confidence * Decimal("0.80"))
    if confidence < config.MIN_RECOMMENDATION_CONFIDENCE:
        return []

    buffer_after = min(buffer_before + Decimal("15"), target_buffer_days)
    score = Decimal(str(_severity_weight(risk.severity))) * confidence * Decimal("0.4")
    return [
        RecommendationCandidate(
            risk_event_id=risk.id,
            risk_type=risk.risk_type,
            title=f"Build an emergency buffer of ₹{_q(target_amount):,.0f} (30-day expense reserve)",
            reason=(
                f"Your income has a high coefficient of variation "
                f"({evidence_data.get('income_cv', '?')}), meaning a low-income month could "
                f"leave you unable to cover fixed obligations. A 30-day expense reserve provides a safety net."
            ),
            evidence=[
                {"type": "fact", "label": "Income CV", "value": evidence_data.get("income_cv", "?")},
                {"type": "fact", "label": "Current liquid balance", "value": f"₹{_q(liquid):,.2f}"},
                {
                    "type": "prediction",
                    "label": "30-day expense reserve target",
                    "value": f"₹{_q(target_amount):,.2f}",
                    "confidence": "medium",
                },
            ],
            action={"type": "increase_savings", "amount": float(current_gap), "period": "next_3_months"},
            expected_impact={
                "buffer_days": {"before": float(buffer_before), "after": float(buffer_after)},
                "target_reserve": float(target_amount),
            },
            confidence=confidence,
            priority=_priority_label(score),
            assumptions=[
                "Assumes surplus is available each month to build the reserve.",
                "Assumes income pattern continues to be irregular.",
            ],
            dedup_key=f"{risk.id}:increase_savings",
        )
    ]


# ---------------------------------------------------------------------------
# Generator: surplus opportunity (no risk, triggered by high savings rate)
# ---------------------------------------------------------------------------


def _gen_surplus_opportunity(
    accounts: list[Account],
    transactions: list[Transaction],
    category_map: dict[UUID, Category],
    income_sources: list[IncomeSource],
    loans: list[Loan],
    history_days: int,
) -> list[RecommendationCandidate]:
    """If savings rate >= 35%, suggest extra loan payment or investment increase."""
    if history_days < 30:
        return []

    monthly_income = ZERO
    for src in income_sources:
        if src.frequency == "monthly":
            monthly_income += src.amount
        elif src.frequency == "biweekly":
            monthly_income += src.amount * Decimal("26") / Decimal("12")
        else:
            monthly_income += src.amount

    if monthly_income <= ZERO:
        return []

    monthly_expense = sum(
        (
            txn.amount
            for txn in transactions
            if txn.direction == "debit"
            and txn.category_id in category_map
            and category_map[txn.category_id].type != "transfer"
        ),
        ZERO,
    ) / Decimal(max(1, history_days // 30))

    savings_rate = (monthly_income - monthly_expense) / monthly_income if monthly_income > ZERO else ZERO
    if savings_rate < Decimal("0.35"):
        return []

    surplus = _q(monthly_income - monthly_expense)
    if surplus <= ZERO:
        return []

    candidates = []
    if loans:
        loan = loans[0]
        liquid = _liquid_balance(accounts)
        extra_payment = _q(min(surplus * Decimal("0.5"), loan.outstanding_balance, liquid * Decimal("0.25")))
        if extra_payment > ZERO:
            confidence = _q(Decimal("0.72"))
            score = Decimal("1.5") * confidence * Decimal("0.6")
            candidates.append(
                RecommendationCandidate(
                    risk_event_id=None,
                    risk_type="surplus_opportunity",
                    title=f"Apply ₹{extra_payment:,.0f} extra toward your loan principal",
                    reason=(
                        f"Your savings rate of {_q(savings_rate * Decimal('100')):.1f}% "
                        f"indicates a ₹{surplus:,.2f}/month surplus. An extra principal payment "
                        f"of ₹{extra_payment:,.2f} reduces your interest burden and shortens the payoff timeline."
                    ),
                    evidence=[
                        {"type": "fact", "label": "Monthly surplus", "value": f"₹{surplus:,.2f}"},
                        {
                            "type": "fact",
                            "label": "Savings rate",
                            "value": f"{_q(savings_rate * Decimal('100')):.1f}%",
                        },
                        {
                            "type": "fact",
                            "label": "Loan outstanding balance",
                            "value": f"₹{_q(loan.outstanding_balance):,.2f}",
                        },
                    ],
                    action={
                        "type": "extra_debt_payment",
                        "loan_id": str(loan.id),
                        "amount": float(extra_payment),
                    },
                    expected_impact={
                        "loan_principal_reduced_by": float(extra_payment),
                        "estimated_interest_saved": float(
                            _q(extra_payment * loan.interest_rate / Decimal("100"))
                        ),
                    },
                    confidence=confidence,
                    priority=_priority_label(score),
                    assumptions=[
                        "Assumes this surplus is not already allocated to another savings goal.",
                        "Assumes no large unscheduled expense this month.",
                    ],
                    dedup_key=f"surplus_opportunity:extra_debt_payment:{loan.id}",
                )
            )

    return candidates


# ---------------------------------------------------------------------------
# Main recommendation pipeline
# ---------------------------------------------------------------------------


def generate_recommendations(
    risk_events: list[RiskEvent],
    accounts: list[Account],
    transactions: list[Transaction],
    category_map: dict[UUID, Category],
    recurring: list[RecurringTransaction],
    income_sources: list[IncomeSource],
    loans: list[Loan],
    credit_cards: list[CreditCard],
    history_days: int,
) -> list[RecommendationCandidate]:
    """Generate, rank and deduplicate recommendations from active risk events."""
    candidates: list[RecommendationCandidate] = []
    seen_dedup: set[str] = set()

    def add(c: RecommendationCandidate) -> None:
        if c.dedup_key not in seen_dedup:
            seen_dedup.add(c.dedup_key)
            candidates.append(c)

    def add_list(cs: list[RecommendationCandidate]) -> None:
        for c in cs:
            add(c)

    for risk in risk_events:
        if risk.status != "active":
            continue
        rt = risk.risk_type
        if rt == "low_cash_buffer":
            add_list(_gen_low_cash_buffer(risk, accounts, transactions, category_map, history_days))
        elif rt == "upcoming_cash_flow_gap":
            add_list(_gen_upcoming_cash_flow_gap(risk, accounts, transactions, category_map, history_days))
        elif rt == "unusually_high_spending":
            add_list(_gen_unusually_high_spending(risk, accounts, transactions, category_map, history_days))
        elif rt == "recurring_payment_burden":
            add_list(
                _gen_recurring_payment_burden(
                    risk, recurring, accounts, transactions, category_map, history_days
                )
            )
        elif rt == "debt_pressure":
            add_list(
                _gen_debt_pressure(
                    risk, loans, credit_cards, accounts, transactions, category_map, history_days
                )
            )
        elif rt == "income_volatility":
            add_list(_gen_income_volatility(risk, accounts, transactions, category_map, history_days))
        # unusual_transaction remains awareness-only: MVP has no supported review/dispute action.

    # Surplus opportunity (no underlying risk needed)
    add_list(
        _gen_surplus_opportunity(accounts, transactions, category_map, income_sources, loans, history_days)
    )

    # Confidence filter
    candidates = [c for c in candidates if c.confidence >= config.MIN_RECOMMENDATION_CONFIDENCE]

    # Recalculate every candidate with the canonical simulation engine. Invalid or
    # infeasible actions are suppressed rather than presented with informal impact math.
    state = FinancialState(
        accounts=accounts,
        transactions=transactions,
        recurring=recurring,
        income_sources=income_sources,
        category_map=category_map,
        loans=loans,
        credit_cards=credit_cards,
    )
    severity_by_risk = {risk.id: risk.severity for risk in risk_events}
    simulated: list[RecommendationCandidate] = []
    for candidate in candidates:
        action_data = candidate.action
        try:
            action = SimulationAction(
                type=action_data["type"],
                category=action_data.get("category"),
                amount=(
                    Decimal(str(action_data["amount"])) if action_data.get("amount") is not None else None
                ),
                period=action_data.get("period"),
                loan_id=(UUID(action_data["loan_id"]) if action_data.get("loan_id") else None),
                account_id=(UUID(action_data["account_id"]) if action_data.get("account_id") else None),
                recurring_id=(UUID(action_data["recurring_id"]) if action_data.get("recurring_id") else None),
                cancel=bool(action_data.get("cancel", False)),
            )
            result = simulate_action(state, action)
        except (KeyError, TypeError, ValueError):
            continue

        before_buffer = Decimal(result.baseline["cash_buffer_days_min"])
        after_buffer = Decimal(result.proposed["cash_buffer_days_min"])
        candidate.expected_impact = {
            "buffer_days": {
                "before": float(_q(before_buffer)),
                "after": float(_q(after_buffer)),
            },
            "month_end_balance": {
                "before": result.baseline["month_end_balance"],
                "after": result.proposed["month_end_balance"],
            },
            "delta": result.delta,
            "confidence": result.confidence,
        }
        severity = severity_by_risk.get(candidate.risk_event_id, "low")
        score = (
            Decimal(str(_severity_weight(severity)))
            * candidate.confidence
            * _impact_magnitude(candidate.expected_impact)
        )
        candidate.priority = _priority_label(score)
        simulated.append(candidate)
    candidates = simulated

    # Rank by priority score descending
    def _score(c: RecommendationCandidate) -> float:
        weight = _severity_weight("high" if c.priority == "P0" else "medium" if c.priority == "P1" else "low")
        return float(weight * c.confidence * _impact_magnitude(c.expected_impact))

    candidates.sort(key=_score, reverse=True)
    return candidates
