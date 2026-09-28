"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { AppShell, PageHeader } from "@/components/app-shell";
import { InsightCard } from "@/components/insight-card";
import { InlineError, InsufficientData, SkeletonCards } from "@/components/states";
import { useAuth } from "@/components/auth-provider";
import { api, ApiError } from "@/lib/api";
import type { DebtSummary } from "@/lib/types";
import { money } from "@/lib/types";

export default function DebtPage() {
  const { token } = useAuth();
  const debt = useQuery({ queryKey: ["debt"], queryFn: () => api<DebtSummary>("/debt/summary", {}, token!), enabled: Boolean(token), retry: false });
  const noData = debt.error instanceof ApiError && debt.error.code === "no_debt_data";
  return <AppShell><main className="dashboard page-stack"><PageHeader eyebrow="OBSERVED OBLIGATIONS" title="Debt overview" description="Understand balances, repayment pressure, and where an extra payment could help." />
    {debt.isLoading && <SkeletonCards count={4} />}{noData && <InsufficientData title="No debt data supplied" message="This is not treated as zero debt. Add a loan or credit card during onboarding to unlock debt analysis." action={<Link href="/onboarding?mode=manual" className="primary link-button">Add debt details</Link>} />}{debt.error && !noData && <InlineError message={debt.error.message} retry={() => debt.refetch()} />}
    {debt.data && <><div className="four-column"><InsightCard kind="fact" title="Total debt" value={money(debt.data.total_debt)} /><InsightCard kind="fact" title="Debt to income" value={`${debt.data.dti}%`} /><InsightCard kind="fact" title="Debt service" value={`${debt.data.debt_service_ratio}%`} /><InsightCard kind="fact" title="Card utilization" value={`${debt.data.credit_utilization}%`} /></div><section className="page-stack"><div className="section-heading"><h2>Loans</h2></div>{debt.data.loans.map((loan) => { const paid = Math.max(0, 100 - Number(loan.outstanding_balance) / Number(loan.principal) * 100); return <article className="surface-card debt-card" key={loan.id}><div><span className="insight-badge badge-fact">● FACT</span><h3>Personal loan</h3><p className="hero-number">{money(loan.outstanding_balance)}</p><p className="muted">outstanding from {money(loan.principal)}</p></div><div className="debt-details"><div className="progress"><span style={{ width: `${paid}%` }} /></div><p>{paid.toFixed(0)}% principal repaid · {loan.interest_rate}% interest</p><p>Monthly installment {money(loan.monthly_installment)}</p><Link className="secondary link-button" href={`/simulate?action=extra_debt_payment&loan=${loan.id}`}>Try an extra payment</Link></div></article>; })}</section><section className="page-stack"><div className="section-heading"><h2>Credit cards</h2></div><div className="two-column">{debt.data.credit_cards.map((card) => { const utilization = Number(card.current_balance) / Number(card.credit_limit) * 100; return <article className="surface-card" key={card.id}><span className="insight-badge badge-fact">● FACT</span><h3>Credit card</h3><p className="hero-number">{money(card.current_balance)}</p><p className="muted">of {money(card.credit_limit)} limit</p><div className="progress"><span style={{ width: `${Math.min(100, utilization)}%` }} /></div><p>{utilization.toFixed(1)}% utilized · minimum due {money(card.minimum_due)}</p></article>; })}</div></section></>}
  </main></AppShell>;
}
