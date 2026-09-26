# Confidence and Explainability

## The Four Labels

Every piece of information the system surfaces carries exactly one of these labels, rendered consistently in the UI (distinct icon + color + text tag, never color alone):

| Label | Meaning | Example |
|---|---|---|
| **OBSERVED FACT** | Directly computed from real ingested data, no projection involved | "You spent ₹12,450 on dining in the last 30 days." |
| **PREDICTION** | A forward-looking estimate, always carries a confidence level | "At the current pace, dining spending may reach approximately ₹15,000 this month. (Medium confidence)" |
| **RECOMMENDATION** | A suggested action derived from a prediction/risk, always carries expected impact + confidence | "Reducing dining spending by ₹2,000 could increase your projected month-end buffer by ₹2,000." |
| **ASSUMPTION** | A stated premise the prediction/recommendation depends on that isn't itself observed | "Assumes no other unscheduled large expenses this month." |

## Confidence Scoring

`confidence = f(data_completeness, data_freshness, historical_consistency, forecast_uncertainty, num_observations)`

Implemented as a weighted rule (transparent, not a black box):

```
confidence_score =
    0.30 * data_completeness_score      # 0-1: % of expected fields/periods present
  + 0.20 * data_freshness_score         # 0-1: recency of last ingested transaction
  + 0.20 * historical_consistency_score # 0-1: inverse of spending/income volatility (CV)
  + 0.20 * forecast_uncertainty_score   # 0-1: inverse of confidence-interval width relative to balance
  + 0.10 * observation_count_score      # 0-1: scaled by number of periods/cycles observed (caps at 6)
```

Mapped to labels:
- `≥ 0.7` → **High**
- `0.4 – 0.7` → **Medium**
- `< 0.4` → **Low** (and if `< 0.25`, the system prefers to say "insufficient data" rather than present a number that looks authoritative)

## Why "Medium" in the Worked Example

For "dining spending may reach ~₹15,000 this month":
- `data_completeness`: high (full 30 days of transactions present) → contributes positively.
- `historical_consistency`: dining has moderate month-to-month variation (CV ≈ 0.22) → pulls confidence down from High.
- `observation_count`: only 3 months of history available → not yet at the 6-period cap → pulls down further.
- Net result lands in the Medium band — and the system states *why* medium, not just that it is medium, whenever a user asks ("why is this medium confidence?").

## No False Precision

- Predictions are always presented as ranges or with an explicit ± band, never a bare single number implying certainty it doesn't have (e.g., "approximately ₹15,000" with a stated range, not "₹15,127.43").
- Rounding rules: amounts under ₹1,000 shown to the nearest ₹10; ₹1,000–₹100,000 to the nearest ₹100; above that, nearest ₹1,000 — predictions only, not observed facts (observed facts show exact figures since they're not estimates).
- Confidence is never omitted for a prediction or recommendation — it is a required field in every API response schema for those types.

## Explainability Requirements

- Every risk event stores its triggering `evidence` (the exact numbers that crossed the threshold) — the UI can always show "why was this flagged?"
- Every recommendation stores the `risk_event_id` it originated from, so a user can trace recommendation → risk → underlying facts.
- Every prediction stores its `method` (e.g., `rolling_average_v1`) so the system (and demo) can explain *how* a number was derived, not just what it is.
