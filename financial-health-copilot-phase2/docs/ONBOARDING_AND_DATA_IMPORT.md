# Onboarding and Data Import

This covers the piece no other document owns end-to-end: what actually happens between signup and a user (or judge) seeing a populated dashboard.

## Why This Matters

`FUNCTIONAL_REQUIREMENTS.md` (section A) specifies *what* can be ingested; `FRONTEND_ARCHITECTURE.md` assumes data already exists when describing the dashboard. This document is the missing link — the first-run experience — which matters both for real users and for a smooth hackathon demo.

## Onboarding Modes (MVP supports all three)

### 1. Demo Mode (primary path for hackathon judging)
- On signup, the user is offered: "Explore with sample data" → picks one of the three personas (`SAMPLE_DATA.md`) → backend runs the seed script scoped to that user's `user_id` → redirected straight to a populated dashboard.
- This is the fastest path to a compelling first impression and the one the demo script (`DEMO_SCRIPT.md`) relies on.

### 2. CSV/File Import
- User uploads a CSV of transactions (a documented template is provided for download: `date, amount, direction, description, account_name`).
- Flow: **Upload → Preview & column mapping → Validate → Confirm import → Ingestion pipeline runs (`DATA_PIPELINES.md`) → Redirect to dashboard.**
- Preview step shows the first 10 parsed rows with detected column mapping, letting the user correct mismatches before committing (e.g., if amount and date columns are swapped).
- Validation errors (bad dates, unparseable amounts) are shown per-row in the preview, not just as a rejected file.

### 3. Manual Entry
- A lightweight form-based path for a user with very few accounts/transactions: add an account, add income sources, add loans/cards, add a handful of transactions directly via `POST /transactions` / `POST /accounts` forms.
- Positioned as the fallback for users without a CSV, not the primary path — the UI nudges toward Demo Mode or CSV import first.

## Onboarding Flow (wireframe)

```
┌─────────────────────────────────────────────────────────┐
│  Welcome! How would you like to get started?              │
│                                                             │
│  [ Explore with sample data ]   ← recommended, one click   │
│  [ Import a CSV of transactions ]                          │
│  [ Add accounts manually ]                                 │
└─────────────────────────────────────────────────────────┘
```

If "Explore with sample data" is chosen:
```
┌─────────────────────────────────────────────────────────┐
│  Pick a starting scenario:                                │
│  ○ Ananya — salaried, tight budget                         │
│  ○ Rohit — freelancer, variable income                     │
│  ○ Meera — high saver, planning a big purchase             │
│                                    [ Continue → ]           │
└─────────────────────────────────────────────────────────┘
```

## Minimum Data for a Non-Degraded Experience

| Feature | Minimum to avoid "insufficient data" state |
|---|---|
| Spending breakdown | 1 period (30 days) of transactions |
| Recurring detection | 2 cycles of the same merchant/amount |
| Cash-flow forecast (Medium confidence) | 1–3 months history |
| Cash-flow forecast (High confidence) | 3+ months history, low spend volatility |
| Debt risk detection | At least one loan or credit card record |
| Income volatility detection | 3+ income periods |

The onboarding UI should set expectations honestly: a brand-new manual-entry user will see several `insufficient_data` states initially, and the onboarding screen says so ("Some predictions need a bit more history — they'll sharpen as you add data") rather than implying full functionality from transaction one.

## Post-Onboarding: Triggering the "Adaptiveness" Demo

Whichever onboarding path is used, the same "inject a new transaction" mechanism (`POST /transactions`) is what powers the recalculation demo (`DEMO_SCENARIOS.md`, Scenario 7). No separate code path is needed — onboarding import and the live demo trigger use the identical ingestion pipeline, which is itself a small piece of design integrity worth preserving during implementation.

## Edge Cases

- **Duplicate CSV upload:** handled by the same `dedup_hash` mechanism as any other ingestion (`DATA_PIPELINES.md`) — re-uploading the same file is a safe no-op, and the confirm screen reports "142 imported, 0 duplicates skipped" (or the actual count) so the user isn't left wondering if it worked.
- **Partially malformed CSV:** valid rows are imported, invalid rows are listed with the specific error, and the user can fix and re-upload just the corrected rows rather than starting over.
- **Switching demo personas:** since demo data is scoped to `user_id`, switching personas mid-demo requires either a fresh account or an explicit "reset my data" action (`DELETE` cascading per `SECURITY_AND_PRIVACY.md`) followed by re-seeding — worth having a one-click "reset & reseed" affordance in the demo build specifically, even though it's not a real-user-facing feature.
