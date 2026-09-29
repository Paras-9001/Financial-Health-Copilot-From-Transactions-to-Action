"use client";

import { Suspense, useState, type FormEvent } from "react";
import { useSearchParams } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AppShell, PageHeader } from "@/components/app-shell";
import { ConfidenceBadge, InsightBadge } from "@/components/insight-card";
import { InlineError } from "@/components/states";
import { useAuth } from "@/components/auth-provider";
import { api } from "@/lib/api";
import type { Category, DebtSummary, Recurring, Simulation } from "@/lib/types";
import { label } from "@/lib/types";

const actions = [
  ["reduce_spending", "Reduce spending"], ["increase_savings", "Increase savings"], ["extra_debt_payment", "Pay extra on debt"], ["delay_purchase", "Delay a purchase"], ["modify_recurring", "Change recurring payment"], ["change_income", "Change income"],
] as const;

function SimulationWorkspace() {
  const { token } = useAuth();
  const params = useSearchParams();
  const initial = actions.some(([value]) => value === params.get("action")) ? params.get("action")! : "reduce_spending";
  const [action, setAction] = useState(initial);
  const categories = useQuery({ queryKey: ["categories"], queryFn: () => api<{ categories: Category[] }>("/categories", {}, token!), enabled: Boolean(token) });
  const debt = useQuery({ queryKey: ["debt"], queryFn: () => api<DebtSummary>("/debt/summary", {}, token!), enabled: Boolean(token), retry: false });
  const recurring = useQuery({ queryKey: ["recurring"], queryFn: () => api<{ recurring: Recurring[] }>("/recurring-expenses", {}, token!), enabled: Boolean(token), retry: false });
  const simulation = useMutation({ mutationFn: (body: unknown) => api<Simulation>("/simulate", { method: "POST", body: JSON.stringify(body) }, token!) });
  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const data = new FormData(event.currentTarget); const raw = Object.fromEntries(data.entries()); const payload: Record<string, unknown> = {}; Object.entries(raw).forEach(([key, value]) => { if (key !== "action_type" && value !== "") payload[key] = value; }); if (action === "modify_recurring") payload.cancel = data.get("cancel") === "true"; simulation.mutate({ action_type: action, params: payload, horizon_days: 90 }); }
  const fields = () => {
    if (action === "reduce_spending") return <><label>Category<select name="category" required>{categories.data?.categories.filter((item) => ["variable", "discretionary"].includes(item.type)).map((item) => <option key={item.id}>{item.name}</option>)}</select></label><Amount /></>;
    if (action === "increase_savings") return <Amount labelText="Monthly savings amount" />;
    if (action === "extra_debt_payment") return <><label>Loan<select name="loan_id" required>{debt.data?.loans.map((item) => <option value={item.id} key={item.id}>Loan · {item.outstanding_balance} outstanding</option>)}</select></label><Amount labelText="Extra payment" /><label>Payment date<input name="date" type="date" /></label></>;
    if (action === "delay_purchase") return <><Amount labelText="Purchase amount" /><label>New purchase date<input name="new_date" type="date" required /></label><label>Original date (optional)<input name="original_date" type="date" /></label></>;
    if (action === "modify_recurring") return <><label>Recurring payment<select name="recurring_id" required>{recurring.data?.recurring.map((item) => <option value={item.id} key={item.id}>{item.merchant} · {item.amount}</option>)}</select></label><label>Change<select name="cancel"><option value="false">Set a new amount</option><option value="true">Cancel payment</option></select></label><label>New amount<input name="new_amount" type="number" min="0.01" step="0.01" /></label></>;
    return <><label>Income change<select name="direction"><option value="percent">Percentage change</option></select></label><label>Percent (negative for a fall)<input name="percent" type="number" step="0.1" required /></label><label>Effective date<input name="effective_date" type="date" /></label></>;
  };
  return <AppShell><main className="dashboard page-stack"><PageHeader eyebrow="DETERMINISTIC WHAT-IF" title="What if I…" description="Change one input and compare the same forecast engine before and after." />
    <section className="surface-card"><form onSubmit={submit} className="simulator-form"><label className="action-picker">Scenario<select value={action} onChange={(event) => { setAction(event.target.value); simulation.reset(); }}>{actions.map(([value, text]) => <option value={value} key={value}>{text}</option>)}</select></label><div className="form-grid">{fields()}</div><button className="primary" disabled={simulation.isPending}>{simulation.isPending ? "Running model…" : "Run simulation"}</button>{simulation.error && <InlineError message={simulation.error.message} />}</form></section>
    {simulation.data && <><div className="comparison"><section className="comparison-panel baseline"><InsightBadge kind="prediction" confidence={simulation.data.confidence} /><h2>Baseline</h2><ResultRows value={simulation.data.baseline} /></section><section className="comparison-panel proposed"><InsightBadge kind="prediction" confidence={simulation.data.confidence} /><h2>Proposed</h2><ResultRows value={simulation.data.proposed} /></section></div><section className="surface-card"><div className="section-heading"><h2>Modeled change</h2><ConfidenceBadge value={simulation.data.confidence} /></div><ResultRows value={simulation.data.delta} /><div className="assumption-note"><InsightBadge kind="assumption" /><p>{simulation.data.trade_off_note}</p></div></section></>}
  </main></AppShell>;
}

function Amount({ labelText = "Amount" }: { labelText?: string }) { return <label>{labelText}<input name="amount" type="number" min="0.01" step="0.01" required /></label>; }
function ResultRows({ value }: { value: Record<string, unknown> }) { return <div className="result-rows">{Object.entries(value).map(([key, item]) => <div key={key}><span>{label(key)}</span><strong>{typeof item === "object" ? JSON.stringify(item) : String(item ?? "—")}</strong></div>)}</div>; }
export default function SimulatePage() { return <Suspense fallback={<main className="loading">Opening simulator…</main>}><SimulationWorkspace /></Suspense>; }
