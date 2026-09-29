"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AppShell, PageHeader } from "@/components/app-shell";
import { InsightCard } from "@/components/insight-card";
import { InlineError, InsufficientData, SkeletonCards } from "@/components/states";
import { useAuth } from "@/components/auth-provider";
import { api } from "@/lib/api";
import type { Recommendation } from "@/lib/types";

export default function RecommendationsPage() {
  const { token } = useAuth();
  const [historyId, setHistoryId] = useState<string | null>(null);
  const recommendations = useQuery({ queryKey: ["recommendations"], queryFn: () => api<{ recommendations: Recommendation[] }>("/recommendations", {}, token!), enabled: Boolean(token), retry: false });
  const history = useQuery({ queryKey: ["recommendation-history", historyId], queryFn: () => api<{ timeline: Array<{ timestamp: string; status: string; expected_impact: Record<string, unknown> }> }>(`/recommendations/${historyId}/history`, {}, token!), enabled: Boolean(token && historyId), retry: false });
  return <AppShell><main className="dashboard page-stack"><PageHeader eyebrow="EVIDENCE-BACKED ACTIONS" title="Recommendations" description="Every action is tied to an active risk, expected impact, and confidence level." />
    {recommendations.isLoading && <SkeletonCards count={3} />}{recommendations.error && <InlineError message={recommendations.error.message} retry={() => recommendations.refetch()} />}{recommendations.data?.recommendations.length === 0 && <InsufficientData title="No active recommendation" message="The current risk analysis did not support a specific action. Generic advice is intentionally excluded." />}
    <div className="recommendation-list">{recommendations.data?.recommendations.map((item) => <InsightCard kind="recommendation" key={item.id} title={item.title} value={item.reason} confidence={item.confidence} basis={item.assumptions} className="recommendation-wide" actions={<><Link className="primary link-button" href={`/simulate?action=${String(item.action.type ?? "reduce_spending")}`}>Simulate this</Link><button className="secondary" onClick={() => setHistoryId(historyId === item.id ? null : item.id)}>View history</button></>}><div className="evidence-grid"><div><span>Priority</span><strong>{item.priority}</strong></div><div><span>Action</span><strong>{String(item.action.type ?? "Defined action").replaceAll("_", " ")}</strong></div><div><span>Expected impact</span><strong>{Object.entries(item.expected_impact).slice(0, 2).map(([key, value]) => `${key.replaceAll("_", " ")}: ${typeof value === "object" ? JSON.stringify(value) : String(value)}`).join(" · ") || "See simulation"}</strong></div></div>{historyId === item.id && <div className="history-panel">{history.isLoading && <p>Loading history…</p>}{history.error && <InlineError message={history.error.message} />}{history.data?.timeline.map((entry) => <div className="history-row" key={entry.timestamp}><time>{entry.timestamp.slice(0, 10)}</time><span>{entry.status}</span><code>{JSON.stringify(entry.expected_impact)}</code></div>)}</div>}</InsightCard>)}</div>
  </main></AppShell>;
}
