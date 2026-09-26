# AI Agent Design

## Agent Decision Flow

```mermaid
flowchart TD
    Q[User Question] --> Classify[Classify Intent]
    Classify --> Identify[Identify Required Data/Tools]
    Identify --> Call[Call Deterministic Tool(s)]
    Call --> Check{Sufficient Data?}
    Check -- No --> Insufficient[Return insufficient_data explanation]
    Check -- Yes --> Simulate{Requires What-If?}
    Simulate -- Yes --> RunSim[Call simulate_action]
    Simulate -- No --> Compose
    RunSim --> Compose[Compose Grounded Response]
    Compose --> Label[Label Fact / Prediction / Recommendation]
    Label --> Return[Return to User]
```

## Tool Definitions

### `get_financial_summary(user_id, period)`
- **Purpose:** Return the core metric set (income, expenses, savings, DTI, buffer, health score) for a period.
- **Inputs:** `user_id: UUID`, `period: {start_date, end_date}` (default: trailing 30 days).
- **Outputs:** `{ metrics: {...}, confidence: {...}, period }`.
- **Validation:** `end_date >= start_date`; period cannot exceed available history.
- **Example:** `get_financial_summary(user_id, {last_30_days}) → { total_income: 60000, total_expenses: 48000, savings_rate: 20.0, ... }`

### `get_transactions(user_id, filters)`
- **Purpose:** Return raw or lightly aggregated transactions matching filters.
- **Inputs:** `filters: {category?, merchant?, date_range?, min_amount?, max_amount?}`.
- **Outputs:** `{ transactions: [...], count, total_amount }`.
- **Validation:** date_range within supported history window.
- **Example:** `get_transactions(user_id, {category: "Dining", last_30_days}) → { count: 14, total_amount: 7200 }`

### `get_spending_by_category(user_id, period)`
- **Purpose:** Category-level breakdown with % of total.
- **Outputs:** `{ categories: [ {name, amount, pct_of_total, type} ] }`.

### `get_recurring_expenses(user_id)`
- **Purpose:** List confirmed/candidate recurring payments.
- **Outputs:** `{ recurring: [ {merchant, amount, frequency, next_expected_date, status} ] }`.

### `get_debt_summary(user_id)`
- **Purpose:** Aggregate debt position across loans/cards.
- **Outputs:** `{ total_debt, dti, debt_service_ratio, credit_utilization, loans: [...], cards: [...] }`.
- **Validation:** Returns `insufficient_data` if no debt accounts exist (not a zero).

### `get_cash_flow_forecast(user_id, horizon_days)`
- **Purpose:** Projected daily balance with confidence band.
- **Inputs:** `horizon_days` (default 30, max 90).
- **Outputs:** `{ daily_projection: [...], confidence, method }`.

### `get_risk_events(user_id, status)`
- **Purpose:** Active or historical risk events.
- **Outputs:** `{ risks: [ {type, severity, evidence, confidence, detected_at} ] }`.

### `calculate_affordability(user_id, amount, target_date)`
- **Purpose:** Determine whether a purchase is affordable without breaching the buffer preference.
- **Inputs:** `amount: decimal`, `target_date: date (optional, default: today)`.
- **Outputs:** `{ verdict: "yes"|"caution"|"no", resulting_buffer_days, confidence, reasoning_basis }`.
- **Validation:** `amount > 0`.

### `simulate_action(user_id, action_type, params)`
- **Purpose:** Run a what-if scenario (see `IMPACT_SIMULATION.md`).
- **Inputs:** `action_type: enum`, `params: {...type-specific...}`.
- **Outputs:** `{ baseline: {...}, proposed: {...}, delta: {...}, confidence }`.
- **Validation:** Type-specific (e.g., cannot reduce a category below its ₹0 floor).

### `get_recommendations(user_id, status)`
- **Purpose:** Current ranked recommendation list.
- **Outputs:** `{ recommendations: [ {...RECOMMENDATION_ENGINE schema...} ] }`.

## Intent Classification (MVP approach)

A lightweight classifier (LLM-based, single call, constrained to a fixed label set) maps the user's question to one of: `spending`, `savings`, `debt`, `cash_flow`, `affordability`, `recommendation`, `what_if`, `general/unclear`. This label determines the initial tool(s) to call; the LLM can still call additional tools if the first result reveals it needs more (multi-step tool use), e.g., an affordability question also pulling `get_cash_flow_forecast`.

## Validation Layer

Every tool call is validated by the orchestrator (not trusted blindly from the LLM's arguments) against the tool's declared JSON schema before execution — rejecting out-of-range dates, negative amounts, or unknown categories with a clear error the LLM can relay or correct.

## Multi-Tool Example

**User:** "Can I afford a ₹30,000 laptop next week and how would it affect my buffer?"

1. Classify → `affordability`.
2. Call `calculate_affordability(user_id, 30000, next_week_date)`.
3. Result includes `resulting_buffer_days`; if `verdict = "caution"`, agent also calls `get_cash_flow_forecast` to explain *why* (e.g., a rent payment due the same week).
4. Compose response labeling the buffer figure as OBSERVED (current buffer) vs. PREDICTED (post-purchase buffer, medium confidence).
