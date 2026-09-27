# Future Scope

Everything below is explicitly **out of MVP scope** and would come after the hackathon.

## Real Data Integration
- **Open Banking / Account Aggregator (e.g., India's AA framework) or Plaid-style integrations** for real bank/credit-card feeds, replacing synthetic seed data.
- **Real-time transaction ingestion** via webhooks instead of batch/manual import.

## Better Forecasting
- Upgrade from rolling-average forecasting to a learned time-series model (Prophet, or a small gradient-boosted/LSTM model) once sufficient per-user history exists, with feature-attribution-based explainability preserved.
- Seasonal adjustment (festival months, annual insurance premiums, etc.).

## Personalization
- User-declared financial goals (e.g., "save ₹5,00,000 for a down payment by 2028") with goal-tracking recommendations.
- Investment analysis: portfolio allocation review, risk profiling (currently only a balance snapshot in MVP).
- Credit score insights and simulated impact of financial decisions on credit score.

## Proactive Features
- Push/email/SMS alerts when a new risk is detected, rather than requiring the user to open the app.
- Bill negotiation assistance (e.g., flagging subscription price increases, suggesting cheaper alternatives).
- Automated savings ("round-up" or rule-based auto-transfers) — would require write-access banking integration, a significant scope/trust increase.

## Multi-Account Optimization
- Recommendations that span multiple debts/accounts simultaneously (e.g., optimal debt avalanche/snowball ordering) rather than one-at-a-time simulation.
- Household/shared-account support (multiple users, shared budgets).

## Platform Expansion
- Native mobile apps (iOS/Android).
- Voice assistant integration for spoken financial Q&A.

## AI/ML Maturity
- Larger, curated groundedness eval set with continuous monitoring in production.
- Fine-tuned or distilled smaller model for the intent-classification step to reduce latency/cost at scale.
- Anomaly detection (ML-based) for unusual transactions, supplementing the rule-based threshold in MVP.

## Explicit MVP vs. Future Boundary

| Area | MVP | Future |
|---|---|---|
| Data source | Synthetic seed data | Real bank feeds via Open Banking/Plaid |
| Forecasting | Rolling average + schedules | ML time-series model |
| Alerts | In-app only, on page load | Push/email/SMS proactive |
| Debt optimization | One action at a time | Multi-debt/multi-goal joint optimization |
| Accounts | Single user | Household/shared |
| Investments | Balance snapshot | Full portfolio analysis, risk profiling |
