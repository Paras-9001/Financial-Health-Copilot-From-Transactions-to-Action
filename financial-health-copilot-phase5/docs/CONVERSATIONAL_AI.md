# Conversational AI

## Supported Question Categories

**Spending**
- "Where did I spend the most?" → `get_spending_by_category`
- "Why did my spending increase?" → `get_spending_by_category` (current vs. trailing average) + `get_transactions` for detail

**Savings**
- "How much am I saving?" → `get_financial_summary`
- "How can I save ₹10,000 this month?" → `get_spending_by_category` to find reducible categories + `simulate_action(reduce_spending)` for the top candidate(s)

**Debt**
- "How much debt do I have?" → `get_debt_summary`
- "What happens if I pay ₹5,000 extra?" → `simulate_action(extra_debt_payment)`

**Cash flow**
- "Will I have enough money at the end of the month?" → `get_cash_flow_forecast`
- "What bills are coming up?" → `get_recurring_expenses` filtered to upcoming window

**Affordability**
- "Can I afford a ₹30,000 purchase?" → `calculate_affordability`

**Recommendations**
- "What should I focus on this month?" → `get_recommendations` (top P0)

**What-if**
- "What if I cancel my subscriptions?" → `simulate_action(modify_recurring, cancel=true)` per subscription, or aggregated if multiple named

## Intent Classification & Tool Selection

A single constrained LLM call maps the question to one of the 7 categories above plus `general/unclear`, extracting any numeric/date/category entities present (e.g., "₹30,000", "next week", "dining"). The orchestrator then:
1. Selects the primary tool for that category.
2. Calls it with extracted parameters (defaults applied for missing ones, e.g., period defaults to trailing 30 days).
3. Inspects the result — if it signals the question needs another tool (e.g., an affordability "caution" verdict benefits from showing the forecast that explains it), calls that tool too, up to a small fixed step limit (3) to bound latency and cost.
4. Composes the final response strictly from tool outputs.

If classified `general/unclear` (e.g., "how am I doing?"), the agent calls `get_financial_summary` + `get_risk_events` and returns a structured overview rather than guessing a narrower intent.

## Context & Follow-Ups

- Each `chat_session` keeps the last N (default 6) turns plus a running summary for longer sessions.
- Follow-ups like "what about last month?" are resolved by carrying forward the previous turn's tool name and category/entity, substituting only the changed parameter (period) — handled by including the prior turn's structured `tool_calls` in the classification prompt's context.

## Example Conversations

**Example 1 — Spending drill-down**
> **User:** Where did I spend the most last month?
> **System (facts):** Your top category was Dining at ₹7,200 (29% of discretionary spend), followed by Shopping at ₹5,100.
> **System (prediction, medium confidence):** At this pace, Dining is on track to exceed last month's total by about 15%.

**Example 2 — Affordability**
> **User:** Can I afford a ₹30,000 laptop next week?
> **System:** Caution. Your current buffer is 9 days (fact). Buying it next week would drop your projected buffer to 2 days (prediction, medium confidence) because your rent payment (₹15,000) is also due that week (fact).

**Example 3 — What-if**
> **User:** What if I pay ₹10,000 extra on my personal loan this month?
> **System:** Your loan payoff would shorten from 14 to 11 months and save about ₹2,100 in interest (prediction, medium confidence). Trade-off: your minimum cash buffer this month would drop from 9 to 5 days.

**Example 4 — Insufficient data**
> **User:** How's my investment portfolio doing?
> **System:** I don't have any investment data for your account yet, so I can't answer that. I can tell you about your spending, savings, or debt instead.

## Response Style Guidelines

- Lead with the direct answer, then supporting facts, then (if relevant) a recommendation.
- Never more than one recommendation per answer unless explicitly asked for a list.
- Always state confidence for predictions inline in plain language ("medium confidence") — never hide it behind a UI-only badge with no textual equivalent, so it survives even in a copy-pasted or voice-read response.
