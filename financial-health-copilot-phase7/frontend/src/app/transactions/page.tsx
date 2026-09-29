"use client";

import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell, PageHeader } from "@/components/app-shell";
import { InlineError, SkeletonCards } from "@/components/states";
import { useAuth } from "@/components/auth-provider";
import { useRecalculation } from "@/components/recalculation-provider";
import { api } from "@/lib/api";
import type { Account, Category, Transaction, TransactionIngestResponse } from "@/lib/types";
import { money } from "@/lib/types";

export default function TransactionsPage() {
  const { token } = useAuth();
  const { captureSnapshot, completeRecalculation } = useRecalculation();
  const client = useQueryClient();
  const [merchant, setMerchant] = useState("");
  const [category, setCategory] = useState("");
  const [showForm, setShowForm] = useState(false);
  const query = new URLSearchParams({ page_size: "100", ...(merchant ? { merchant } : {}) });
  const transactions = useQuery({ queryKey: ["transactions", merchant], queryFn: () => api<{ transactions: Transaction[]; total_count: number }>(`/transactions?${query}`, {}, token!), enabled: Boolean(token), retry: false });
  const categories = useQuery({ queryKey: ["categories"], queryFn: () => api<{ categories: Category[] }>("/categories", {}, token!), enabled: Boolean(token) });
  const accounts = useQuery({ queryKey: ["accounts"], queryFn: () => api<{ accounts: Account[] }>("/accounts", {}, token!), enabled: Boolean(token) });
  const add = useMutation({
    mutationFn: async (payload: { transactions: Array<{ account_id: FormDataEntryValue | null; txn_date: FormDataEntryValue | null; amount: FormDataEntryValue | null; direction: FormDataEntryValue | null; raw_description: FormDataEntryValue | null }> }) => {
      const before = await captureSnapshot();
      const result = await api<TransactionIngestResponse>("/transactions", { method: "POST", body: JSON.stringify(payload) }, token!);
      return { before, payload, result };
    },
    onSuccess: async ({ before, payload, result }) => {
      setShowForm(false);
      await client.invalidateQueries({ queryKey: ["transactions"] });
      if (result.recalculation_triggered) {
        const transaction = payload.transactions[0];
        await completeRecalculation(before, {
          label: "Transaction added and analysis recalculated",
          detail: `${money(transaction.amount)} ${String(transaction.raw_description)} is now included in every dashboard, risk, and recommendation.`,
        });
      }
    },
  });
  const correct = useMutation({
    mutationFn: async ({ id, categoryId }: { id: string; categoryId: string }) => {
      const before = await captureSnapshot();
      await api(`/transactions/${id}`, { method: "PATCH", body: JSON.stringify({ category_id: categoryId }) }, token!);
      return { before };
    },
    onSuccess: async ({ before }) => {
      await client.invalidateQueries({ queryKey: ["transactions"] });
      await completeRecalculation(before, { label: "Category corrected and analysis recalculated" });
    },
  });
  const rows = transactions.data?.transactions.filter((item) => !category || item.category_id === category) ?? [];
  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const data = new FormData(event.currentTarget); add.mutate({ transactions: [{ account_id: data.get("account"), txn_date: data.get("date"), amount: data.get("amount"), direction: data.get("direction"), raw_description: data.get("description") }] }); }
  return <AppShell><main className="dashboard page-stack"><PageHeader eyebrow="OBSERVED DATA" title="Transactions" description="Search, add, and correct the records behind every calculation." actions={<button className="primary" onClick={() => setShowForm(!showForm)}>＋ Add transaction</button>} />
    {showForm && <section className="surface-card"><h2>Add a transaction</h2><p className="muted">Saving new activity recalculates your dashboard, risks, forecast, and recommendations.</p><form className="form-grid" onSubmit={submit}><label>Account<select name="account" required><option value="">Select an account</option>{accounts.data?.accounts.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label><label>Date<input name="date" type="date" defaultValue={new Date().toISOString().slice(0, 10)} required /></label><label>Amount<input name="amount" type="number" min="0.01" step="0.01" required /></label><label>Direction<select name="direction"><option value="debit">Expense</option><option value="credit">Income</option></select></label><label className="span-2">Description<input name="description" required maxLength={240} placeholder="e.g. Medical expense" /></label><div className="span-2 card-actions"><button className="primary" disabled={add.isPending}>{add.isPending ? "Recalculating…" : "Save and recalculate"}</button><button className="secondary" type="button" onClick={() => setShowForm(false)}>Cancel</button></div>{add.error && <InlineError message={add.error.message} />}</form></section>}
    <section className="surface-card"><div className="filters"><label>Search merchant<input value={merchant} onChange={(event) => setMerchant(event.target.value)} placeholder="e.g. Swiggy" /></label><label>Category<select value={category} onChange={(event) => setCategory(event.target.value)}><option value="">All categories</option>{categories.data?.categories.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label><span className="result-count">{rows.length} shown</span></div>
      {transactions.isLoading && <SkeletonCards count={3} />}{transactions.error && <InlineError message={transactions.error.message} retry={() => transactions.refetch()} />}
      <div className="table-wrap"><table><thead><tr><th>Date</th><th>Description</th><th>Category</th><th>Amount</th></tr></thead><tbody>{rows.map((item) => <tr key={item.id}><td>{item.txn_date}</td><td>{item.raw_description}</td><td><select className={item.category_id ? "table-select" : "table-select uncategorized"} value={item.category_id ?? ""} aria-label={`Category for ${item.raw_description}`} onChange={(event) => correct.mutate({ id: item.id, categoryId: event.target.value })}><option value="" disabled>Uncategorized</option>{categories.data?.categories.map((cat) => <option value={cat.id} key={cat.id}>{cat.name}</option>)}</select></td><td className={item.direction === "credit" ? "positive amount" : "amount"}>{item.direction === "credit" ? "+" : "−"}{money(item.amount)}</td></tr>)}</tbody></table></div>
    </section>
  </main></AppShell>;
}
