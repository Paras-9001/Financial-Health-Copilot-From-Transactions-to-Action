# Phase 6 setup

Generate `.env` from the repository root, then run the full stack:

```bash
python scripts/setup_env.py
docker compose up --build
```

The frontend uses `NEXT_PUBLIC_API_URL` and defaults to `http://localhost:8000`. No hosted AI key is required; the Phase 5 deterministic Copilot fallback remains available.

For the fastest check: create an account, choose “Explore with sample data,” select Ananya, and visit every navigation item. CSV import expects `date,amount,direction,description,account_name` columns.
