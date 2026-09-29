import type { ReactNode } from "react";

export type InsightKind = "fact" | "prediction" | "recommendation" | "assumption";
const meta = {
  fact: { icon: "●", label: "FACT" },
  prediction: { icon: "◆", label: "PREDICTION" },
  recommendation: { icon: "▶", label: "RECOMMENDATION" },
  assumption: { icon: "○", label: "ASSUMPTION" },
};

export function InsightBadge({ kind, confidence }: { kind: InsightKind; confidence?: string | null }) {
  const value = meta[kind];
  return (
    <span className={`insight-badge badge-${kind}`} aria-label={`${value.label}${confidence ? `, ${confidence} confidence` : ""}`}>
      <span aria-hidden="true">{value.icon}</span> {value.label}{confidence ? ` · ${confidence}` : ""}
    </span>
  );
}

export function InsightCard({ kind, title, value, confidence, basis, children, actions, className = "" }: {
  kind: InsightKind;
  title: string;
  value?: ReactNode;
  confidence?: string | null;
  basis?: string | string[] | null;
  children?: ReactNode;
  actions?: ReactNode;
  className?: string;
}) {
  const items = Array.isArray(basis) ? basis : basis ? [basis] : [];
  return (
    <article className={`insight-card insight-${kind} ${className}`}>
      <InsightBadge kind={kind} confidence={confidence} />
      <h3>{title}</h3>
      {value !== undefined && <div className="insight-value">{value}</div>}
      {children}
      {items.length > 0 && (
        <details className="why"><summary>Why?</summary><ul>{items.map((item) => <li key={item}>{item}</li>)}</ul></details>
      )}
      {actions && <div className="card-actions">{actions}</div>}
    </article>
  );
}

export function ConfidenceBadge({ value }: { value: string }) {
  return <span className={`confidence confidence-${value.toLowerCase()}`}>{value} confidence</span>;
}
