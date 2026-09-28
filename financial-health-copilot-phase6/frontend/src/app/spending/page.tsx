"use client";

import { useQuery } from "@tanstack/react-query";
import { AppShell, PageHeader } from "@/components/app-shell";
import { SpendingChart } from "@/components/charts";
import { InsightCard } from "@/components/insight-card";
import { InlineError, InsufficientData, SkeletonCards } from "@/components/states";
import { useAuth } from "@/components/auth-provider";
import { api, ApiError } from "@/lib/api";
import type { SpendingCategory } from "@/lib/types";
import { money } from "@/lib/types";

export default function SpendingPage() {
  const { token } = useAuth();
  const spending = useQuery({ queryKey: ["spending"], queryFn: () => api<{ categories: SpendingCategory[] }>("/spending/by-category", {}, token!), enabled: Boolean(token), retry: false });
  const noData = spending.error instanceof ApiError && spending.error.code === "no_data";
  return <AppShell><main className="dashboard page-stack"><PageHeader eyebrow="OBSERVED PATTERNS" title="Spending" description="See where money went, with fixed and discretionary spending kept distinct." />
    {spending.isLoading && <SkeletonCards count={3} />}{noData && <InsufficientData message="Add at least one period of transactions to see a supported spending breakdown." />}{spending.error && !noData && <InlineError message={spending.error.message} retry={() => spending.refetch()} />}
    {spending.data && <><section className="surface-card"><div className="section-heading"><div><p className="section-kicker">CATEGORY BREAKDOWN</p><h2>Your largest spending areas</h2></div></div><SpendingChart categories={spending.data.categories} /><p className="chart-summary">The bars show recorded debit transactions by category. Uncategorized spending remains visible rather than being guessed.</p></section><section><div className="section-heading"><h2>Top categories</h2></div><div className="three-column">{spending.data.categories.slice(0, 3).map((item) => <InsightCard kind="fact" key={item.name} title={item.name} value={money(item.amount)}><p>{item.pct_of_total}% of total · {item.type}</p></InsightCard>)}</div></section><section className="surface-card"><h2>All categories</h2><div className="list">{spending.data.categories.map((item) => <div className="list-row" key={item.name}><div><strong>{item.name}</strong><span>{item.type}</span></div><div className="align-right"><b>{money(item.amount)}</b><span>{item.pct_of_total}%</span></div></div>)}</div></section></>}
  </main></AppShell>;
}
