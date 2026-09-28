# Phase 5 implementation

Phase 5 adds a grounded conversational layer over the deterministic financial services. It is intentionally usable without an AI API key: the same allowlisted tools run locally and a deterministic response template explains tool results. A hosted model is opt-in only.

## Implemented modules

| Module | Responsibility |
|---|---|
| `backend/app/ai/schemas.py` | Intent, claim, tool-call and response contracts |
| `backend/app/ai/intent.py` | Conservative fallback intent/entity extraction |
| `backend/app/ai/tools.py` | Ten owner-scoped deterministic tools and strict argument models |
| `backend/app/ai/orchestrator.py` | Bounded tool selection/execution, fallback composition and optional provider composition |
| `backend/app/ai/provider.py` | OpenAI-compatible JSON composition adapter using the existing HTTP client |
| `backend/app/ai/prompts.py` | Inert-data, no-number-invention system instructions |
| `backend/app/ai/grounding.py` | Numeric post-check against tool results |
| `backend/app/chat/models.py` | SQLAlchemy chat session/message persistence |
| `backend/app/chat/router.py` | Authenticated `/chat/sessions/*` API |
| `backend/app/db/migrations/versions/0002_chat_schema.py` | Persists response JSON and optional session title |
| `backend/scripts/evaluate_ai.py` | Provider-free 20-question intent/tool contract check |

## API usage

```bash
# Create a login token first using /api/v1/auth/signup or /api/v1/auth/login.
curl -X POST http://localhost:8000/api/v1/chat/sessions \
  -H "Authorization: Bearer $TOKEN"

curl -X POST http://localhost:8000/api/v1/chat/sessions/$SESSION_ID/messages \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"message":"Can I afford a ₹30,000 laptop next week?"}'

curl http://localhost:8000/api/v1/chat/sessions/$SESSION_ID/messages \
  -H "Authorization: Bearer $TOKEN"
```

With an empty Phase 0/early Phase 1 workspace, the response deliberately says which information is missing. It does not present zero debt, zero spending or an invented forecast.

## Tool contract

The registry exposes exactly these names: `get_financial_summary`, `get_transactions`, `get_spending_by_category`, `get_recurring_expenses`, `get_debt_summary`, `get_cash_flow_forecast`, `get_risk_events`, `calculate_affordability`, `simulate_action` and `get_recommendations`. The authenticated request supplies the owner ID; no model argument can override it.

Each tool validates arguments through Pydantic, applies a bounded date/horizon, executes owner-scoped SQL or calls the future Phase 4 engine, and returns `status: ok`, `insufficient_data` or `error`. Tool results are stored in the assistant message only as structured output and a safe summary; raw model reasoning is never stored.

## Model mode and consent

Default configuration is `AI_MODE=auto` with `CLOUD_AI_CONSENT_GRANTED=false`, so no model request occurs. To opt in for a test environment, set a provider key, model and explicit consent in the server environment:

```dotenv
AI_MODE=auto
CLOUD_AI_CONSENT_GRANTED=true
LLM_API_KEY=...
LLM_MODEL=gpt-4.1-mini
LLM_BASE_URL=https://api.openai.com/v1
```

The provider receives the user question and compact, verified tool results—not a database dump. The provider must return JSON that validates as `ChatResponse`. A provider timeout, malformed response or grounding failure falls back to the deterministic response without failing the deterministic API. Phase 5 does not add a consent UI; Phase 6 should wire the existing product consent journey before enabling cloud AI for real users.

## Grounding behavior

The fallback response labels facts, predictions, recommendations and assumptions in structured fields. Any model-composed answer is checked for numeric tokens against the tool payload. A number absent from the current tool result rejects the model response and uses the fallback. Years are ignored by the lightweight checker; this is a safeguard, not a formal proof system.

## Current Phase 4 dependency boundary

The repository currently contains the Phase 0 foundation and Phase 5 integration points. If the Phase 1–4 data/forecast/recommendation services have not been merged into this checkout, their tools return a truthful `insufficient_data` response—especially forecasts, simulations and recommendations. Once those services exist, replace the query bodies behind the same registry names; chat routes and schemas do not need to change.

## Verification

```bash
cd backend
pytest -q
python scripts/evaluate_ai.py
```

The evaluation script verifies all 20 authored prompts select an allowlisted intent/tool path. Numeric groundedness tests reject an unsupported amount. Full answer correctness and 0% hallucination claims require seeded Phase 1–4 fixtures and are not claimed from an empty database.

## Security notes

User transaction descriptions are data, not instructions. Tool calls cannot accept `user_id`; authorization is injected from the verified bearer token. The provider adapter has no arbitrary function execution, SQL access, browser access or payment capability. The server logs no raw prompt/tool payload by default.
