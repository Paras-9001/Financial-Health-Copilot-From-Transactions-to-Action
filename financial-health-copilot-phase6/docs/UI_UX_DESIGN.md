# UI/UX Design

This document specifies the visual design system and interaction patterns referenced but not fully detailed in `FRONTEND_ARCHITECTURE.md`. Where the two overlap, this document is authoritative for visual/interaction specifics; `FRONTEND_ARCHITECTURE.md` remains authoritative for component/state architecture.

## Design Principles

1. **Labeling is load-bearing, not decorative.** The fact/prediction/recommendation/assumption distinction must be visually unmistakable at a glance, not something a user has to read carefully to notice.
2. **No number without a home.** Every figure on screen belongs to exactly one of the four label types, has a unit/currency, and (for money) a period.
3. **Calm, not alarming.** Risk severity uses color deliberately but avoids a "red alert dashboard" feel — this is a financial advisor's tone, not a security-incident tone.
4. **Progressive disclosure.** Summary first, detail on demand ("Why medium confidence?", "Show evidence") — the dashboard should never feel like a wall of numbers.

## Color System

Defined as design tokens (CSS variables), theme-aware (light default; dark optional/stretch).

| Token | Light value | Usage |
|---|---|---|
| `--color-bg` | `#FAFAF9` | App background |
| `--color-surface` | `#FFFFFF` | Cards |
| `--color-text-primary` | `#1C1B1A` | Body text |
| `--color-text-secondary` | `#6B6864` | Captions, labels |
| `--color-fact` | `#2563EB` (blue) | Fact badges/accents |
| `--color-prediction` | `#7C3AED` (violet) | Prediction badges/accents |
| `--color-recommendation` | `#059669` (green) | Recommendation badges/accents |
| `--color-assumption` | `#6B7280` (gray) | Assumption badges/accents |
| `--color-risk-low` | `#65A30D` | Low severity |
| `--color-risk-medium` | `#D97706` | Medium severity |
| `--color-risk-high` | `#DC2626` | High severity |
| `--color-border` | `#E7E5E4` | Card/table borders |

Color is never the sole signal — every badge pairs color with an icon and a text label (e.g., a small circle icon + "FACT" text on a blue-tinted chip).

## Typography

- **Font:** Inter (or system-ui fallback stack) — clean, highly legible at small sizes for dense financial data.
- **Scale:** 12px (captions/labels) / 14px (body) / 16px (emphasized body) / 20px (card titles) / 28px (page titles) / 40px (hero numbers, e.g., health score).
- **Numerals:** tabular figures (`font-variant-numeric: tabular-nums`) everywhere money/dates are shown in tables or comparisons, so digits align vertically.

## Spacing & Layout

- 8px base spacing unit; card padding 16–24px; page gutter 24px (mobile) / 48px (desktop).
- Dashboard uses a 12-column responsive grid; cards span 4/6/12 columns depending on content weight (health score: 4, risk/recommendation: 6–12, chart: 12).

## The Fact/Prediction/Recommendation/Assumption Badge (canonical spec)

```
┌──────────────────────────────┐
│ ● FACT                       │   <- 12px pill, colored bg-tint, icon + label
│ You spent ₹12,450 on dining  │   <- 14px body text
│ in the last 30 days.         │
└──────────────────────────────┘

┌──────────────────────────────┐
│ ◆ PREDICTION · Medium         │   <- confidence appended inline, never separate/optional
│ Dining may reach ~₹15,000     │
│ this month.        [Why?]     │   <- inline expandable, not a separate page navigation
└──────────────────────────────┘

┌──────────────────────────────┐
│ ▶ RECOMMENDATION               │
│ Reduce dining by ₹2,500       │
│ Impact: buffer 4d → 9d         │
│ [Simulate]      [Dismiss]      │
└──────────────────────────────┘
```

- Icons: filled circle (fact), diamond (prediction), triangle/arrow (recommendation), outlined circle (assumption) — chosen to be distinguishable in grayscale/colorblind-safe contexts, not relying on hue alone.
- "Why?" expansion shows the `confidence_basis` fields verbatim from the API (data completeness, history length, volatility) as a short bullet list — never a client-invented explanation.

## Page-by-Page Wireframes

### Transactions Page

```
┌─────────────────────────────────────────────────────────┐
│ Transactions                     [+ Add Transaction]     │
│ Filters: [Category ▾] [Date range ▾] [Search merchant]   │
├─────────────────────────────────────────────────────────┤
│ Date       Merchant        Category      Amount          │
│ Sep 26     Salary Credit   Income        +₹60,000        │
│ Sep 25     HDFC CC Pmt     Debt Payment  -₹5,000          │
│ Sep 24     Zomato          Dining        -₹780   [Edit ▾] │
│ Sep 23     Electricity Bd  Utilities     -₹1,450          │
│ ...                                                       │
│                                              [Load more]  │
└─────────────────────────────────────────────────────────┘
```
- Clicking `[Edit ▾]` on a row opens an inline category picker (manual override, per FR-B5).
- Uncategorized rows show an amber "Uncategorized" chip with a one-click categorize action, surfaced as a banner count at the top ("12 uncategorized transactions").

### Debt Page

```
┌─────────────────────────────────────────────────────────┐
│ Debt Overview                                            │
│ Total Debt ₹1,42,000   DTI 15.8%   Utilization 22%       │
├─────────────────────────────────────────────────────────┤
│ Personal Loan            ₹1,20,000 outstanding            │
│ [progress bar: 8/22 months paid]                          │
│ 14 months left · ₹8,200 interest remaining                │
│ [Try extra payment in Simulator]                          │
├─────────────────────────────────────────────────────────┤
│ HDFC Credit Card         ₹22,000 / ₹1,00,000 (22%)         │
│ [utilization bar]                                          │
└─────────────────────────────────────────────────────────┘
```

### What-If Simulator Page

```
┌─────────────────────────────────────────────────────────┐
│ What if I...  [Reduce spending ▾]                         │
│  Category: [Dining ▾]   Amount: [₹____]   [Run Simulation]│
├───────────────────────────┬───────────────────────────────┤
│ BASELINE                  │ PROPOSED                       │
│ Balance: -₹1,450 (Oct 14) │ Balance: +₹1,050 (Oct 14)       │
│ Buffer: 4 days            │ Buffer: 9 days                 │
├───────────────────────────┴───────────────────────────────┤
│ Confidence: Medium   [Why?]                                │
│ Assumptions: no other unscheduled large expenses           │
└─────────────────────────────────────────────────────────┘
```
- Left/right panels use neutral gray (baseline) vs. green-tinted (proposed) backgrounds — not red/green, since baseline isn't "bad," just current.

### AI Copilot (Chat) Page

```
┌─────────────────────────────────────────────────────────┐
│  🤖 Your top dining spend is ₹7,200 this month, 42%       │
│     above your 3-month average.                           │
│     ┌───────────────────────────────┐                     │
│     │ ● FACT: Dining ₹7,200 (30d)   │                     │
│     │ ◆ PREDICTION · Medium: ~₹15k  │                     │
│     └───────────────────────────────┘                     │
├─────────────────────────────────────────────────────────┤
│  [Type a question...]                          [Send]     │
└─────────────────────────────────────────────────────────┘
```
- Assistant messages render inline `<FactCard>`/`<PredictionCard>`/`<RecommendationCard>` components identical to the dashboard's — never plain text pretending to be a number without its label.

## Interaction Patterns

- **Loading:** skeleton placeholders (shimmering gray blocks matching final content shape), never a generic spinner-only state for data-heavy cards.
- **`<RecalculationToast>`:** slides in from the top-right, persists until dismissed or 8s, reads "Your financial picture updated — [N] changes. [View what changed]" — clicking navigates to a diff view highlighting new/changed/resolved risk and recommendation cards with a subtle highlight animation (fade-in, not a jarring flash).
- **Empty/insufficient-data state:** centered icon + one-sentence explanation + (if applicable) a single clear next action button — never a bare "No data."
- **Error state:** inline retry button on the specific failed card/section, not a full-page crash — other cards on the same page continue to render if their data loaded successfully.

## Accessibility

- Minimum contrast ratio 4.5:1 for body text, 3:1 for large text/icons (WCAG AA).
- All interactive elements reachable via keyboard (Tab order follows visual/logical order); focus states visibly outlined.
- All charts have an adjacent text summary (also satisfies the "no color-only meaning" rule).
- Badge components use `aria-label` stating the full label (e.g., "Prediction, medium confidence") for screen readers, not just the icon.

## Responsive Behavior

- Breakpoints: mobile (<640px, single column, cards stack), tablet (640–1024px, 2-column grid), desktop (>1024px, full 12-column grid).
- Charts on mobile switch to a simplified view (e.g., cash-flow forecast shows a condensed 7-day window with a "view full 30 days" expand, rather than a cramped full chart).
- What-If Simulator's baseline/proposed panels stack vertically on mobile rather than side-by-side.
