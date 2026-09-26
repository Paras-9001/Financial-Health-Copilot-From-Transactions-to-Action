# Product Requirements

## Problem Definition

Individuals have financial data spread across bank accounts, credit cards, loans, and investments, but no system connects that data into a coherent understanding of their financial health, what's likely to happen next, and what they should do about it. Existing personal finance apps mostly visualize the past (dashboards, pie charts) without projecting the future or recommending quantified actions.

## Target Users

- **Primary:** Working professionals with a mix of fixed income, recurring expenses, and at least one debt obligation (credit card or loan), who check their finances reactively rather than proactively.
- **Secondary:** Freelancers/gig workers with variable income who need cash-flow foresight more than budgeting.
- **Tertiary:** Financially disciplined savers who want to stress-test decisions ("what if I make this purchase") before acting.

## User Pain Points

- "I don't know where my money actually goes each month."
- "I get surprised by low balances near the end of the month."
- "I don't know if I can afford something without doing manual math."
- "Generic advice like 'save more' doesn't tell me what to actually do."
- "I don't know if paying extra on my loan is worth the hit to my cash cushion."
- "My financial app shows numbers but doesn't tell me anything I can act on."

## Product Vision

A financial copilot that behaves like a competent, honest financial analyst sitting next to the user — one who separates what it knows for certain from what it's predicting, always ties advice to a number, and shows the user what happens next if they take that advice.

## Product Goals

1. Give users a single, trustworthy view of their financial health.
2. Detect risks and opportunities before they become problems.
3. Turn every insight into a specific, quantified next action.
4. Let users interrogate their finances conversationally.
5. Make the system's reasoning fully transparent (fact vs. prediction vs. recommendation).
6. Show that the system adapts as new data arrives.

## Non-Goals (MVP)

- Real bank account integration (Plaid/Open Banking) — synthetic data only.
- Investment portfolio optimization or trading advice.
- Tax filing or tax optimization.
- Multi-currency support.
- Multi-user / shared household accounts.
- Mobile native apps (web-responsive only).
- Credit score simulation.

## Core Value Proposition

"Understand my financial situation → identify what may happen next → tell me what I can do → show me the expected impact." Every major feature must trace this chain; the app is not a dashboard.

## MVP Scope

- Synthetic multi-persona seed data (transactions, income, debt, recurring payments).
- Deterministic financial analytics engine (income, expenses, savings, debt, cash flow).
- Rule-based cash-flow forecasting with confidence.
- Rule-based risk detection.
- Recommendation engine with quantified expected impact.
- What-if / impact simulation for at least 4 action types.
- LLM-powered conversational assistant grounded via tool-calling.
- Web dashboard covering: overview, transactions, spending, debt, cash flow, recommendations, what-if simulator, chat.
- Demonstrable recalculation when new data is added.
- Simple email/password authentication.

## Stretch Goals

- Persisted recommendation history / outcome tracking over time.
- Multiple synthetic personas selectable in the demo.
- Lightweight ML model for spending forecast (in addition to the rule-based baseline).
- Exportable financial health report (PDF).
- Voice input for chat.

## Success Criteria

- A user (or judge) can, within 2 minutes, see their financial health, one clear risk, one clear recommendation with a numeric impact, and ask a free-form question that gets answered correctly.
- Adding a transaction visibly changes at least one recommendation and its rationale.
- No financial calculation is ever produced solely by the LLM without a backing deterministic function.
- Every recommendation on screen has visible evidence and a confidence label.

## Primary User Journeys

1. **First look:** User logs in → sees dashboard with health score, top risk, top recommendation.
2. **Investigate:** User clicks into "Cash Flow" → sees forecast with confidence band and the risk event that generated it.
3. **Ask a question:** User types "Can I afford a ₹30,000 laptop next week?" → gets grounded yes/no with numbers.
4. **Simulate:** User opens What-If Simulator → tries "pay ₹10,000 extra on loan" → sees before/after comparison.
5. **See adaptation:** User (or demo script) adds a new large transaction → dashboard and recommendations update, and the user can see *why* they changed.

## Major Product Features & Prioritization

| Feature | Priority |
|---|---|
| Financial data model + synthetic data seeding | P0 |
| Deterministic analytics engine (income/expense/savings/debt) | P0 |
| Cash-flow forecasting (rule-based) | P0 |
| Risk detection engine | P0 |
| Recommendation engine with expected impact | P0 |
| Fact/Prediction/Recommendation/Confidence labeling | P0 |
| Conversational AI (tool-calling, grounded) | P0 |
| What-if / impact simulation | P0 |
| Dashboard UI (overview, spending, debt, cash flow) | P0 |
| Recalculation on new transaction | P0 |
| Recommendation history / "why did this change" view | P1 |
| Multiple selectable personas in UI | P1 |
| Category-level drill-down charts | P1 |
| Lightweight ML forecast model | P2 |
| PDF export of financial health report | P2 |
| Voice input | P2 |
