# Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation | Fallback |
|---|---|---|---|---|
| Inaccurate financial calculations | Medium | High (undermines core trust proposition) | Table-driven unit tests against hand-computed fixtures for every formula; `Decimal` arithmetic throughout, no floats | Manually re-verify demo persona numbers before presenting |
| Hallucinated advice from the LLM | Medium | High | Strict tool-calling architecture, no-tool-no-number rule, post-response numeric cross-check against tool outputs | If detected, disable free-form chat for the demo and rely on structured dashboard views |
| Insufficient data for confident predictions | High (typical for any new user) | Medium | Explicit `insufficient_data`/low-confidence states rather than fabricated numbers; seed demo personas with enough history to avoid this in the live demo | Use pre-seeded personas with 3+ months of history for judging |
| Forecast uncertainty misread as precision | Medium | Medium | Always show confidence bands and labels, round predicted figures, never show false precision | UI review pass specifically checking every number has a label |
| Bad transaction categorization | Medium | Low–Medium | Rule/keyword-based categorization with clear "Uncategorized" fallback rather than a wrong guess; manual override supported | Pre-verify seed data categorizes correctly before demo |
| Over-reliance on LLM for core functionality | Medium | High | Architectural separation (`AI_ARCHITECTURE.md`) ensures dashboard/analytics work with zero LLM dependency | Demo the dashboard-only flow as a complete fallback path if chat fails live |
| Unrealistic/conflicting recommendations | Medium | Medium | Validation caps (can't reduce below ₹0, can't exceed surplus), shared-assumption disclosure for competing recommendations | Manual review of generated recommendations for the demo personas before presenting |
| Privacy/security concerns (financial data) | Low (synthetic data used) | High if misunderstood by judges | Explicitly state all demo data is synthetic; document hackathon-vs-production security gaps transparently (`SECURITY_AND_PRIVACY.md`) | Be ready to answer security questions directly rather than deflect |
| Integration complexity (frontend/backend/LLM converging) | Medium | Medium | Freeze API spec early, build frontend against mocks matching the spec from day one | Buffer time built into `DEVELOPMENT_PHASES.md` for integration fixes |
| Demo failure (live bug, network/LLM outage) | Medium | High | Rehearse the exact demo script and data state; deterministic features have zero external dependency | Pre-recorded backup video of the full demo flow |
| LLM provider latency during live demo | Medium | Medium | Low `max_tokens`, minimal context, single-turn tool calls where possible | Fallback templated response after a timeout threshold (e.g., 6s) |
| Scope creep beyond hackathon time | High | Medium | Strict P0/P1/P2 prioritization (`PRODUCT_REQUIREMENTS.md`); MVP scope frozen after Phase 0 | Cut P1/P2 features per the 24-hour compressed plan if behind schedule |
