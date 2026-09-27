# Financial Analytics

All formulas below are implemented as pure, deterministic, unit-tested functions. **The LLM never performs any of this arithmetic** — it only reads the output.

Currency: INR (₹). Examples assume a monthly period unless stated.

---

### Total Income
`total_income = Σ(credit transactions classified as income in period)`
- **Required data:** transactions with category type = 'income', or declared `income_sources`.
- **Interpretation:** Baseline for every ratio below.
- **Limitations:** Irregular/gig income understates reliability — see Income Volatility.

### Total Expenses
`total_expenses = Σ(debit transactions in period, excluding transfers)`

### Fixed Expenses
`fixed_expenses = Σ(debit transactions where category.type = 'fixed')`
- e.g., rent, EMI, insurance premiums.

### Variable Expenses
`variable_expenses = Σ(debit transactions where category.type = 'variable')`
- e.g., groceries, utilities — necessary but fluctuating.

### Discretionary Expenses
`discretionary_expenses = Σ(debit transactions where category.type = 'discretionary')`
- e.g., dining, entertainment, shopping.
- **Example:** Groceries ₹6,000 + Rent ₹15,000 (fixed/variable) vs. Dining ₹7,200 + Subscriptions ₹2,100 + Shopping ₹9,100 = ₹18,400 discretionary.

### Savings
`savings = total_income - total_expenses`

### Savings Rate
`savings_rate = savings / total_income × 100`
- **Interpretation:** >20% generally healthy; <0% means spending exceeds income.
- **Example:** Income ₹60,000, Expenses ₹48,000 → Savings ₹12,000 → Savings Rate = 20%.

### Expense-to-Income Ratio
`expense_to_income = total_expenses / total_income × 100`

### Debt-to-Income Ratio (DTI)
`debt_to_income = total_monthly_debt_payments / total_monthly_income × 100`
- **Required data:** loan installments + credit card minimum dues, income.
- **Interpretation:** <36% generally healthy, 36–43% caution, >43% high risk (commonly used bands; configurable).
- **Example:** EMI ₹8,000 + Card min-due ₹1,500 on income ₹60,000 → DTI = 15.8%.

### Debt Service Ratio
`debt_service_ratio = total_monthly_debt_payments / total_monthly_take_home_income × 100`
- Distinguished from DTI when take-home income differs materially from gross declared income (MVP: often the same input; kept as a separate metric for clarity and future extension).

### Monthly Burn
`monthly_burn = total_expenses / number_of_days_in_period × 30`
- Normalizes partial-period expenses to a monthly rate.

### Cash Buffer (days)
`cash_buffer_days = current_liquid_balance / average_daily_expense`
- `average_daily_expense = trailing_30_day_expenses / 30`.
- **Example:** Balance ₹9,000, avg daily expense ₹1,600 → buffer ≈ 5.6 days.

### Emergency Fund Coverage
`emergency_fund_months = liquid_savings_balance / average_monthly_expense`
- **Interpretation:** <1 month = high vulnerability; 3–6 months commonly recommended target.

### Recurring Expense Burden
`recurring_burden_pct = total_recurring_monthly_obligations / total_monthly_income × 100`
- **Required data:** confirmed `recurring_transactions` + loan installments.
- **Example:** Recurring obligations ₹28,000 on income ₹60,000 → 46.7%.

### Credit Utilization
`credit_utilization_pct = current_credit_card_balance / credit_limit × 100`, aggregated as `Σ balances / Σ limits` across cards for an overall figure.
- **Interpretation:** <30% generally healthy; >70% high risk.

### Income Volatility
`income_cv = stddev(monthly_income_last_N_periods) / mean(monthly_income_last_N_periods)`
- Coefficient of variation over trailing 6 periods (or fewer, with reduced confidence, if <6 available).
- **Interpretation:** CV < 0.1 stable; 0.1–0.3 moderate; >0.3 high volatility.

### Spending Volatility
`spending_cv = stddev(monthly_discretionary_spend_last_N_periods) / mean(monthly_discretionary_spend_last_N_periods)`
- Used as an input to forecast confidence — high volatility widens the forecast's confidence interval.

---

## Notes on Limitations (apply throughout)

- All ratios require a minimum data window (recommend ≥2 full periods) to be reported with anything above "low" confidence; below that, the system reports the raw number with an explicit `insufficient_history` flag rather than suppressing it entirely.
- Ratios involving income are only as good as income detection; misclassified income (e.g., a large one-off transfer categorized as income) can distort results — the categorization confidence is carried forward into the metric's confidence score (see `CONFIDENCE_AND_EXPLAINABILITY.md`).
- All formulas operate on completed, ingested transactions only; they do not account for pending/uncleared transactions in MVP.
