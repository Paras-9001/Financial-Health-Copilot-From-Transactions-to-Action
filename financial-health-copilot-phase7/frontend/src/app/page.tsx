"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { AppShell, PageHeader } from "@/components/app-shell";
import { CashFlowChart } from "@/components/charts";
import { InsightCard } from "@/components/insight-card";
import { InlineError, InsufficientData, SkeletonCards } from "@/components/states";
import { useAuth } from "@/components/auth-provider";
import { api, ApiError } from "@/lib/api";
import type { FinancialSummary, Forecast, Recommendation, Recurring, Risk, Transaction } from "@/lib/types";
import { label, money } from "@/lib/types";

export default function Dashboard() {
  const { token, user } = useAuth();
  const summary = useQuery({ queryKey: ["financial-summary"], queryFn: () => api<FinancialSummary>("/financial-summary", {}, token!), enabled: Boolean(token), retry: false });
  const risks = useQuery({ queryKey: ["risks"], queryFn: () => api<{ risks: Risk[] }>("/risks", {}, token!), enabled: summary.isSuccess, retry: false });
  const recommendations = useQuery({ queryKey: ["recommendations"], queryFn: () => api<{ recommendations: Recommendation[] }>("/recommendations", {}, token!), enabled: summary.isSuccess, retry: false });
  const forecast = useQuery({ queryKey: ["forecast", 30], queryFn: () => api<Forecast>("/cash-flow/forecast?horizon_days=30", {}, token!), enabled: summary.isSuccess, retry: false });
  const transactions = useQuery({ queryKey: ["transactions", "recent"], queryFn: () => api<{ transactions: Transaction[] }>("/transactions?page_size=5", {}, token!), enabled: summary.isSuccess, retry: false });
  const recurring = useQuery({ queryKey: ["recurring"], queryFn: () => api<{ recurring: Recurring[] }>("/recurring-expenses", {}, token!), enabled: summary.isSuccess, retry: false });
  const noData = summary.error instanceof ApiError && summary.error.code === "no_data";
  return (
    <AppShell>
      <main className="dashboard page-stack">
        <PageHeader eyebrow="YOUR FINANCIAL PICTURE" title={`Welcome, ${user?.name?.split(" ")[0] ?? "there"}.`} description="Know where you stand, what may happen next, and the most useful action to take." actions={<Link className="primary link-button" href="/chat">Ask Copilot</Link>} />
        {summary.isLoading && <SkeletonCards count={4} />}
        {noData && <InsufficientData title="Choose how to start" message="Your workspace is ready. Add sample data, import a CSV, or enter your finances manually to unlock the full dashboard." action={<Link className="primary link-button" href="/onboarding">Set up my workspace</Link>} />}
        {summary.error && !noData && <InlineError message={summary.error.message} retry={() => summary.refetch()} />}
        {summary.data && (
          <>
            <section aria-labelledby="where-heading"><div className="section-heading"><div><p className="section-kicker">01 · OBSERVED</p><h2 id="where-heading">Where am I?</h2></div><span className="period">{summary.data.period.start} — {summary.data.period.end}</span></div>
              <div className="metrics-grid">
                <article className="score-card"><span className="insight-badge badge-fact">● FACT</span><div className="score-ring"><strong>{summary.data.health_score.value}</strong><span>/100</span></div><h3>Financial health</h3><p>{summary.data.health_score.confidence} confidence · {summary.data.data_quality.observation_periods} observed periods</p></article>
                <InsightCard kind="fact" title="Income" value={money(summary.data.facts.total_income)}><p>Recorded in this period</p></InsightCard>
                <InsightCard kind="fact" title="Expenses" value={money(summary.data.facts.total_expenses)}><p>Recorded in this period</p></InsightCard>
                <InsightCard kind="fact" title="Savings rate" value={`${summary.data.facts.savings_rate}%`}><p>Cash buffer: {summary.data.facts.cash_buffer_days ?? "—"} days</p></InsightCard>
              </div>
            </section>
            <section aria-labelledby="might-heading"><div className="section-heading"><div><p className="section-kicker">02 · PREDICTED</p><h2 id="might-heading">What might happen?</h2></div><Link href="/cash-flow">Explore cash flow →</Link></div>
              {risks.isLoading && <SkeletonCards count={2} />}
              {risks.error && <InlineError message={risks.error.message} retry={() => risks.refetch()} />}
              <div className="two-column">{risks.data?.risks.slice(0, 2).map((risk) => <InsightCard kind="prediction" key={risk.id} title={label(risk.risk_type)} value={<span className={`severity severity-${risk.severity}`}>{risk.severity} severity</span>} confidence={risk.confidence} basis={Object.entries(risk.evidence).map(([key, value]) => `${label(key)}: ${String(value)}`)} />)}{risks.data?.risks.length === 0 && <InsufficientData title="No active risks detected" message="The current Phase 4 risk rules did not find a supported warning in your data." />}</div>
            </section>
            <section aria-labelledby="do-heading"><div className="section-heading"><div><p className="section-kicker">03 · RECOMMENDED</p><h2 id="do-heading">What should I do?</h2></div><Link href="/recommendations">View all actions →</Link></div>
              {recommendations.isLoading && <SkeletonCards count={2} />}
              {recommendations.error && <InlineError message={recommendations.error.message} retry={() => recommendations.refetch()} />}
              <div className="two-column">{recommendations.data?.recommendations.slice(0, 2).map((item) => <InsightCard kind="recommendation" key={item.id} title={item.title} value={item.reason} confidence={item.confidence} basis={item.assumptions} actions={<Link className="secondary link-button" href={`/simulate?action=${item.action.type ?? "reduce_spending"}`}>Simulate this</Link>} />)}{recommendations.data?.recommendations.length === 0 && <InsufficientData title="No action needed yet" message="No evidence-backed recommendation is active for this financial picture." />}</div>
            </section>
            <section className="surface-card" aria-labelledby="forecast-heading"><div className="section-heading"><div><p className="section-kicker">04 · EXPECTED IMPACT</p><h2 id="forecast-heading">Thirty-day cash-flow outlook</h2></div>{forecast.data && <span className={`confidence confidence-${forecast.data.confidence}`}>{forecast.data.confidence} confidence</span>}</div>
              {forecast.isLoading && <div className="skeleton skeleton-chart" />}{forecast.error && <InlineError message={forecast.error.message} retry={() => forecast.refetch()} />}{forecast.data && <><CashFlowChart points={forecast.data.daily_projection} /><p className="chart-summary">Projected from {forecast.data.as_of_date} using {forecast.data.method}. The shaded band communicates uncertainty; the line is the modeled balance.</p></>}
            </section>
            <div className="two-column"><section className="surface-card"><div className="section-heading compact"><h2>Recent transactions</h2><Link href="/transactions">See all</Link></div><div className="list">{transactions.data?.transactions.map((item) => <div className="list-row" key={item.id}><div><strong>{item.raw_description}</strong><span>{item.txn_date}</span></div><b className={item.direction === "credit" ? "positive" : ""}>{item.direction === "credit" ? "+" : "−"}{money(item.amount)}</b></div>)}</div></section><section className="surface-card"><div className="section-heading compact"><h2>Recurring payments</h2><Link href="/cash-flow">View schedule</Link></div><div className="list">{recurring.data?.recurring.slice(0, 5).map((item) => <div className="list-row" key={item.id}><div><strong>{item.merchant}</strong><span>{item.frequency} · {item.status}</span></div><b>{money(item.amount)}</b></div>)}</div></section></div>
          </>
        )}
      </main>
    </AppShell>
  );
}
