# Judging Criteria Mapping

This document exists for one purpose: to make it fast, during Q&A, to point a judge at exactly where in the system (and in this documentation) each requirement from the original problem statement is addressed. Nothing here is new design — it's a cross-reference index.

## Expected Outcome 1: "Creates a consolidated financial-health view from transaction and financial-history data."

- **Where:** `DATA_ARCHITECTURE.md` (unified data model), `FINANCIAL_ANALYTICS.md` (the metric set), `API_SPECIFICATION.md` → `GET /financial-summary`, `FRONTEND_ARCHITECTURE.md` (dashboard "Where am I?" section).
- **Demo evidence:** Dashboard first-look screen (`DEMO_SCRIPT.md`, 0:45–1:30).

## Expected Outcome 2: "Identifies spending patterns, recurring obligations, debt pressure, and potential future cash-flow gaps."

- **Where:** `DATA_PIPELINES.md` (recurring detection stage), `FORECASTING_AND_RISK.md` (all 7 risk rules including recurring burden, debt pressure, cash-flow gap), `FUNCTIONAL_REQUIREMENTS.md` section D.
- **Demo evidence:** `DEMO_SCENARIOS.md` Scenarios 1, 4, 5, 7.

## Expected Outcome 3: "Answers financial questions conversationally with personalised recommendations."

- **Where:** `AI_ARCHITECTURE.md`, `AI_AGENT_DESIGN.md` (tool set), `CONVERSATIONAL_AI.md` (question categories + example conversations), `RECOMMENDATION_ENGINE.md` (personalization logic — never generic advice).
- **Demo evidence:** `DEMO_SCRIPT.md` 1:30–2:15; `DEMO_SCENARIOS.md` Scenario 2.

## Expected Outcome 4: "Shows the expected impact of each recommended action."

- **Where:** `IMPACT_SIMULATION.md` (the whole document), `RECOMMENDATION_ENGINE.md` (`expected_impact` field is mandatory in the schema), `API_SPECIFICATION.md` → `POST /simulate`.
- **Demo evidence:** `DEMO_SCRIPT.md` 3:00–4:00 (loan what-if); `DEMO_SCENARIOS.md` Scenario 3.

## Expected Outcome 5: "Clearly separates observed facts, model predictions, and recommendations, and shows confidence where information is incomplete."

- **Where:** `CONFIDENCE_AND_EXPLAINABILITY.md` (the entire labeling and confidence-scoring system), `UI_UX_DESIGN.md` (canonical badge spec), `AI_ARCHITECTURE.md` (response schema enforcing this at the API level), `ERROR_HANDLING.md` (insufficient-data behavior).
- **Demo evidence:** Visible on every screen throughout the demo; explicitly called out at `DEMO_SCRIPT.md` 5:15–6:00.

## Expected Outcome 6: "Demonstrates how recommendations change as new transactions, income, debt, or expense information is added."

- **Where:** `DATA_PIPELINES.md` (recalculation trigger), `FUNCTIONAL_REQUIREMENTS.md` section H, `RECOMMENDATION_ENGINE.md` (lifecycle states: active/resolved/superseded), `API_SPECIFICATION.md` → `POST /transactions` (`recalculation_triggered` field), `GET /recommendations/{id}/history`.
- **Demo evidence:** This is the centerpiece of the demo — `DEMO_SCRIPT.md` 4:00–5:15, `DEMO_SCENARIOS.md` Scenario 7 (the full before/after walkthrough).

## "Must NOT simply be a dashboard" / DATA → INSIGHT → RISK → RECOMMENDATION → IMPACT chain

- **Where:** `SYSTEM_ARCHITECTURE.md` (Recommendation Flow diagram), `FRONTEND_ARCHITECTURE.md` (dashboard structured around the four-question chain, not a metrics grid), `UI_UX_DESIGN.md` (badge system enforces this chain is visible per-card, not just structurally present in the backend).

## Explicit LLM Constraints ("never rely on LLM for arithmetic")

- **Where:** `AI_ARCHITECTURE.md` ("Where the LLM Is Never Used" section), `AI_AGENT_DESIGN.md` (all financial tools are deterministic Python), `TESTING_STRATEGY.md` (groundedness/hallucination-rate tests), `EVALUATION_METRICS.md` (hallucination rate as a tracked metric).
- **How to prove it live if asked:** Run the groundedness eval set (`TESTING_STRATEGY.md`) and show 0% hallucination rate, or walk through `AI_ARCHITECTURE.md`'s "no-tool-no-number rule."

## Technology Choice Justification

- **Where:** `TECH_STACK.md` — every technology choice has an explicit "why," alternatives considered, and trade-offs, per the brief's instruction not to blindly assume a stack.

## MVP vs. Future Scope Discipline

- **Where:** `PRODUCT_REQUIREMENTS.md` (P0/P1/P2), `FUTURE_SCOPE.md` (explicit MVP-vs-future table), `ASSUMPTIONS.md`.
- **Why it matters for judging:** Demonstrates the team scoped deliberately rather than either over-building or leaving gaps unacknowledged.
