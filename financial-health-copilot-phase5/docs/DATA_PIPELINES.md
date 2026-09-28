# Data Pipelines

## Pipeline Overview

```
Raw Data → Validation → Normalization → Categorization → Merchant Enrichment
→ Recurring Detection → Aggregation → Financial Metrics → Forecasting
→ Risk Detection → Recommendations
```

Each stage is a pure function (or small set of functions) taking the previous stage's output and the relevant slice of the database, so stages can be tested and re-run independently.

## Stage Detail

### 1. Validation
- Reject transactions with null amount, unparseable date, or amount = 0.
- Flag (don't reject) transactions with dates in the future or older than the supported history window (default 24 months) — surfaced as data-quality warnings, not silently dropped.

### 2. Normalization
- Trim/uppercase raw description for matching; strip trailing reference numbers/IDs (`SWIGGY*ORDER1234` → `SWIGGY`).
- Convert amount sign/direction into a consistent `(amount: positive decimal, direction: debit|credit)` representation regardless of source format.

### 3. Categorization
- Match normalized merchant against a keyword/pattern table (`merchants.raw_pattern`).
- No match → category = `Uncategorized`, categorization_confidence = low; never guess a category from amount alone.
- Respect any user manual override recorded for that merchant.

### 4. Merchant Enrichment
- Resolve to (or create) a `merchants` row with a clean `normalized_name` and a `default_category_id`.

### 5. Recurring Detection
- Group transactions by (user, merchant, amount within ±10%).
- A group qualifies as recurring if it has ≥2 occurrences at a regular interval (weekly ±3 days / monthly ±3 days / yearly ±7 days).
- Status `candidate` at 1 occurrence with a suggestive interval hint from category (e.g., known subscription merchant); `confirmed` at ≥2 occurrences.
- Store `next_expected_date` = last occurrence + interval.

### 6. Aggregation
- Roll up transactions by category/period (daily/weekly/monthly) using pandas groupby.
- Separate fixed (rent, EMI, insurance), variable (utilities, groceries — necessary but fluctuating), and discretionary (dining, entertainment, shopping) using the `categories.type` field.

### 7. Financial Metrics
- Compute the full metric set from `FINANCIAL_ANALYTICS.md` from the aggregated data; persist as a new `financial_snapshots` row.

### 8. Forecasting
- Project the next N days of balance using recurring schedules (known future debits/credits) plus a rolling-average estimate for unscheduled variable/discretionary spend; persist as a new `cash_flow_forecasts` row.

### 9. Risk Detection
- Evaluate the rule set in `FORECASTING_AND_RISK.md` against the latest snapshot + forecast; insert new `risk_events` rows for newly triggered risks; mark previously active risks `resolved` if their condition no longer holds.

### 10. Recommendations
- For each active risk (and detected surplus/opportunity), generate a candidate recommendation, compute its expected impact via the Impact Simulation Engine, deduplicate, rank, and persist as `recommendations` + `recommendation_impacts` rows. Recommendations tied to now-resolved risks are marked `resolved`; recommendations superseded by better-ranked ones are marked `superseded` (kept for history, not deleted).

## Batch vs. Incremental Processing

- **Full recompute (batch):** used on first data load (seeding a persona) — process the entire transaction history through all stages.
- **Incremental:** used when a single new transaction/income/expense/debt event arrives (the common demo case) — only stages affected by the new data point are rerun (categorization/recurring-check on the new row; metrics/forecast/risk/recommendation always rerun in full since they're relatively cheap at hackathon data scale, but implemented as a single `recalculate_user(user_id)` job for simplicity rather than fine-grained incremental diffing).

## Idempotency

- Every transaction has a `dedup_hash = hash(account_id, txn_date, amount, raw_description)` with a `UNIQUE(account_id, dedup_hash)` constraint — re-ingesting the same file/event is a no-op, not a duplicate.
- Recalculation (`recalculate_user`) is idempotent: given the same underlying data, it produces the same snapshot values; it always appends a new snapshot/forecast/risk-evaluation rather than mutating history, so re-running it twice with no new data simply produces two identical snapshots (acceptable at hackathon scale; a production system would add a "no-op if unchanged" guard).

## Missing Data

- Missing income data → savings rate and debt-to-income calculations flagged `insufficient_data` rather than computed from an assumed value.
- Missing debt data → debt-related metrics/risks simply don't fire; UI shows "No debt data provided" rather than a zero (a true zero and "unknown" must never look the same).

## Duplicate Transactions

- Caught at the `dedup_hash` unique constraint during ingestion; ingestion endpoint returns which rows were skipped as duplicates so the caller/demo script can show this behavior explicitly.

## Data Corrections

- A category override or transaction edit updates the row directly (transactions are not append-only), and triggers a full `recalculate_user(user_id)` so downstream metrics/risks/recommendations reflect the correction. A note (`is_manual_override = true`) prevents the categorization stage from silently overwriting the user's correction on a later re-run.
