# Error Handling

## Principle

The system should never present uncertainty as certainty, and never fail silently. A missing/incomplete/invalid state always gets a clear, specific message — to the user and in the API contract — rather than a zero, a crash, or a guessed value.

## Scenarios

| Scenario | System behavior |
|---|---|
| **Missing transactions** (new user, no data yet) | Dashboard shows onboarding/empty state: "No transactions yet — import data to see your financial health." No metrics computed/shown as zero. |
| **Incomplete financial history** (<2 periods) | Metrics requiring trend/comparison return with `insufficient_history: true`; UI shows the raw available number with a note, not a suppressed blank. |
| **Duplicate transactions** | Caught by `dedup_hash` unique constraint at ingestion; ingestion response reports `duplicates_skipped` count explicitly rather than silently dropping them without mention. |
| **Invalid amounts** (zero, non-numeric, absurd e.g. negative balance where not allowed) | `422 validation_error` at the API boundary with the specific offending field; batch ingestion reports per-row errors, valid rows still processed. |
| **Unknown categories/merchants** | Transaction stored with `category = Uncategorized`, `merchant = null`; never force-matched to a wrong category. Surfaced in UI as an actionable "12 uncategorized transactions" prompt. |
| **Missing income data** | Savings rate / DTI / debt-service-ratio return `insufficient_data`; UI explains "Add income information to see this metric." |
| **Missing debt data** | Debt-related endpoints return `404 no_debt_data`, not a fabricated zero-debt state; UI distinguishes "no debt" (explicitly declared) from "no debt data provided" (unknown). |
| **Forecast uncertainty** | Every forecast carries a confidence label and interval; when confidence would be "low," the UI still shows the projection but visually de-emphasized with a clear "low confidence — limited history" note, rather than hiding it. |
| **Insufficient data for a request** (e.g., simulate with a horizon beyond available context) | `422`/`404` with a specific `code` (`insufficient_data`) the frontend maps to `<InsufficientDataCard>`, explaining exactly what's missing. |
| **LLM failure** (timeout, provider error, malformed response) | Agent orchestrator catches the failure, retries once with a stricter prompt if the failure was a schema-validation mismatch, and otherwise returns a templated response: "I couldn't complete that just now — here's what I can tell you from your data directly," falling back to calling the relevant deterministic endpoint result if available. Deterministic dashboard endpoints are entirely unaffected by LLM outages. |
| **API failure** (DB unavailable, unexpected exception) | Global exception handler returns `500` with a generic safe message (no stack trace leakage) and logs full detail server-side; frontend shows a retry-capable error state, never a blank screen. |

## Communicating Uncertainty in the UI (not just errors)

- Confidence badges (`CONFIDENCE_AND_EXPLAINABILITY.md`) are the primary mechanism — they are not decorative, they are load-bearing product behavior distinguishing this app from a dashboard that overstates certainty.
- Any card showing a PREDICTION or RECOMMENDATION without enough backing confidence is replaced with an explicit "Not enough data to predict this yet" card rather than a low-confidence number rendered identically to a high-confidence one.
