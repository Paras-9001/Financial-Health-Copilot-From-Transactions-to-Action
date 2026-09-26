# Security and Privacy

This is financial data. Every section below states the **hackathon MVP implementation** and the **production requirement** it stands in for, so the gap is explicit rather than accidental.

## Authentication

- **MVP:** Email/password with JWT (short-lived access token, e.g., 24h for demo convenience).
- **Production:** Shorter-lived access tokens + refresh tokens, MFA option, rate-limited login attempts.

## Authorization

- **MVP:** Every query is scoped by `user_id` extracted from the verified JWT; no endpoint accepts a `user_id` from the request body/query for data access — it's always derived server-side from the token.
- **Production:** Add row-level security policies in Postgres as a defense-in-depth layer beyond application-level checks.

## Encryption

- **MVP:** TLS in transit (via hosting provider default). Data at rest relies on the managed Postgres provider's default encryption.
- **Production:** Field-level encryption for the most sensitive fields (account numbers if ever ingested) plus a KMS-managed key strategy.

## Secrets

- **MVP:** `.env` file (gitignored) for DB credentials and LLM API key; never logged, never sent to the frontend.
- **Production:** Secrets manager (e.g., AWS Secrets Manager/Vault), automatic rotation.

## PII and Financial Data

- **MVP:** Synthetic data only — no real PII/financial data is ever ingested, which meaningfully lowers real-world risk during the hackathon.
- **Production:** Data classification policy distinguishing PII (name/email) from financial data (transactions/balances), with the latter subject to stricter access logging.

## Database Security

- **MVP:** Single application DB user with least-privilege grants (no superuser access from the app).
- **Production:** Separate read/write roles, network-level restriction (VPC/private networking), audit logging on sensitive tables.

## API Security

- **MVP:** Input validation via Pydantic on every endpoint; standard CORS restricted to the known frontend origin; basic rate limiting on `/auth/*` to deter brute force.
- **Production:** WAF, full rate limiting across all endpoints, request signing for any future third-party integrations.

## Logging

- **MVP:** Structured logs for ingestion, recalculation, risk detection, recommendation generation, and agent tool calls — logs include `user_id` and event type but never raw transaction descriptions or full financial detail beyond what's needed to debug.
- **Production:** Log redaction policy, centralized log storage with access controls, retention limits.

## Data Retention

- **MVP:** No explicit retention policy needed (synthetic/demo data); document intended default (e.g., 24 months) for future real deployment.
- **Production:** User-configurable retention, automatic purging beyond the configured window.

## Data Deletion

- **MVP:** `DELETE /users/me` cascades via FK `ON DELETE CASCADE` to remove all associated data — sufficient for demo "right to be forgotten" simulation.
- **Production:** Soft-delete with a grace period, verified deletion across backups.

## Prompt Injection

- User-supplied free text that reaches the LLM (chat messages, and in principle any transaction description shown to the LLM) is always passed as clearly delimited **data**, never concatenated into the system/instruction prompt. The agent's system prompt explicitly instructs the model to treat content inside data fields as informational only, never as new instructions.
- Tool-call arguments proposed by the LLM are validated server-side against strict schemas before execution — the LLM cannot, for example, cause a query for another `user_id` because `user_id` is never an LLM-controllable parameter; it's injected server-side from the authenticated session.

## LLM Data Exposure

- Only the minimum structured context needed for the current turn is sent to the LLM provider (see `AI_ARCHITECTURE.md` "Structured Context") — not raw database dumps, not other users' data.
- **MVP:** Uses the LLM provider's standard API (data may be used per their standard terms — documented, not hidden, in the demo).
- **Production:** Use a provider agreement/offering with no training-data retention for enterprise/financial use cases, and consider redacting merchant-level detail before sending to the LLM where not needed for the answer.

## Third-Party AI Provider Considerations

- Provider outage or latency spikes must not take down the whole app — deterministic dashboard/analytics endpoints have zero dependency on the LLM provider being reachable (see `BACKEND_ARCHITECTURE.md` error handling); only `/chat/*` degrades.
- API keys scoped to the minimum necessary provider permissions; no client-side exposure of the key under any circumstance (all LLM calls happen server-side).
