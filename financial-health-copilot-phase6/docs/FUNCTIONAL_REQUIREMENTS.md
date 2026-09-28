# Functional Requirements

## A. Financial Data Ingestion

- FR-A1: System shall ingest transactions with fields: date, amount, direction (debit/credit), merchant (raw string), account reference.
- FR-A2: System shall ingest account records (checking/savings/credit card/loan/investment) with type, balance, and metadata.
- FR-A3: System shall ingest income records, either as detected recurring credit transactions or explicit user-declared income sources (amount, frequency, source name).
- FR-A4: System shall ingest loan records: principal, interest rate, term, start date, payment schedule.
- FR-A5: System shall ingest credit card records: limit, current balance, statement date, minimum due.
- FR-A6: System shall ingest investment holdings (MVP: balance snapshot only, no transaction-level trading data).
- FR-A7: System shall support bulk import via CSV/JSON seed files (MVP) and expose an ingestion API for future integrations.
- FR-A8: System shall support incremental ingestion (new transactions appended without reprocessing the entire history from scratch where possible).

## B. Categorization

- FR-B1: System shall assign each transaction a category from a fixed taxonomy (e.g., Groceries, Dining, Transport, Utilities, Rent, Subscriptions, Entertainment, Healthcare, Debt Payment, Income, Transfer, Other).
- FR-B2: Categorization shall use deterministic rule/keyword matching against merchant name (MVP); confidence is reduced for unmatched merchants, which fall into "Uncategorized" rather than a guessed category.
- FR-B3: System shall normalize merchant names (e.g., "SWIGGY*ORDER1234" → "Swiggy") via pattern stripping rules.
- FR-B4: System shall detect recurring payments by grouping transactions with the same normalized merchant and similar amount (±10%) recurring at a regular interval (±3 days tolerance) across ≥2 cycles.
- FR-B5: Users shall be able to manually correct a transaction's category; corrections shall be remembered for future matching of the same merchant.

## C. Financial Health

- FR-C1: System shall compute total income, total expenses, fixed expenses, variable expenses, and discretionary expenses per period.
- FR-C2: System shall compute savings and savings rate per period.
- FR-C3: System shall compute debt-to-income ratio, debt service ratio, and credit utilization per debt account and in aggregate.
- FR-C4: System shall compute a cash buffer (days of runway at current balance vs. average daily burn).
- FR-C5: System shall compute a composite "financial health indicator" (0–100 score, MVP: transparent weighted rule, not a black-box ML model) summarizing the above.
- FR-C6: All metrics in this section shall be computed via pure deterministic functions with unit tests; the LLM shall never compute these values itself.

## D. Risk Detection

- FR-D1: System shall detect a **low cash buffer** risk when projected buffer falls below a configurable threshold (default: 5 days).
- FR-D2: System shall detect an **upcoming cash-flow gap** when a forecasted date exists where projected balance goes negative or below the user's buffer preference.
- FR-D3: System shall detect **unusually high spending** in a category when current-period spend exceeds the trailing 3-period average by a configurable margin (default: 30%).
- FR-D4: System shall detect **recurring payment burden** when total recurring obligations exceed a configurable share of income (default: 50%).
- FR-D5: System shall detect **debt pressure** when debt service ratio exceeds a configurable threshold (default: 40%) or credit utilization exceeds 70%.
- FR-D6: System shall detect **income volatility** when income coefficient of variation across recent periods exceeds a configurable threshold.
- FR-D7: System shall detect **unusual transaction behavior** (e.g., a single transaction >3x the average transaction size in its category).
- FR-D8: Every detected risk shall carry: condition triggered, severity (Low/Medium/High), evidence (specific numbers), and confidence.

## E. Recommendations

- FR-E1: System shall generate personalized recommendations from active risks/opportunities, never generic/static advice text.
- FR-E2: Each recommendation shall include: title, reason, evidence, concrete action, expected impact (quantified), confidence, priority, and assumptions.
- FR-E3: System shall rank recommendations by a transparent priority score (severity × confidence × impact magnitude), not a subjective/moral framing.
- FR-E4: System shall deduplicate recommendations addressing the same underlying risk.
- FR-E5: System shall suppress recommendations when supporting data is insufficient (e.g., <2 cycles of history) rather than emit a low-confidence guess as if certain.
- FR-E6: System shall detect and avoid presenting conflicting recommendations simultaneously (e.g., "increase debt payment" and "increase savings" competing for the same surplus) — MVP resolves by ranking, not by blocking.

## F. Conversational Assistant

- FR-F1: System shall accept free-form natural-language questions about spending, savings, debt, cash flow, and affordability.
- FR-F2: System shall classify user intent and route to the correct deterministic tool(s) before generating a response.
- FR-F3: System shall support basic follow-up/context (e.g., "what about last month?" after a spending question) within a chat session.
- FR-F4: Every response shall label which parts are fact, prediction, or recommendation.
- FR-F5: System shall decline to answer (rather than fabricate) when required data is missing, and shall state what's missing.

## G. What-If Analysis

- FR-G1: System shall support what-if simulations for: reduce spending (category, amount), increase savings (amount), extra debt repayment (amount), delay a purchase (amount, date), modify/cancel a recurring expense, and change income assumption (amount or %).
- FR-G2: Each simulation shall produce a baseline projection and a proposed-scenario projection using the same underlying forecasting engine.
- FR-G3: Simulation output shall include: projected balance, savings, debt balance/payoff timeline, cash buffer, and any risk status changes, compared side by side.
- FR-G4: System shall validate simulation inputs for realism (e.g., cannot reduce a category's spend below ₹0, cannot allocate more than available surplus) and return a clear validation error otherwise.

## H. Timeline / History

- FR-H1: System shall persist a timestamped snapshot of computed metrics, risks, and recommendations each time they are recalculated.
- FR-H2: System shall, on request, show how a specific recommendation changed (or was resolved) between two points in time.
- FR-H3: System shall recalculate metrics, risks, and recommendations automatically whenever new transactions/income/debt/expense data is ingested.
- FR-H4: Demo/UI shall support manually triggering a "new data arrived" event to showcase FR-H3 live.
