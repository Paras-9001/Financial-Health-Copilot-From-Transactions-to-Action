# Demo Scenarios

## Scenario 1 — Dashboard First Look (Persona A)

- **Initial state:** Balance ₹9,000, buffer 5.6 days, dining trending 42% above average.
- **User action:** Opens dashboard.
- **Observed:** Income ₹60,000, expenses ₹48,000, savings rate 20%.
- **Prediction (medium):** Dining spend on track to hit ~₹15,000 this month vs. ₹5,080 average.
- **Recommendation:** Reduce dining by ₹2,500 this month.
- **Expected impact:** Buffer 5.6 → ~8 days.
- **UI elements:** Health score card, fact row, prediction card with confidence badge, recommendation card with impact preview.

## Scenario 2 — Conversational Affordability Check (Persona A)

- **Initial state:** Same as above, mid-month, rent due in 5 days.
- **User question:** "Can I afford a ₹30,000 laptop next week?"
- **System analysis:** `calculate_affordability` → factors in upcoming rent (₹15,000) and EMI (₹8,000).
- **Observed:** Current balance ₹9,000 + expected inflows before purchase date: none.
- **Prediction:** Resulting buffer would go to -2 days (medium confidence).
- **Verdict:** No / Caution.
- **UI elements:** Chat bubble with verdict, fact/prediction breakdown, link to "Simulate delaying this purchase."

## Scenario 3 — Debt What-If (Persona A)

- **Initial state:** Personal loan ₹1,20,000 outstanding, 14 months remaining, ₹8,200 interest remaining.
- **User action:** Opens What-If Simulator, selects "Extra debt payment," enters ₹10,000.
- **Baseline:** 14 months, ₹8,200 interest.
- **Proposed:** 11 months, ₹6,100 interest.
- **Trade-off shown:** Cash buffer drops from 9 to 5 days immediately after payment.
- **UI elements:** Side-by-side comparison panel, trade-off callout banner.

## Scenario 4 — Income Volatility Risk (Persona B)

- **Initial state:** Last 4 months' income: ₹95,000, ₹42,000, ₹88,000, ₹35,000 (CV ≈ 0.38).
- **System analysis:** Income volatility risk triggered (medium severity).
- **Recommendation:** Build a buffer during high-income months — increase savings by ₹15,000 in months where income exceeds ₹80,000.
- **Expected impact:** Projected buffer during a low-income month improves from 3 days to 11 days.
- **UI elements:** Risk card with income bar chart showing volatility, recommendation tied explicitly to the volatility evidence.

## Scenario 5 — Debt Pressure from High Utilization (Persona B)

- **Observed:** Credit utilization 90.7% (₹68,000 / ₹75,000).
- **Prediction:** Continuing at current pay-down rate, utilization stays above 70% for 4+ more months (medium confidence).
- **Recommendation:** Redirect ₹5,000/month from discretionary spend to extra card payments.
- **Expected impact:** Utilization drops to <70% in ~3 months instead of ~7.

## Scenario 6 — Surplus Opportunity (Persona C)

- **Observed:** Savings rate 38%, no debt, healthy buffer (45+ days).
- **System analysis:** No risks triggered; opportunity detection surfaces a "surplus" recommendation instead.
- **Recommendation:** Given consistent surplus, consider increasing SIP/investment contribution by ₹10,000/month.
- **Expected impact:** Projected investment balance in 12 months increases by ~₹1,25,000 (illustrative, deterministic compounding calculation, not investment advice).

## Scenario 7 — THE Key Demo: Before/After Recalculation (Persona A)

This scenario directly demonstrates the explicit requirement that recommendations change as new data arrives.

**BEFORE:**
- Balance ₹9,000, buffer 5.6 days.
- Active recommendation: "Reduce dining spending by ₹2,500 this month" (P0, confidence medium).
- No active cash-flow-gap risk (buffer is low but forecast doesn't yet show a breach).

**NEW DATA ARRIVES:**
- User (or demo operator) submits a new transaction: an unplanned ₹12,000 medical expense today.

**RECALCULATION (visible via `<RecalculationToast>`):**
- Snapshot recomputed: balance now -₹3,000 effectively against upcoming obligations.
- New risk detected: **Upcoming cash-flow gap**, high severity, breach projected in 3 days.
- Old recommendation ("reduce dining ₹2,500") is now marked `superseded` — it's no longer sufficient.

**AFTER:**
- New top recommendation: "This month, reduce discretionary spending (Dining + Shopping) by a combined ₹8,000 and consider paying only the minimum due (₹1,500) on your credit card instead of ₹5,000, to avoid a cash shortfall." (P0, high confidence — now grounded in a confirmed shortfall, not just a trend.)
- Expected impact: resolves the projected breach, restoring buffer to 6 days.
- UI shows a clear diff: "Your top recommendation changed because of a new ₹12,000 expense on Sep 26."

## Scenario 8 — Insufficient Data Handling (new user, Persona template not yet seeded)

- **User action:** Asks "How's my debt looking?" with zero loan/credit-card data ingested.
- **System response:** "I don't have any debt information for your account yet, so I can't answer that. Add a loan or credit card to see this."
- **UI elements:** `<InsufficientDataCard>` in both dashboard and chat contexts, demonstrating the system never fabricates a zero-debt answer.
