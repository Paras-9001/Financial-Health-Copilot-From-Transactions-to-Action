# User Stories

Each story includes acceptance criteria, relevant data, expected system behavior, and edge cases.

---

## US-01: Understand where money goes

**Story:** As a user, I want to understand where my money goes so that I can control unnecessary spending.

- **Acceptance Criteria:**
  - User sees a category breakdown of spending for a selectable period (default: last 30 days).
  - Top 3 categories are highlighted with amount and % of total spend.
  - Discretionary vs. fixed spending is distinguished.
- **Relevant data:** transactions, categories, merchants.
- **Expected behavior:** System aggregates transactions by category, computes totals and percentages deterministically, renders a chart plus a one-line natural-language summary from the LLM layer (grounded in the aggregation).
- **Edge cases:** No transactions in period → show "insufficient data" state, not a zeroed chart. Uncategorized transactions → shown under "Uncategorized" rather than silently dropped or guessed with false confidence.

---

## US-02: Affordability check

**Story:** As a user, I want to know whether I can afford a purchase so that I don't create future cash-flow stress.

- **Acceptance Criteria:** User can enter an amount and (optional) date; system returns a clear affordability verdict with reasoning and impact on projected buffer.
- **Relevant data:** current balance, projected income/expenses, cash-flow forecast, user's preferred buffer setting.
- **Expected behavior:** Runs `calculate_affordability()` deterministically against the forecast; returns verdict (Yes/Caution/No), resulting buffer, and confidence based on forecast horizon.
- **Edge cases:** Purchase date beyond forecast horizon → confidence downgraded and stated explicitly. No buffer preference set → system uses a sane default (e.g., 7 days of average expenses) and states the assumption.

---

## US-03: Recurring expense visibility

**Story:** As a user, I want to know which recurring expenses are affecting my monthly budget.

- **Acceptance Criteria:** User sees a list of detected recurring payments with amount, frequency, next expected date, and % of monthly income they consume.
- **Relevant data:** transaction history (≥2 cycles), recurring_transactions table.
- **Expected behavior:** Recurring detection pipeline groups transactions by merchant + amount-similarity + interval regularity; confidence scales with number of confirmed cycles.
- **Edge cases:** Only one occurrence seen → flagged as "possible recurring, unconfirmed" rather than asserted as fact. Amount varies slightly (e.g., variable electricity bill) → detected as recurring with a range, not a fixed value.

---

## US-04: Debt payoff impact

**Story:** As a user, I want to understand how paying extra toward debt would affect my finances.

- **Acceptance Criteria:** User can specify an extra payment amount; system shows before/after payoff timeline, interest saved, and impact on short-term cash buffer.
- **Relevant data:** loan principal, rate, term, payment history, current cash flow.
- **Expected behavior:** Deterministic amortization recalculation for baseline vs. proposed scenario; both timelines and interest totals shown side by side.
- **Edge cases:** Extra payment exceeds available buffer → system warns of resulting cash-flow risk rather than only showing the debt benefit. Multiple debts exist → user must pick one (MVP does not auto-optimize across debts).

---

## US-05: Conversational financial questions

**Story:** As a user, I want to ask questions about my finances in natural language.

- **Acceptance Criteria:** User can type free-form questions; responses are grounded in real computed values, cite the underlying facts, and label predictions vs. facts.
- **Relevant data:** all financial data, via agent tool calls.
- **Expected behavior:** Intent classification → tool selection → deterministic computation → LLM composes a grounded natural-language answer strictly from tool outputs.
- **Edge cases:** Ambiguous question ("How am I doing?") → agent asks a clarifying follow-up or gives a structured summary rather than guessing intent. Question requires data the system doesn't have (e.g., investment questions when no investment data exists) → system states the limitation, doesn't fabricate.

---

## US-06: Risk awareness

**Story:** As a user, I want to be warned about an upcoming cash-flow problem before it happens.

- **Acceptance Criteria:** Dashboard surfaces active risk events with severity, evidence, and a recommended action.
- **Relevant data:** cash-flow forecast, recurring obligations, historical spending volatility.
- **Expected behavior:** Risk rules evaluate forecast output each time it's regenerated; new/changed risks are visibly flagged.
- **Edge cases:** Multiple risks active simultaneously → ranked by severity, not just listed chronologically. Risk resolves itself after new data (e.g., income arrives) → risk is marked resolved, not left stale.

---

## US-07: What-if exploration

**Story:** As a user, I want to explore hypothetical financial decisions before making them.

- **Acceptance Criteria:** User selects an action type (reduce spending, increase savings, extra debt payment, delay purchase, change recurring expense, income change) and parameters; system shows baseline vs. proposed comparison.
- **Relevant data:** current financial state, forecast engine, simulation engine.
- **Expected behavior:** Simulation reuses the same deterministic forecasting logic with modified inputs; never a separate, inconsistent calculation path.
- **Edge cases:** Unrealistic input (e.g., reduce spending by more than total spending) → validated and rejected with guidance. Compound what-ifs (multiple actions at once) → MVP supports one action at a time; stretch goal supports stacking.

---

## US-08: Seeing recommendations evolve

**Story:** As a user, I want to see how my recommendations change as my financial situation changes.

- **Acceptance Criteria:** After a new transaction/income/expense is added, previously shown recommendations are recalculated and any changes are visibly highlighted (new, changed, resolved).
- **Relevant data:** full transaction/recommendation history with timestamps.
- **Expected behavior:** Recommendation engine reruns on every relevant data change; diff against previous recommendation set is shown to the user.
- **Edge cases:** New data resolves a risk entirely → recommendation is marked resolved with an explanation, not silently removed.

---

## US-09: Trusting the numbers

**Story:** As a user, I want to know whether the app is showing me a fact or a guess.

- **Acceptance Criteria:** Every figure in the UI is visibly tagged as Fact, Prediction, Recommendation, or Assumption, with a confidence indicator on predictions.
- **Relevant data:** confidence scoring inputs (data completeness, freshness, history length).
- **Expected behavior:** UI components consume a `type` and `confidence` field from every API response and render consistent visual treatment.
- **Edge cases:** Insufficient history for a confident prediction → system explicitly states "insufficient data" rather than emitting a low-confidence number that looks the same as a high-confidence one.
