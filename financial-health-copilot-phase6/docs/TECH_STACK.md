# Technology Stack

## Frontend

### Next.js (React) + TypeScript
- **Why:** File-based routing, fast dev server, easy deployment to Vercel, strong charting/ecosystem support, and TypeScript catches data-shape bugs early — important when every number carries a fact/prediction/confidence type.
- **Used for:** Dashboard, chat UI, what-if simulator, all client-side rendering.
- **Alternatives considered:** Plain React + Vite (simpler, but lose SSR/routing conveniences); Vue/Nuxt (smaller team familiarity in most hackathons).
- **Trade-off:** Slightly more boilerplate than plain React for a small app; accepted for the ecosystem and deployment benefits.

### Tailwind CSS
- **Why:** Fast to build a clean, consistent UI without hand-rolled CSS; good for hackathon speed.
- **Used for:** All styling.
- **Alternatives:** CSS Modules, Chakra/MUI component libraries.
- **Trade-off:** Utility-class verbosity in JSX; accepted for speed and consistency.

### Recharts
- **Why:** Simple React-native charting API, good enough for line/bar/area charts (spending trends, cash-flow forecast with confidence bands).
- **Alternatives:** Chart.js (less React-idiomatic), D3 (too low-level for hackathon timelines), Nivo.
- **Trade-off:** Less customizable than D3; not needed at this scope.

## Backend

### Python + FastAPI
- **Why:** Python has the best ecosystem for financial/data calculations (pandas, numpy) and is the natural choice given the analytics-heavy nature of this product. FastAPI gives async support, automatic OpenAPI docs (useful for a hackathon demo and for the frontend team to work in parallel), and Pydantic for strict request/response schemas — which matters a lot here because every response must carry a well-defined fact/prediction/confidence shape.
- **Used for:** All backend logic — API, analytics, forecasting, risk, recommendations, simulation, agent orchestration.
- **Alternatives considered:** Node.js + TypeScript (would unify language with frontend, but weaker numerical/data ecosystem than pandas/numpy for the analytics core, which is the heart of this product).
- **Trade-off:** Two languages across the stack (TS frontend, Python backend) instead of one; accepted because analytics correctness matters more than language unification for this problem.

### pandas
- **Why:** Ideal for time-series aggregation (rolling averages, category grouping, recurring-payment detection) with well-tested, readable operations.
- **Used for:** Transaction aggregation, recurring detection, forecasting inputs.
- **Alternatives:** Raw SQL aggregation (viable for some queries, used alongside pandas where simpler); Polars (faster but unnecessary at this data scale).

## AI

### LLM via tool-calling (e.g., Anthropic Claude API)
- **Why:** Tool-calling lets the LLM select and invoke deterministic backend functions rather than compute numbers itself — this is the core safeguard against hallucinated financial figures.
- **Used for:** Intent classification, natural-language Q&A, explanation generation, summarization.
- **Explicitly NOT used for:** Any arithmetic, forecasting, or ratio calculation — all of that lives in Python functions the LLM calls as tools.
- **Alternatives considered:** OpenAI GPT-4 class models (equally viable; the architecture is provider-agnostic since it depends only on tool-calling support).

### Rule-based / statistical forecasting and risk detection
- **Why:** Explainability is a hard product requirement. Rolling averages, recurring-payment schedules, and threshold rules are fully interpretable — a judge or user can verify the logic by hand. See `FORECASTING_AND_RISK.md` for when upgrading to ML would be justified.
- **Alternatives considered:** Time-series ML models (ARIMA/Prophet/LSTM) — explicitly deferred to Future Scope; not justified by MVP data volume or explainability requirements.

## Database

### PostgreSQL
- **Why:** Relational structure fits financial data naturally (users, accounts, transactions, loans — all with clear relationships and referential integrity requirements); strong support for numeric/decimal types (critical for money); mature, free, well understood.
- **Used for:** All persistent storage.
- **Alternatives considered:** SQLite (fine for solo prototyping, weaker for a demo with concurrent judges/testers); MongoDB (schema flexibility not needed — financial data is inherently structured/relational).

## Authentication

### JWT-based email/password auth
- **Why:** Realistic enough to demonstrate a real product, simple enough to build in hours. FastAPI + `passlib`/`python-jose` covers this cleanly.
- **Alternatives considered:** OAuth/social login (adds setup overhead with no product benefit for a hackathon demo); no-auth (unrealistic and wouldn't demonstrate per-user data isolation, which matters for judging).

## Deployment

- **Local dev:** Docker Compose (Postgres + backend + frontend) — one command to run for judges/teammates.
- **Hosted demo (optional):** Vercel for frontend, Render or Railway for backend + managed Postgres.
- **Why:** Free tiers exist for all of these, setup time is minutes, and this is a common, well-documented path for hackathon deployments.

## Recommended Final Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend framework | Next.js + TypeScript | UI, routing, SSR |
| Styling | Tailwind CSS | Fast, consistent styling |
| Charts | Recharts | Spending/cash-flow/forecast visualization |
| Backend framework | Python + FastAPI | API, business logic, agent orchestration |
| Data processing | pandas / numpy | Aggregation, forecasting math |
| Database | PostgreSQL | Persistent relational storage |
| AI / LLM | Claude (or GPT-4 class) via tool-calling | NLU, explanation, conversational layer only |
| Auth | JWT (python-jose) + bcrypt | User authentication |
| Containerization | Docker + Docker Compose | Local dev & reproducible demo |
| Hosting (optional) | Vercel (frontend) + Render/Railway (backend+DB) | Hosted demo |
