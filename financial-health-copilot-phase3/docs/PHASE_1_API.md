# Phase 1 API

All routes below use the `/api/v1` prefix and require `Authorization: Bearer <JWT>` unless noted. The authenticated user ID always comes from the verified token; data routes never accept another user's ID.

## Manual entry

- `GET/POST /accounts` — list or create checking, savings, credit-card, loan, or investment accounts.
- `GET/POST /loans` — list or create loan details; a linked account must belong to the user and have type `loan`.
- `GET/POST /credit-cards` — list or create card details; the linked account must have type `credit_card`.
- `GET/POST /income-sources` — list or declare monthly, biweekly, or irregular income.
- `GET /categories` — return the deterministic fixed taxonomy.

## Transaction ingestion

`POST /transactions` accepts `{ "transactions": [...] }`. Each row contains `account_id`, `txn_date`, `amount`, `direction`, and `raw_description`. Valid rows are committed even when another row is invalid. The response reports `ingested`, `duplicates_skipped`, row-specific `rejected` errors, data-quality `warnings`, and whether recalculation was triggered.

`GET /transactions` supports category, merchant, date, amount and pagination filters. `PATCH /transactions/{id}` accepts `category_id`, marks the row as a manual override, and remembers that merchant correction only for the current user.

The duplicate key is SHA-256 over canonical account ID, date, positive two-decimal amount and trimmed raw description. Repeating the same event is a no-op.

## CSV import

1. Send a multipart CSV file to `POST /imports/csv/preview`. Optional form field `column_mapping` is a JSON object mapping `date`, `amount`, `direction`, `description`, and `account_name` to source column names.
2. The response returns a short-lived `preview_id`, detected mapping, the first 10 rows, and valid/invalid totals.
3. Send `{ "preview_id": "..." }` to `POST /imports/csv/confirm`. You may supply a corrected `column_mapping` in this request.
4. Valid rows import; malformed rows return with source row numbers. Re-uploading the same file reports duplicates without inserting them again.

Limits: UTF-8 CSV, 2 MB, 5,000 rows, 30-minute in-memory preview lifetime. Missing account names are created as INR checking accounts during confirmation. Preview state is deliberately local-process state for the MVP and should move to a persistent staging table before horizontally scaling the API.

## Demo onboarding

`GET /onboarding/personas` lists Ananya, Rohit and Meera. `POST /onboarding/demo` accepts `{ "persona": "ananya" }` (or `rohit`/`meera`) and seeds the authenticated user's empty workspace. An account that already contains financial data receives `409 onboarding_already_completed`, preventing accidental persona mixing.

The CLI supports repeatable bulk seeding:

```bash
docker compose exec backend python scripts/seed_demo_data.py --persona all
```

Use `--persona ananya`, `rohit`, or `meera` for one persona. It is disabled when `ENVIRONMENT=production`.
