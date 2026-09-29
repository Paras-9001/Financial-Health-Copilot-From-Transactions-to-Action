"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AppShell, PageHeader } from "@/components/app-shell";
import { CashFlowChart } from "@/components/charts";
import { ConfidenceBadge, InsightCard } from "@/components/insight-card";
import { InlineError, InsufficientData, SkeletonCards } from "@/components/states";
import { useAuth } from "@/components/auth-provider";
import { api, ApiError } from "@/lib/api";
import type { Forecast, Recurring, Risk } from "@/lib/types";
import { label, money } from "@/lib/types";

export default function CashFlowPage() {
  const { token } = useAuth();
  const [horizon, setHorizon] = useState(30);
  const forecast = useQuery({ queryKey: ["forecast", horizon], queryFn: () => api<Forecast>(`/cash-flow/forecast?horizon_days=${horizon}`, {}, token!), enabled: Boolean(token), retry: false });
  const recurring = useQuery({ queryKey: ["recurring"], queryFn: () => api<{ recurring: Recurring[] }>("/recurring-expenses", {}, token!), enabled: Boolean(token), retry: false });
  const risks = useQuery({ queryKey: ["risks"], queryFn: () => api<{ risks: Risk[] }>("/risks", {}, token!), enabled: Boolean(token), retry: false });
  const noData = forecast.error instanceof ApiError && forecast.error.code === "no_data";
  const minimum = forecast.data?.daily_projection.reduce((lowest, point) => Number(point.projected_balance) < Number(lowest.projected_balance) ? point : lowest, forecast.data.daily_projection[0]);
  return <AppShell><main className="dashboard page-stack"><PageHeader eyebrow="PREDICTED OUTLOOK" title="Cash flow" description="A deterministic forecast of balances, uncertainty, and upcoming obligations." actions={<label className="inline-control">Horizon<select value={horizon} onChange={(event) => setHorizon(Number(event.target.value))}><option value={30}>30 days</option><option value={60}>60 days</option><option value={90}>90 days</option></select></label>} />
    {forecast.isLoading && <SkeletonCards count={3} />}{noData && <InsufficientData message="A cash-flow forecast needs transactions, an account balance, and enough history to anchor the model." />}{forecast.error && !noData && <InlineError message={forecast.error.message} retry={() => forecast.refetch()} />}
    {forecast.data && <><div className="three-column"><InsightCard kind="prediction" title="Forecast confidence" value={<ConfidenceBadge value={forecast.data.confidence} />} confidence={forecast.data.confidence} basis={forecast.data.assumptions} /><InsightCard kind="prediction" title="Lowest projected balance" value={minimum ? money(minimum.projected_balance) : "—"} confidence={forecast.data.confidence}><p>{minimum?.date ?? "No projected point"}</p></InsightCard><InsightCard kind="assumption" title="History coverage" value={`${forecast.data.history_days} days`}><p>{forecast.data.recurring_coverage_pct}% recurring coverage</p></InsightCard></div><section className="surface-card"><div className="section-heading"><h2>Projected balance and confidence band</h2><ConfidenceBadge value={forecast.data.confidence} /></div><CashFlowChart points={forecast.data.daily_projection} /><p className="chart-summary">The violet line is the projected balance. The shaded region is the lower-to-upper confidence range. It is a prediction, not a guaranteed outcome.</p></section></>}
    <div className="two-column"><section className="surface-card"><div className="section-heading compact"><h2>Upcoming recurring payments</h2></div>{recurring.error && <InlineError message={recurring.error.message} />}{recurring.data?.recurring.length === 0 && <p className="muted">No recurring pattern is supported yet.</p>}<div className="list">{recurring.data?.recurring.map((item) => <div className="list-row" key={item.id}><div><strong>{item.merchant}</strong><span>{item.next_expected_date ?? "Date not established"} · {item.status}</span></div><b>{money(item.amount)}</b></div>)}</div></section><section className="surface-card"><div className="section-heading compact"><h2>Cash-flow risks</h2></div>{risks.error && <InlineError message={risks.error.message} />}{risks.data?.risks.filter((risk) => risk.risk_type.includes("cash") || risk.risk_type.includes("buffer")).map((risk) => <div className="risk-row" key={risk.id}><span className={`severity severity-${risk.severity}`}>{risk.severity}</span><div><strong>{label(risk.risk_type)}</strong><p>{Object.values(risk.evidence).map(String).join(" · ")}</p></div></div>)}</section></div>
  </main></AppShell>;
}
