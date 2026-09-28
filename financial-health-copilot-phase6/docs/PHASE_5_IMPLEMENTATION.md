# Phase 5 implementation

This folder is a continuation of `financial-health-copilot-phase4`, not the Phase 0 skeleton. Every Phase 1–4 module and test remains present.

## Architecture

The AI layer classifies a question, validates arguments, and invokes only an allowlisted tool. Each tool injects the authenticated user ID and delegates to the canonical service already used by the REST API:

| AI tool | Canonical implementation |
|---|---|
| `get_financial_summary` | Phase 2 analytics service |
| `get_transactions` | Phase 1 owner-scoped transaction model |
| `get_spending_by_category` | Phase 2 analytics service |
| `get_recurring_expenses` | Phase 3 recurring detector |
| `get_debt_summary` | Phase 2 debt analytics |
| `get_cash_flow_forecast` | Phase 3 forecast engine |
| `get_risk_events` | Phase 4 risk engine |
| `calculate_affordability` | Phase 4 affordability simulation |
| `simulate_action` | Phase 4 impact simulation engine |
| `get_recommendations` | Phase 4 recommendation pipeline |

The model never receives database access, arbitrary function execution, or a caller-supplied user ID. Optional provider output must validate as `ChatResponse`, and every numeric token must be present in the current tool payload. Failure falls back to deterministic composition.

## Persistence and context

Migration `0004_phase5` adds `chat_sessions.title` and `chat_messages.structured_answer` to the chat tables created in the initial schema. The API stores user and assistant turns, tool-call summaries, and structured labels. Up to the latest six turns are supplied to the deterministic follow-up resolver.

## Provider consent

No key is required. `CLOUD_AI_CONSENT_GRANTED=false` prevents provider calls even if other provider variables exist. Enabling hosted composition requires explicit consent plus `LLM_API_KEY` and `LLM_MODEL`.

## Verification boundary

`pytest -q` exercises all Phase 0–5 tests, including a seeded persona chat integration test. `python scripts/evaluate_ai.py` verifies deterministic routing for the committed twenty-question set. Full response correctness is evaluated against seeded personas; an empty account truthfully returns `insufficient_data`.

Phase 6 is responsible for the complete browser chat interface.
