"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell, PageHeader } from "@/components/app-shell";
import { InsightCard } from "@/components/insight-card";
import { InlineError } from "@/components/states";
import { useAuth } from "@/components/auth-provider";
import { api } from "@/lib/api";
import type { ChatHistoryMessage, ChatResponse, Claim } from "@/lib/types";

export default function ChatPage() {
  const { token, user } = useAuth();
  const client = useQueryClient();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionError, setSessionError] = useState("");
  const creating = useRef(false);
  useEffect(() => {
    if (!token || !user || creating.current) return;
    const saved = window.localStorage.getItem(`fhc-chat-${user.id}`);
    if (saved) {
      queueMicrotask(() => setSessionId(saved));
      return;
    }
    creating.current = true;
    api<{ session_id: string }>("/chat/sessions", { method: "POST" }, token).then((result) => { window.localStorage.setItem(`fhc-chat-${user.id}`, result.session_id); setSessionId(result.session_id); }).catch((error: Error) => setSessionError(error.message));
  }, [token, user]);
  const history = useQuery({ queryKey: ["chat-history", sessionId], queryFn: () => api<ChatHistoryMessage[]>(`/chat/sessions/${sessionId}/messages`, {}, token!), enabled: Boolean(token && sessionId), retry: false });
  const send = useMutation({ mutationFn: (message: string) => api<ChatResponse>(`/chat/sessions/${sessionId}/messages`, { method: "POST", body: JSON.stringify({ message }) }, token!), onSuccess: async () => { await client.invalidateQueries({ queryKey: ["chat-history", sessionId] }); } });
  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const form = event.currentTarget; const data = new FormData(form); const message = String(data.get("message") ?? "").trim(); if (!message) return; send.mutate(message); form.reset(); }
  const messages = history.data ?? [];
  return <AppShell><main className="dashboard chat-page"><PageHeader eyebrow="GROUNDED CONVERSATION" title="AI Copilot" description="Ask about your finances. Every number comes from a deterministic tool result." />
    <section className="chat-window" aria-live="polite"><div className="chat-messages">{messages.length === 0 && !history.isLoading && <div className="chat-welcome"><span className="state-icon">✦</span><h2>What would you like to understand?</h2><p>Try “Can I afford a ₹30,000 laptop next week?” or “What should I focus on this month?”</p></div>}{messages.map((message) => <article className={`chat-message chat-${message.role}`} key={message.id}><div className="message-meta">{message.role === "assistant" ? "COPILOT" : "YOU"}</div><p>{message.content}</p>{message.structured_answer && <StructuredAnswer value={message.structured_answer} />}</article>)}{send.isPending && <article className="chat-message chat-assistant"><div className="message-meta">COPILOT</div><div className="thinking"><span /><span /><span /></div></article>}</div>
      {(sessionError || history.error || send.error) && <InlineError message={sessionError || history.error?.message || send.error?.message || "Chat is unavailable."} />}
      <form className="chat-composer" onSubmit={submit}><label className="sr-only" htmlFor="chat-message">Type a question</label><textarea id="chat-message" name="message" placeholder="Ask about spending, debt, cash flow, or a decision…" maxLength={4000} required /><button className="primary" disabled={!sessionId || send.isPending}>Send</button></form></section>
  </main></AppShell>;
}

function StructuredAnswer({ value }: { value: ChatResponse }) {
  const claims: Claim[] = [...value.facts, ...value.predictions, ...value.recommendations, ...value.assumptions];
  return <div className="chat-claims">{claims.map((claim, index) => <InsightCard key={`${claim.type}-${claim.label}-${index}`} kind={claim.type} title={claim.label} value={formatValue(claim.value)} confidence={claim.confidence} basis={claim.basis} />)}{value.missing_information.length > 0 && <p className="missing-note">Missing: {value.missing_information.join(", ")}</p>}<p className="grounding-note">{value.grounded ? "✓ Grounded response" : "Grounding unavailable"} · {value.provider}</p></div>;
}
function formatValue(value: unknown) { if (value === null || value === undefined) return "—"; return typeof value === "object" ? JSON.stringify(value) : String(value); }
