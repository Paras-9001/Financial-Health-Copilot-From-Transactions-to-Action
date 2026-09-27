# Sample Data

All data below is synthetic, INR-denominated, and designed to exercise every feature: spending patterns, recurring payments, debt, cash-flow forecasting, risks, recommendations, and what-if simulations.

## Persona A — "Stable but Tight" (Ananya, salaried professional)

- Income: ₹60,000/month, salary credited on the 1st (stable, CV ≈ 0.02).
- Fixed: Rent ₹15,000 (1st), Personal Loan EMI ₹8,000 (5th).
- Variable: Groceries ~₹6,000/month, Utilities ~₹2,200/month.
- Discretionary: Dining ~₹7,200/month (trending up), Subscriptions ₹2,100/month (Netflix ₹649, Spotify ₹119, gym ₹1,332), Shopping ~₹9,100/month (volatile).
- Credit card: limit ₹1,00,000, balance ₹22,000 (22% utilization).
- Current checking balance: ₹9,000 (as of demo "today", mid-month).
- **Designed to trigger:** low cash buffer risk, upcoming cash-flow gap (rent due before next salary if a large expense hits), unusually high dining spend.

### Sample transactions (last 10 days, table)

| Date | Merchant (raw) | Amount | Direction | Category |
|---|---|---|---|---|
| 2026-09-17 | SWIGGY*ORDER8823 | 620 | debit | Dining |
| 2026-09-18 | BIGBASKET | 2100 | debit | Groceries |
| 2026-09-19 | NETFLIX.COM | 649 | debit | Subscriptions |
| 2026-09-20 | AMAZON PAY | 3200 | debit | Shopping |
| 2026-09-21 | SWIGGY*ORDER8901 | 540 | debit | Dining |
| 2026-09-22 | UBER TRIP | 310 | debit | Transport |
| 2026-09-23 | ELECTRICITY BOARD | 1450 | debit | Utilities |
| 2026-09-24 | ZOMATO*ORDER | 780 | debit | Dining |
| 2026-09-25 | HDFC CC PAYMENT | 5000 | debit | Debt Payment |
| 2026-09-26 | SALARY CREDIT | 60000 | credit | Income |

## Persona B — "Feast or Famine" (Rohit, freelance designer)

- Income: variable, ₹35,000–₹95,000/month, irregular deposit dates (CV ≈ 0.38 → triggers income volatility risk).
- No fixed rent (lives with family) but a personal loan EMI ₹12,000 and credit card balance ₹68,000 on a ₹75,000 limit (90.7% utilization → triggers debt pressure/credit utilization risk).
- Discretionary spend relatively low (~₹6,000/month) but concentrated in bursts after large client payments.
- **Designed to trigger:** income volatility risk, debt pressure (high utilization), recurring burden risk if EMI + minimum due exceed 50% of a low-income month.

## Persona C — "Comfortable Saver" (Meera, stable senior professional)

- Income: ₹1,40,000/month, stable.
- Fixed: Rent ₹28,000, no loans.
- Savings rate: ~38% historically.
- Investments: Mutual funds ₹6,20,000 (snapshot only).
- Planning a large upcoming purchase: a ₹1,80,000 vacation in 2 months.
- **Designed to demonstrate:** affordability check for a large purchase, "surplus opportunity" recommendation (e.g., suggest increasing investment contribution), and a what-if simulation for "delay purchase."

## Recurring Payment Detection Example (Persona A, Netflix)

| Date | Amount |
|---|---|
| 2026-07-19 | 649 |
| 2026-08-19 | 649 |
| 2026-09-19 | 649 |

→ 3 cycles, exact amount match, ~30-day interval → `status: confirmed`, `frequency: monthly`, `next_expected_date: 2026-10-19`.

## Data Sufficiency for Each Feature (using Persona A)

| Feature | Minimum data present | Resulting confidence |
|---|---|---|
| Spending by category | 30+ days transactions | High |
| Recurring detection | 3 cycles (Netflix, Spotify, gym) | High (confirmed) |
| Cash-flow forecast | 2 months history | Medium |
| Income volatility | Only 1 income source, stable | Not triggered (CV too low) — correctly suppressed |
| Debt pressure | Full loan + CC data | High |

## Seeding

Seed data should be loaded via `POST /transactions` bulk endpoint plus direct `loans`/`credit_cards`/`income_sources` inserts for each persona, exposed as a `scripts/seed_demo_data.py` script producing all three personas so the demo can switch between them.
