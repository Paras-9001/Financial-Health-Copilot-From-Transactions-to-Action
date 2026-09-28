# Financial Health Copilot — Phase 5

Phase 5 adds the grounded AI Copilot to the complete Phase 0–4 backend. The chat layer calls the existing deterministic analytics, recurring detection, forecast, risk, recommendation, simulation, and affordability services; it does not replace or duplicate their calculations.

**Phases 0–5 are implemented.** The full chat UI remains Phase 6. Phase 5 chat is available through the authenticated API and FastAPI `/docs` page.

## What Phase 5 adds

- Authenticated chat sessions and persisted messages.
- Deterministic intent/entity extraction with an optional, explicitly consented provider.
- Ten allowlisted, owner-scoped tools backed by the real Phase 1–4 services.
- Structured fact, prediction, recommendation, assumption, confidence, and source labels.
- Numeric groundedness validation for provider-composed answers.
- A deterministic fallback that works without an API key.
- Twenty-question routing evaluation plus seeded integration tests.

## Start locally

```bash
cd financial-health-copilot-phase5
python scripts/setup_env.py
docker compose up --build
```

Open `http://localhost:8000/docs`. Sign up or log in, authorize with the returned bearer token, seed a demo persona through `POST /api/v1/onboarding/demo`, then use:

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/chat/sessions` | Create an owned chat session |
| POST | `/api/v1/chat/sessions/{id}/messages` | Ask a grounded financial question |
| GET | `/api/v1/chat/sessions/{id}/messages` | Read the session history |

## Verify

```bash
docker compose exec backend pytest -q
docker compose exec backend python scripts/evaluate_ai.py
docker compose exec backend ruff check .
docker compose exec backend ruff format --check .
```

The health endpoint reports Phase 5, and readiness requires migration `0004_phase5`.

## Optional provider mode

Local deterministic mode is the default. A hosted provider is used only when consent, a key, and a model are all configured:

```dotenv
AI_MODE=auto
CLOUD_AI_CONSENT_GRANTED=true
LLM_API_KEY=...
LLM_MODEL=...
LLM_BASE_URL=https://api.openai.com/v1
```

If the provider fails, returns malformed JSON, or introduces an unsupported number, the API returns the deterministic grounded response instead.

See `docs/PHASE_5_IMPLEMENTATION.md`, `docs/PHASE_5_API.md`, and `docs/PHASE_5_REVIEW.md`.
