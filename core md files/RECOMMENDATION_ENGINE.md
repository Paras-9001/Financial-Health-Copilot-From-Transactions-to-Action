# Recommendation Engine

## Principle

A recommendation is never generic. It is always: **a specific action, a specific number, tied to specific evidence, with a specific expected outcome.** "Spend less and save more" is never valid output; "Reduce dining spending by ~₹2,500 this month, projected to raise your month-end buffer by ₹2,500" is the bar.

## Recommendation Structure

```json
{
  "recommendation_id": "uuid",
  "title": "Reduce dining spending by ₹2,500 this month",
  "reason": "Dining spend is 42% above your 3-month average and is the largest contributor to a projected cash-flow gap on Oct 14.",
  "evidence": [
    { "type": "fact", "label": "Dining spend (last 30 days)", "value": "₹7,200" },
    { "type": "fact", "label": "3-month average dining spend", "value": "₹5,080" },
    { "type": "prediction", "label": "Projected cash-flow gap", "value": "-₹1,450 on 2026-10-14", "confidence": "medium" }
  ],
  "action": { "type": "reduce_spending", "category": "Dining", "amount": 2500, "period": "this_month" },
  "expected_impact": {
    "buffer_days": { "before": 4, "after": 9 },
    "month_end_balance": { "before": -1450, "after": 1050 }
  },
  "confidence": 0.68,
  "priority": "P0",
  "assumptions": ["User can reduce dining spend without replacing it with another discretionary category", "No other unscheduled large expenses occur this month"]
}
```

## Generation Pipeline

1. **Input:** active risk events + detected surplus opportunities (e.g., consistently high savings rate → suggest an extra debt payment or savings allocation).
2. **Candidate generation:** each risk type maps to one or more candidate action templates (e.g., `upcoming_cash_flow_gap` → {reduce top discretionary category, delay a known upcoming non-essential purchase if detected, flag for user awareness only if no reducible category exists}).
3. **Parameterization:** the candidate's numeric parameters (how much to reduce, by when) are derived deterministically from the evidence (e.g., reduce by exactly the projected gap amount, capped at the category's discretionary total).
4. **Impact calculation:** each candidate is run through the Impact Simulation Engine (`IMPACT_SIMULATION.md`) to get `expected_impact` — never estimated informally.
5. **Confidence:** combines the confidence of the underlying risk/prediction with data completeness (see `CONFIDENCE_AND_EXPLAINABILITY.md`).
6. **Deduplication:** candidates targeting the same risk_event_id and same action type are merged; only the strongest (highest impact-to-effort) survives.
7. **Conflict awareness:** if two recommendations compete for the same surplus (e.g., "pay extra on loan" and "increase savings" both assume the same ₹5,000 surplus), both are shown but each explicitly states the assumption "assumes this surplus is not already allocated elsewhere" and priority ranking indicates which the system considers higher-value given current risk severity. MVP does not block either — it makes the shared-resource assumption visible rather than silently double-counting it as if independently achievable.
8. **Insufficient data filter:** a candidate is suppressed (not shown, not silently downgraded to look normal) if its confidence is below a minimum threshold (default 0.4) or if it depends on <2 cycles of recurring/history data.

## Ranking Logic

`priority_score = severity_weight(risk) × confidence × normalized_impact_magnitude`

- `severity_weight`: High=3, Medium=2, Low=1.
- `normalized_impact_magnitude`: expected change in buffer days (or equivalent) scaled 0–1 relative to the user's typical monthly cash flow.
- Mapped to labels: score ≥ 2.0 → P0, 1.0–2.0 → P1, < 1.0 → P2.

This is a transparent, inspectable formula — never framed as a moral judgment about the user's spending choices; language is always neutral and action-oriented ("Reducing X is projected to..." not "You're overspending on X").

## Avoiding Common Failure Modes

- **Duplicates:** enforced by the `risk_event_id` + `action.type` dedup key in step 6.
- **Unrealistic recommendations:** action parameters are capped against real data (e.g., cannot recommend reducing a category below ₹0, cannot recommend an extra debt payment larger than the user's current surplus).
- **Insufficient-data recommendations:** filtered in step 8; the UI shows "not enough data yet" for the underlying risk rather than a recommendation.
- **Conflicting recommendations:** handled via explicit shared-assumption disclosure (step 7) rather than silently presenting both as fully additive.

## Lifecycle States

`active → resolved` (underlying risk resolved) or `active → superseded` (a stronger recommendation replaces it on recalculation). Both states are retained for the recommendation-history feature (FR-H2).
