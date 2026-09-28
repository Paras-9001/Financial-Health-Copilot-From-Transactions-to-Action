import type { ReactNode } from "react";

export function SkeletonCards({ count = 3 }: { count?: number }) {
  return <div className="skeleton-grid" role="status" aria-label="Loading financial data">{Array.from({ length: count }).map((_, index) => <div className="skeleton-card" key={index}><div className="skeleton skeleton-pill" /><div className="skeleton skeleton-title" /><div className="skeleton skeleton-line" /></div>)}</div>;
}

export function InsufficientData({ title = "More data needed", message, action }: { title?: string; message: string; action?: ReactNode }) {
  return <section className="state-card"><span className="state-icon" aria-hidden="true">◎</span><h2>{title}</h2><p>{message}</p>{action && <div className="card-actions">{action}</div>}</section>;
}

export function InlineError({ message, retry }: { message: string; retry?: () => void }) {
  return <div className="error inline-error" role="alert"><span>{message}</span>{retry && <button className="text-button" onClick={retry}>Try again</button>}</div>;
}
