# Non-Functional Requirements

Scoped realistically for a hackathon MVP (single small Postgres instance, single backend process, demo-scale data volumes of a few thousand transactions per user).

## Performance

- API responses for dashboard/analytics endpoints: p95 < 500ms against seeded demo data.
- Chat/agent responses: target < 4s end-to-end (tool calls + LLM composition); acceptable to stream partial output to the UI.
- Recalculation after a new transaction: < 2s for a single user's dataset.

## Scalability

- MVP targets tens of demo users / low thousands of transactions each — no need for horizontal scaling, sharding, or queueing infrastructure.
- Architecture should avoid choices that make later scaling *hard* (e.g., keep analytics logic stateless and callable as a batch job), but should not build scaling infrastructure now.

## Availability

- Single-instance deployment is acceptable; no HA requirement for the hackathon.
- Graceful degradation: if the LLM provider is unreachable, deterministic analytics/dashboard features must continue to work; only the chat feature degrades.

## Security

- All financial data endpoints require authentication (JWT).
- Passwords hashed (bcrypt/argon2); no plaintext storage anywhere.
- Secrets (LLM API key, DB credentials) via environment variables, never committed.
- See `SECURITY_AND_PRIVACY.md` for full detail and hackathon-vs-production distinctions.

## Privacy

- All demo data is synthetic; no real user financial data is required or requested.
- If a user account system is added, each user can only access their own data (row-level ownership checks on every query).

## Explainability

- Every numeric output must be traceable to either a raw data aggregation or a named calculation function.
- Every prediction must state its confidence and the primary factors behind that confidence.
- The LLM must never be the sole source of a financial number.

## Reliability

- Financial calculation functions must be covered by unit tests with known expected outputs (see `TESTING_STRATEGY.md`).
- The system must handle missing/incomplete data without crashing — it should degrade to "insufficient data" states.

## Maintainability

- Clear separation of concerns: ingestion, categorization, analytics, forecasting, risk, recommendation, simulation, and conversational layers are independent modules with defined interfaces (see `BACKEND_ARCHITECTURE.md`).
- Configuration (thresholds, buffer defaults) centralized, not hardcoded across files.

## Observability

- Structured logging for: ingestion events, recalculation triggers, risk detections, recommendation generations, LLM tool calls (inputs/outputs, excluding secrets).
- MVP: console/file logging is sufficient; no dedicated observability stack required.

## Accessibility

- Dashboard should meet basic accessibility practices: sufficient color contrast, keyboard navigability of primary actions, alt text on icons, and no information conveyed by color alone (e.g., risk severity uses icon + label + color).

## Usability

- No page in the app should show a number without a label of what it is (fact/prediction/recommendation) and, for money, currency and period.
- Empty/insufficient-data states must explain what's missing and, where possible, what would resolve it (e.g., "add at least 2 months of transactions to enable forecasting").
