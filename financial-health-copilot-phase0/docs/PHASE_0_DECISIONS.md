# Phase 0 implementation decisions

Authority: the supplied `IMPLEMENTATION_PLAN.md`, `CONFIGURATION.md` and supporting documents. These notes resolve implementation details without changing the agreed phase boundary. The original Markdown requirements are preserved unchanged.

## Scope interpretation

Phase 0 explicitly calls for a PostgreSQL schema migration; Phase 1 calls for domain models and repositories. Therefore this delivery creates the full 19-table schema now, but only maps the User ORM model and implements auth/profile access. It does not add transaction, account, seed, forecast, recommendation or chat behavior.

The original local setup guide describes a completed product. A separate Phase 0 guide prevents its future seed and financial endpoint instructions being mistaken for working functionality.

## Decisions

| Area | Choice | Reason and consequence |
|---|---|---|
| Frontend | Next.js App Router, TypeScript, Tailwind, TanStack Query | Matches the uploaded stack; only two screens and the session provider are needed now |
| API | FastAPI, SQLAlchemy and Alembic | Modular monolith and explicit migration history |
| Password hashing | bcrypt, cost 12, reject over 72 UTF-8 bytes | Matches the specified hash family; prevents silent truncation |
| JWT library | PyJWT instead of python-jose/passlib wrappers | The current official FastAPI guide supports direct PyJWT integration; bcrypt remains the specified hashing scheme |
| Session | 30-minute HS256 token with required issuer, audience, subject and expiry | More limited than the illustrative 24-hour demo token; no refresh-token implementation yet |
| Browser storage | Memory only | Avoids persisting bearer tokens in localStorage; refresh requires login |
| Logout | Clears browser token, profile and query cache | No server token revocation; a separately copied token remains valid until expiry |
| Email policy | Trim and lowercase the entire address | Practical demo identity convention; enforced by database check and unique constraint |
| Database roles | Bootstrap administrator, separate migration owner and runtime data role | API process has no superuser or schema-owner credentials |
| Compose | Three long-running services plus one-shot migration | Deterministic startup ordering; migrations do not race inside API workers |
| Rate limiting | Bounded in-memory client-IP limiter, 10 attempts/minute | Suitable for one local API process; not distributed production enforcement |
| Config units | `_PCT` values use percentage points; CV/weights/scores use Decimal fractions | Removes the ambiguity between `30` and `0.30` |
| Config names | Uppercase aliases for user default names; explicit names for unnamed bands/rounding | Every policy value has one importable location |
| Migration defaults | Frozen literal defaults in historical DDL | Importing future runtime policy into old migrations would make replay nondeterministic |
| Fonts | System font fallback; no network font request | Reliable offline build and readable scaffold |
| AI | No provider calls or key dependency | AI implementation belongs to Phase 5 |

## Configuration mapping

The 36 named entries in the supplied configuration document map to uppercase names in `app/core/config.py`. `preferred_buffer_days` maps to `PREFERRED_BUFFER_DAYS`, `currency` to `CURRENCY`, and `forecast_horizon_default_days` to `FORECAST_HORIZON_DEFAULT_DAYS`.

The unnamed confidence bands map to `CONFIDENCE_HIGH_MIN`, `CONFIDENCE_MEDIUM_MIN`, and `CONFIDENCE_LOW_MIN`. Values below the last boundary are insufficient. The simulation-specific 180-day limit is `SIMULATION_HORIZON_MAX_DAYS`. Prediction rounding cutoffs/steps use the `PREDICTION_ROUNDING_*` prefix. This phase defines these constants; it does not yet implement confidence scoring or rounding algorithms.

Tests parse the supplied Markdown values, compare every named default, check the additional bands/rounding rules, and prevent policy names being redefined in consumers. Historical migrations are excluded from the redefinition guard. The actual user creation model references `config.PREFERRED_BUFFER_DAYS`.

## Schema completion choices

The document gives some tables as full SQL and others as dictionaries. The migration fills in PKs, timestamps, FKs and described enum constraints consistently. It adds basic nonnegative/range checks where implied, verifies loan payment principal plus interest equals total, and uses owner-safe composite links for a loan's account and a recommendation's risk event. These additions prevent obvious integrity errors without adding new domain features.

The original signed/nonzero `transactions.amount` constraint is preserved because the source allows it, even though direction is separately stored. Phase 1 must settle normalization before ingestion. No transaction endpoint currently accepts an ambiguous signed value.

Shared merchants/categories have no user owner as specified. Future user-specific merchant patterns will require an explicit schema change. Database row-level security is deferred by the supplied MVP security document; later repositories must enforce ownership on every query and relationship.

## References checked

- [Next.js installation](https://nextjs.org/docs/app/getting-started/installation): framework and runtime setup.
- [FastAPI JWT guide](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/): direct JWT and password-hashing integration.

These references support implementation mechanics. They do not replace the project's requirements or imply production security certification.
