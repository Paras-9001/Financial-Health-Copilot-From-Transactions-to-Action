# Evaluation Metrics

## Product Metrics

| Metric | Definition | How to demonstrate |
|---|---|---|
| Insight usefulness | Subjective: does each dashboard insight lead to a clear next step? | Manual review checklist: every risk on screen has a corresponding recommendation |
| Recommendation relevance | % of recommendations tied to an active, real risk (not generic) | Audit generated recommendations against the "no generic advice" rule (RECOMMENDATION_ENGINE.md) |
| Task completion | % of the 5 primary user journeys (PRODUCT_REQUIREMENTS.md) completable without confusion | Manual walkthrough / judge dry-run |

## Technical Metrics

| Metric | Target (hackathon scale) | Measurement |
|---|---|---|
| API latency (analytics endpoints) | p95 < 500ms | Simple timing middleware/log |
| Forecast error | Backtest MAPE on held-out trailing period | Compare rolling-average forecast vs. actual outcome for synthetic persona history |
| Calculation accuracy | 100% match to hand-computed fixtures | Unit test suite (TESTING_STRATEGY.md) |
| Data processing accuracy | 0 duplicate transactions post-ingestion; >95% categorization match rate on seed data | Ingestion test assertions |

## AI Metrics

| Metric | Definition | Measurement |
|---|---|---|
| Groundedness | % of numeric claims in chat responses traceable to a tool result in that turn | Automated check against the fixed Q&A eval set |
| Hallucination rate | % of eval questions where an unsupported number appears | Same eval set; target 0% |
| Tool selection accuracy | % of eval questions where the correct tool(s) were called | Same eval set |
| Response correctness | % of eval questions where the final numeric answer matches the expected computed value | Same eval set |
| Confidence calibration | Qualitative: does "medium confidence" correspond to genuinely medium data completeness across sampled outputs? | Manual spot-check across personas with differing history lengths |

## Hackathon / Demo Metrics

| Metric | Target |
|---|---|
| Time to first insight | Dashboard shows health score + 1 risk + 1 recommendation within 2 seconds of login (seeded data) |
| Number of actionable insights on dashboard | ≥ 3 at all times for the demo persona (risk, recommendation, forecast) |
| Quality of impact simulation | Every recommendation's "expected impact" numbers reproduce exactly when run manually through `/simulate` |
| Explainability | Every number on screen has a visible label (fact/prediction/recommendation) and, for predictions, a "why" explanation reachable in ≤1 click |

## How to Demonstrate During the Hackathon

- Keep the eval Q&A set (20 questions) and expected tool calls/answers in a committed test file; run it live or show the passing test output during the demo/judging Q&A as evidence of groundedness.
- Show the unit test suite passing for financial calculations as proof of correctness rather than asserting it verbally.
- Use the "before/after" recalculation demo scenario (`DEMO_SCENARIOS.md`) as the live proof of adaptiveness rather than only describing it.
