# Development Phases (Day-by-Day)

## Team Roles

- **Backend Engineer:** data layer, analytics, forecasting, risk, recommendations, simulation.
- **AI/ML Engineer:** agent orchestration, tool definitions, prompt design, LLM eval set.
- **Frontend Engineer:** all pages/components, charts, state management.
- **Full-Stack/Integration Engineer:** API contracts, seed data, deployment, demo wiring, unblocks whoever is stuck.

## Working in Parallel Without Blocking

- Agree on `API_SPECIFICATION.md` request/response shapes **before** writing code — frontend builds against mocked responses matching the spec from hour one, backend builds the real implementation independently, and they converge in an integration pass.
- Backend module boundaries (`BACKEND_ARCHITECTURE.md`) let the AI/ML engineer build the agent layer against the analytics/forecasting/risk/recommendation modules' function signatures as soon as they're stubbed (even before full logic is implemented, using fixture return values).
- Seed data (`SAMPLE_DATA.md`) is finalized early and shared as a fixture file so frontend, backend, and AI eval work all reference the same known numbers.

## 48-Hour Plan (typical hackathon)

**Day 1 Morning (0–4h)**
- Repo setup, docker-compose, DB schema migration (Backend/Integration).
- Finalize API spec + seed data personas (all, together).
- Frontend scaffolding + routing + mock API layer (Frontend).
- Tool schema definitions drafted (AI/ML).

**Day 1 Afternoon (4–8h)**
- Ingestion + categorization + recurring detection (Backend).
- Financial analytics functions + unit tests (Backend).
- Dashboard layout + fact/prediction/recommendation card components against mocks (Frontend).
- System prompt + intent classification prototype (AI/ML).

**Day 1 Evening (8–12h)**
- Forecasting engine (Backend).
- Chat UI + simulator UI against mocks (Frontend).
- Tool implementations wired to real (stubbed) analytics functions (AI/ML).
- Checkpoint: merge backend analytics into main, confirm fixture numbers match frontend mocks.

**Day 2 Morning (12–20h)**
- Risk engine + recommendation engine + impact simulation engine (Backend).
- Frontend swaps mocks for real `/financial-summary`, `/risks` endpoints (Frontend + Integration).
- Full agent orchestration + groundedness eval set running (AI/ML).

**Day 2 Afternoon (20–28h)**
- `/simulate`, `/chat` fully wired end-to-end (all).
- Recalculation-on-new-transaction flow + `<RecalculationToast>` (Backend + Frontend).
- Fix integration bugs; run E2E test script.

**Day 2 Evening (28–36h)**
- Seed final demo personas; rehearse `DEMO_SCRIPT.md`; polish visuals; record backup video.
- Buffer time for fixing anything the rehearsal reveals.

**Remaining time before judging (36–48h)**
- Final rehearsal, sleep if possible, deploy hosted demo if using one, prepare for Q&A (be ready to explain the fact/prediction/recommendation architecture and where the LLM is/isn't used — judges will probe this).

## 24-Hour Compressed Version

- Cut Persona B/C to single fixture rows (keep Persona A full).
- Skip hosted deployment — demo locally via docker-compose.
- Reduce recommendation engine to 3 risk types (low buffer, cash-flow gap, high category spend) instead of all 7.
- Skip the recommendation-history/timeline endpoint (P1) — keep only current-state recalculation (P0 requirement, not the historical view).
- Combine Integration engineer's role into whichever of Backend/Frontend is ahead of schedule.

## 72-Hour Extended Version

- Add all P1 features: recommendation history/timeline, multiple selectable personas in UI, category drill-down charts.
- Add lightweight ML forecast comparison (P2) as a bonus "under the hood" toggle for judges who ask about it.
- More thorough LLM eval set (40+ questions) and a written eval report.
