# Demo Script (5–7 minutes)

## 0:00 – 0:45 | The Problem

> "Most finance apps show you the past — a pie chart of last month's spending — and stop there. They never tell you what's about to happen or what to actually do about it. We built a Financial Health Copilot that closes that loop: data → insight → risk → recommendation → expected impact."

## 0:45 – 1:30 | Meet Ananya (Persona A)

Open the dashboard for Ananya, a salaried professional.

> "Here's Ananya's financial health at a glance. These are facts — computed directly from her transactions: ₹60,000 income, ₹48,000 expenses, 20% savings rate, and a 5.6-day cash buffer."

Point out the fact/prediction/recommendation labeling scheme.

> "Notice everything is labeled — fact, prediction, or recommendation — with a confidence level. Nothing here is a guess dressed up as certainty."

## 1:30 – 2:15 | Ask a Question

Switch to the AI Copilot chat.

> **Type:** "Where did most of my money go this month?"
> **Expected response:** "Your top category is Dining at ₹7,200, which is 42% above your 3-month average of ₹5,080 — that's a prediction I'm making at medium confidence based on 3 months of history."

> "Notice the assistant isn't inventing this — it called a tool that computed it directly from her transactions."

## 2:15 – 3:00 | Risk & Recommendation

Back to dashboard.

> "The system already flagged this: dining is trending toward ₹15,000 this month, which threatens her end-of-month buffer. So it doesn't just show me the trend — it recommends: reduce dining by ₹2,500. And it tells me the expected impact: buffer improves from about 5.6 to 9 days."

## 3:00 – 4:00 | Impact Simulation

Open the What-If Simulator.

> "Let's ask a harder question: what if Ananya pays ₹10,000 extra on her personal loan this month?"

Run the simulation live.

> "Baseline: 14 months left, ₹8,200 interest remaining. With the extra payment: 11 months, ₹6,100 interest — but her cash buffer drops from 9 to 5 days immediately after. The system shows the trade-off, not just the upside."

## 4:00 – 5:15 | The Big Moment: Data Changes, Recommendations Change

> "Now here's the part that matters most: does this system actually adapt, or is it just a static report?"

Submit a new ₹12,000 unplanned medical expense transaction live (via the transactions page or a seeded "inject transaction" demo button).

> "I just added a ₹12,000 medical expense today. Watch the dashboard."

Point to the `<RecalculationToast>` and the changed recommendation.

> "The system recalculated instantly. The old recommendation — 'reduce dining by ₹2,500' — is no longer enough, so it's been superseded. There's now a high-severity risk: a projected cash-flow gap in 3 days. And a new recommendation: cut ₹8,000 from discretionary spend this month and pay only the minimum on the credit card, which resolves the gap and restores a 6-day buffer."

## 5:15 – 6:00 | Explainability Close-Up

Click "Why medium confidence?" on any prediction.

> "Every prediction can explain itself — here it's medium confidence because we only have 3 months of history and dining spend has some month-to-month variability. As more data comes in, confidence improves automatically."

## 6:00 – 6:45 | Closing Value Proposition

> "This isn't a dashboard. It's a system that understands where you are, predicts what's coming, tells you exactly what to do — with a number attached — and proves it by showing you the impact before you act. And critically, it adapts in real time as your financial life changes, the same way a good financial advisor would."

## 6:45 – 7:00 | Close

> "Everything you saw — every number — came from deterministic financial calculations, not from the LLM guessing. The AI's job here is to explain, not to calculate. Thank you."

## Presenter Notes

- Keep a browser tab pre-loaded on each page to avoid live-loading delays.
- Have the "inject transaction" step ready as a single pre-filled form submission — don't type it live under time pressure.
- If the LLM call is slow/fails during the demo, fall back to the dashboard's deterministic view — rehearse this fallback explicitly (see `ERROR_HANDLING.md`).
