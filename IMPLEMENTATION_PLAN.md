# Implementation Plan

## Phase 0 — Setup
- **Tasks:** Repo scaffolding (frontend/backend/docker-compose), Postgres schema migration (Alembic) from `DATABASE_SCHEMA.md`, auth module, CI lint/test hook.
- **Dependencies:** None.
- **Output:** Running skeleton app; login works; empty dashboard loads.
- **Acceptance criteria:** `docker compose up` starts all services; a user can sign up and log in.

## Phase 1 — Data Layer
- **Tasks:** Implement `accounts`, `transactions`, `merchants`, `categories`, `loans`, `credit_cards`, `income_sources` models + repositories; build `POST /transactions` ingestion with validation + dedup; seed script for the 3 personas.
- **Dependencies:** Phase 0.
- **Output:** Seed data loads cleanly; transactions queryable via API.
- **Acceptance criteria:** Re-running the seed script produces zero duplicate transactions.

## Phase 2 — Financial Analytics
- **Tasks:** Implement all formulas in `FINANCIAL_ANALYTICS.md` as unit-tested pure functions; `GET /financial-summary` endpoint.
- **Dependencies:** Phase 1.
- **Output:** Accurate metrics for all 3 personas, verified against hand-computed fixtures.
- **Acceptance criteria:** Unit test suite passes with 100% of fixture values matching.

## Phase 3 — Forecasting
- **Tasks:** Recurring detection, rolling-average forecast, confidence interval/labeling logic; `GET /cash-flow/forecast`.
- **Dependencies:** Phase 2.
- **Output:** Forecast chart data available for all personas.
- **Acceptance criteria:** Confidence label correctly degrades on a truncated-history test fixture.

## Phase 4 — Recommendation Engine
- **Tasks:** Risk rule engine (`FORECASTING_AND_RISK.md`), recommendation generation/ranking/dedup, impact simulation engine, `/risks`, `/recommendations`, `/simulate` endpoints.
- **Dependencies:** Phase 3.
- **Output:** Personas A/B/C each produce their designed risks and recommendations (per `SAMPLE_DATA.md`).
- **Acceptance criteria:** Scenario 7 (before/after recalculation) reproducible end-to-end via API calls alone.

## Phase 5 — AI Copilot
- **Tasks:** Tool registry (`AI_AGENT_DESIGN.md`), intent classification, agent orchestrator, response schema validation, `/chat/*` endpoints, groundedness eval script.
- **Dependencies:** Phase 4 (needs all tools implemented).
- **Output:** Chat answers the 20-question eval set correctly and shows correct labeling.
- **Acceptance criteria:** 0% hallucination rate on the eval set (per `EVALUATION_METRICS.md` methodology).

## Phase 6 — Frontend
- **Tasks:** All pages/components from `FRONTEND_ARCHITECTURE.md`; React Query wiring to every endpoint; fact/prediction/recommendation card components; charts.
- **Dependencies:** Can start in parallel with Phases 2–5 against mocked API responses matching `API_SPECIFICATION.md`, then swap to real endpoints.
- **Output:** Full navigable UI for all pages.
- **Acceptance criteria:** All 5 primary user journeys (`PRODUCT_REQUIREMENTS.md`) completable via UI only.

## Phase 7 — Integration
- **Tasks:** Wire frontend to real backend end-to-end; fix contract mismatches; implement `<RecalculationToast>` behavior; polish loading/error states.
- **Dependencies:** Phases 5, 6.
- **Output:** Fully working app against seeded data.
- **Acceptance criteria:** Demo Scenario 7 works live through the UI (inject transaction → see dashboard/recommendation change).

## Phase 8 — Testing
- **Tasks:** Complete unit/integration/E2E suites per `TESTING_STRATEGY.md`; run the LLM eval set; fix any groundedness failures.
- **Dependencies:** Phase 7.
- **Output:** Green test suite; documented eval results.
- **Acceptance criteria:** All P0 acceptance criteria across this document pass.

## Phase 9 — Demo Polish
- **Tasks:** Rehearse `DEMO_SCRIPT.md`; pre-seed the exact demo state; add the "inject transaction" one-click demo trigger; visual polish pass; record a backup video in case of live-demo failure.
- **Dependencies:** Phase 8.
- **Output:** Demo-ready build.
- **Acceptance criteria:** Full demo script runs in under 7 minutes without manual data entry beyond one click.
