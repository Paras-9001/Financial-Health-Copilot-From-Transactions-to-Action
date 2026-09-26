# AI Architecture

## Core Principle

**The LLM never performs financial calculations.** It is a natural-language interface over a deterministic system. This is enforced architecturally, not just by prompting: the LLM has no way to answer a financial question except by calling a tool that returns a computed, structured result.

## The Five Layers

| Layer | Responsibility | Implementation |
|---|---|---|
| 1. Deterministic financial computation | Income, expenses, ratios, buffers | Python functions, unit-tested (`FINANCIAL_ANALYTICS.md`) |
| 2. Statistical forecasting | Near-term cash-flow projection with confidence | Rolling averages, recurring schedules, trend detection (`FORECASTING_AND_RISK.md`) |
| 3. Risk detection | Threshold/pattern rules over layers 1–2 | Rule engine, fully deterministic |
| 4. Recommendation generation | Turn risks into ranked, quantified actions | Deterministic scoring + simulation engine |
| 5. Natural-language explanation | Answer questions, summarize, converse | LLM, strictly grounded in outputs of layers 1–4 |

Only layer 5 touches the LLM. Layers 1–4 are plain Python, callable directly by the API (for dashboard rendering) *and* by the LLM (as tools, for chat).

## Where the LLM Is Used

- Classifying user intent from free text.
- Selecting which tool(s) to call and with what parameters.
- Turning structured tool output into a fluent, well-organized natural-language answer.
- Summarizing multiple data points into a short narrative (e.g., "your top 3 categories are...").
- Asking a clarifying question when intent is ambiguous.

## Where the LLM Is Never Used

- Computing any ratio, sum, average, or projection.
- Deciding whether a risk threshold has been crossed.
- Generating a recommendation's expected impact number.
- Deciding priority/ranking of recommendations.

## Structured Context Passed to the LLM

For every chat turn, the agent orchestrator assembles a context object, not raw database rows:

```json
{
  "user_id": "...",
  "session_summary": "short rolling summary of prior turns",
  "available_tools": ["get_financial_summary", "get_transactions", "..."],
  "user_preferences": { "buffer_days": 7, "currency": "INR" }
}
```

The LLM is never given raw table dumps; it requests exactly what it needs via tool calls, keeping context small and auditable.

## System Prompt Strategy

The system prompt establishes:
1. Role: "You are a financial copilot. You must never state a number you did not receive from a tool call."
2. Labeling requirement: every factual claim must be tagged as OBSERVED, PREDICTED, or RECOMMENDED in the underlying structured response (rendered by the UI, not necessarily inline text).
3. Refusal behavior: if a needed tool returns `insufficient_data`, say so explicitly instead of estimating.
4. Scope boundary: no investment/tax/legal advice — redirect to what the system *can* answer.

## Tool/Function Calling

The LLM has access to the tool set defined in `AI_AGENT_DESIGN.md`. Each tool has a strict JSON schema for inputs and outputs. The orchestrator validates tool-call arguments against the schema before executing (e.g., rejects a `simulate_action` call with a negative amount).

## Response Schema

Every agent response returned to the frontend follows:

```json
{
  "answer_text": "string, LLM-composed",
  "facts": [ { "label": "...", "value": "...", "source": "tool_name" } ],
  "predictions": [ { "label": "...", "value": "...", "confidence": "medium", "basis": "..." } ],
  "recommendations": [ { "...": "see RECOMMENDATION_ENGINE.md schema" } ],
  "tool_calls": [ { "tool": "...", "args": {...}, "result_summary": "..." } ]
}
```

The frontend renders `facts`/`predictions`/`recommendations` with consistent visual treatment regardless of whether they came from the dashboard API or the chat API — same underlying data, same labeling.

## Grounding Strategy

- Every numeric claim in `answer_text` must have a corresponding entry in `facts`/`predictions`/`recommendations` sourced from an actual tool call in that turn.
- The orchestrator performs a lightweight post-check: numbers appearing in `answer_text` are cross-referenced against `tool_calls` results; a mismatch triggers a retry with a stricter reminder prompt (hackathon-scope safeguard, not a full verifier).

## Hallucination Prevention

1. **No-tool-no-number rule:** the LLM is instructed, and post-checked, to never state a figure without a backing tool result in the same turn.
2. **Explicit insufficiency:** tools return `{"status": "insufficient_data", "reason": "..."}` rather than a fabricated best-guess; the LLM is instructed to relay this directly.
3. **Temperature:** low temperature (e.g., 0.2) for the composition step, since creativity is not desired — fidelity to tool output is.
4. **Schema-validated outputs:** the final response is validated against the response schema above; malformed or unsupported responses are rejected and retried once, then fall back to a templated "I couldn't complete that calculation" response.
5. **Prompt-injection isolation:** any user-supplied free text (e.g., a transaction description) that ends up in LLM context is passed as inert data within a clearly delimited field, never as instructions (see `SECURITY_AND_PRIVACY.md`).
