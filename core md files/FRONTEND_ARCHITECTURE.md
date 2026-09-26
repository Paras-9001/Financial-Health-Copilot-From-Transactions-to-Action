# Frontend Architecture

## Pages

| Page | Route | Purpose |
|---|---|---|
| Login/Signup | `/login` | Auth |
| Dashboard | `/` | "Where am I / what might happen / what should I do" summary |
| Transactions | `/transactions` | Full transaction list, filters, manual category correction |
| Spending | `/spending` | Category breakdown, trends |
| Cash Flow | `/cash-flow` | Forecast chart with confidence band, upcoming bills |
| Debt | `/debt` | Loans/cards, amortization, payoff projection |
| Recommendations | `/recommendations` | Ranked recommendation feed with expected impact |
| What-If Simulator | `/simulate` | Interactive scenario builder |
| AI Copilot | `/chat` | Conversational interface |

## Dashboard Design Around the Core Loop

The dashboard is organized into four stacked sections, directly mirroring the product's value chain:

1. **Where am I?** — Health score, key facts (income, expenses, savings rate, buffer) — all tagged OBSERVED.
2. **What might happen?** — Top 1–2 active risks with evidence and confidence — tagged PREDICTION.
3. **What should I do?** — Top-ranked recommendation(s) with reason — tagged RECOMMENDATION.
4. **What happens if I do it?** — Inline mini expected-impact preview with a "Try it in the simulator" link.

## Wireframe (ASCII)

```
┌─────────────────────────────────────────────────────────────┐
│  Financial Health Copilot          [Chat]  [Profile]         │
├─────────────────────────────────────────────────────────────┤
│  WHERE AM I?                                                 │
│  ┌───────────┐  Income ₹60,000   Expenses ₹48,000            │
│  │  Health   │  Savings Rate 20%  Buffer: 9 days  [FACT]      │
│  │  Score 71 │                                                │
│  └───────────┘                                                │
├─────────────────────────────────────────────────────────────┤
│  WHAT MIGHT HAPPEN?                            [PREDICTION]   │
│  ⚠ High: Cash-flow gap projected Oct 14 (-₹1,450)             │
│  Confidence: Medium   [Why?]                                  │
├─────────────────────────────────────────────────────────────┤
│  WHAT SHOULD I DO?                          [RECOMMENDATION]  │
│  → Reduce Dining spend by ₹2,500 this month                   │
│    Impact: Buffer 4d → 9d, Balance -₹1,450 → +₹1,050           │
│    [Simulate this]  [Dismiss]                                 │
├─────────────────────────────────────────────────────────────┤
│  Cash Flow (30d)      [chart with shaded confidence band]     │
├─────────────────────────────────────────────────────────────┤
│  Recent Transactions            Recurring Payments            │
│  ...                            ...                            │
└─────────────────────────────────────────────────────────────┘
```

## Major Components

- `<FactCard>` / `<PredictionCard>` / `<RecommendationCard>` — shared visual language (icon + color + label), used identically on the dashboard and in chat responses.
- `<ConfidenceBadge>` — text + color, never color-only.
- `<CashFlowChart>` — Recharts `AreaChart` with a shaded confidence band (upper/lower bound as a translucent area, projected line on top).
- `<CategoryBreakdownChart>` — Recharts `BarChart`/`PieChart` toggle.
- `<AmortizationTable>` — collapsible schedule for a selected loan.
- `<SimulatorForm>` — action-type selector + dynamic parameter fields + `<ComparisonPanel>` (baseline vs proposed side-by-side).
- `<ChatWindow>` — message list + input; renders `<FactCard>`/`<PredictionCard>`/`<RecommendationCard>` inline within assistant messages.
- `<RecalculationToast>` — appears when new data triggers a recalculation, linking to what changed (supports the "recommendations evolve" demo requirement).

## State Management

- **Server state:** React Query (TanStack Query) for all API data — handles caching, refetch-on-mutation (e.g., after `POST /transactions`, invalidate `financial-summary`, `risks`, `recommendations` queries), and loading/error states uniformly.
- **Local/UI state:** React `useState`/`useReducer` for form state (simulator inputs, chat input box) — no need for Redux/Zustand at this scope.
- **Auth state:** JWT stored in memory + httpOnly-friendly pattern (MVP: localStorage acceptable for hackathon; documented as a production gap in `SECURITY_AND_PRIVACY.md`), a lightweight React context exposes `user`/`login`/`logout`.

## Chart Strategy

- Recharts for all standard charts (line/area/bar/pie) — sufficient for spending trends, forecast bands, category breakdowns.
- Every chart has an accompanying textual summary (accessibility + reinforces the fact/prediction labeling — charts alone never carry the confidence label).

## Handling Uncertainty in UI

- Insufficient-data states render a dedicated `<InsufficientDataCard>` (not an empty chart or a zero) explaining what's missing and, where known, what would unlock it.
- Predictions always show their confidence badge and a "Why this confidence?" expandable explanation sourced directly from the API's `confidence_basis` field — never invented client-side.
