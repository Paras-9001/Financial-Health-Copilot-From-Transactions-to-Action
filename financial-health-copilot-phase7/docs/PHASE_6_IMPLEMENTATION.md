# Phase 6 implementation

Phase 6 starts from the corrected Phase 5 repository and follows `IMPLEMENTATION_PLAN.md`, `FRONTEND_ARCHITECTURE.md`, `UI_UX_DESIGN.md`, `ONBOARDING_AND_DATA_IMPORT.md`, `API_SPECIFICATION.md`, `PRODUCT_REQUIREMENTS.md`, and `USER_STORIES.md` from the original core documentation.

## Design system

- Exact light-theme color tokens from `UI_UX_DESIGN.md`.
- 12/14/16/20/28/40-oriented typography scale with tabular numerals.
- Canonical circle/diamond/triangle/outline badges for Fact, Prediction, Recommendation, and Assumption.
- Confidence shown as text plus color; severity likewise never relies on color alone.
- Skeleton loading, section-level retry errors, and explicit insufficient-data cards.
- Responsive single/two/twelve-column behavior with keyboard-visible focus states.

## Product coverage

All nine specified application pages are implemented. The dashboard follows the four-part product loop. Recharts renders spending and cash-flow data, with adjacent textual descriptions for accessibility. Chat reuses the same labeled claim cards as the dashboard.

All three onboarding modes are present: persona seeding, CSV preview/confirm, and manual account/income/loan/card/transaction forms.

## State and API

TanStack Query owns API server state and cache invalidation. Adding or correcting a transaction invalidates transactions, summary, risks, and recommendations. Authentication uses the documented MVP local-storage approach; production should replace it with secure HTTP-only session cookies.

## Phase 7 handoff

The frontend already uses real endpoints. Phase 7 should focus on full live-stack contract testing, the recommendation diff experience, recalculation toast, and final loading/error polish discovered during integration.
