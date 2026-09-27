# Assumptions

## Data & Currency
- All amounts are in INR (₹); no multi-currency support.
- Transactions are assumed complete and settled (no pending/uncleared transaction handling in MVP).
- Historical data window supported: up to 24 months; forecasting/risk logic assumes at least some history exists, with explicit degraded confidence below 1–3 months.

## Recurring Payments
- A payment is treated as recurring only after ≥2 observed cycles at a regular interval; a single occurrence is never asserted as recurring fact.
- Amount tolerance of ±10% and interval tolerance of ±3 days (±7 for annual) are assumed reasonable defaults — configurable, not hardcoded assumptions the team should treat as final.

## Income
- Income frequency is either monthly, biweekly, or irregular; the system assumes a user has at most a small number of income sources (not modeling complex multi-income-stream tax/timing interactions).
- Gross vs. take-home distinction is simplified in MVP — declared income is assumed usable directly for ratio calculations unless the user provides a separate take-home figure.

## Forecast Horizon
- Default forecast horizon is 30 days, extendable to 90 for what-if simulations, capped at 180 — beyond this, confidence is assumed too low to be useful and the system should say so rather than project further.

## Missing Data
- Missing data is never filled with an assumed/average value silently — the system always distinguishes "zero" (observed, real) from "unknown" (not enough data) per `ERROR_HANDLING.md`.

## User Goals
- MVP assumes no explicit user-declared goals (e.g., "save for a house") — recommendations are derived purely from risk/opportunity detection, not goal-tracking. This is called out as a Future Scope gap, not silently ignored.

## Debt & Investment Data
- Loans are assumed to be simple fixed-rate, fixed-term amortizing loans (no variable-rate mortgages, balloon payments, or multiple simultaneous rate changes in MVP).
- Investment data is a balance snapshot only — no transaction-level buy/sell history, no return calculation beyond simple compounding assumptions used illustratively in surplus recommendations.

## Confidence
- The confidence-scoring formula (`CONFIDENCE_AND_EXPLAINABILITY.md`) uses assumed weightings (0.30/0.20/0.20/0.20/0.10) chosen for reasonable, explainable behavior — these are a starting point to validate against real usage, not empirically derived.
- Confidence bands (High ≥0.7, Medium 0.4–0.7, Low <0.4) are likewise reasonable defaults, not statistically calibrated in MVP.

## Assumptions Requiring Validation During Implementation

- Whether ±10%/±3-day recurring-detection tolerances produce acceptable false-positive/negative rates on real-world-shaped data.
- Whether the rolling-average forecast's error is acceptable for the demo personas (should be backtested per `EVALUATION_METRICS.md` before presenting confidence claims to judges).
- Whether the chosen risk thresholds (5-day buffer, 40% debt service ratio, etc.) match commonly accepted financial guidance closely enough to be credible — worth a quick sanity check against public personal-finance guidance during implementation.
- Whether 3 fixed synthetic personas are sufficient to convincingly exercise every risk/recommendation type for judging, or whether a 4th edge-case persona (e.g., zero debt, zero income data) is needed to demonstrate `insufficient_data` handling live.
