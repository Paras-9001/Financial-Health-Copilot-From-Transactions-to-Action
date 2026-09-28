"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { useAuth } from "@/components/auth-provider";

const navigation = [
  ["/", "Overview", "⌂"],
  ["/transactions", "Transactions", "↕"],
  ["/spending", "Spending", "◒"],
  ["/cash-flow", "Cash flow", "⌁"],
  ["/debt", "Debt", "▤"],
  ["/recommendations", "Actions", "→"],
  ["/simulate", "Simulator", "⇄"],
  ["/chat", "Copilot", "✦"],
] as const;

export function AppShell({ children }: { children: ReactNode }) {
  const { user, token, ready, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  useEffect(() => {
    if (ready && !token) router.replace("/login");
  }, [ready, token, router]);
  if (!ready || !user || !token) {
    return (
      <main className="loading" role="status">
        <div className="skeleton skeleton-title" />
        <div className="skeleton skeleton-line" />
      </main>
    );
  }
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link className="brand brand-link" href="/">
          <span className="brand-icon" aria-hidden="true">↗</span>
          <span>Financial Health<br />Copilot</span>
        </Link>
        <p className="eyebrow nav-label">YOUR WORKSPACE</p>
        <nav aria-label="Main navigation">
          {navigation.map(([href, text, icon]) => {
            const active = href === "/" ? pathname === href : pathname.startsWith(href);
            return (
              <Link className={active ? "nav-active" : "nav-item"} href={href} key={href} aria-current={active ? "page" : undefined}>
                <span aria-hidden="true">{icon}</span><span>{text}</span>
              </Link>
            );
          })}
        </nav>
        <Link className="sidebar-onboarding" href="/onboarding">＋ Add financial data</Link>
        <p className="sidebar-note"><span className="small-dot" /> Calculations stay deterministic.</p>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div>
            <span className="mobile-brand">FHC</span>
            <span className="topbar-title">{navigation.find(([href]) => href === "/" ? pathname === href : pathname.startsWith(href))?.[1] ?? "Workspace"}</span>
          </div>
          <div className="user-menu">
            <span>{user.name ?? user.email}</span>
            <button className="secondary" onClick={() => { logout(); router.replace("/login"); }}>Log out</button>
          </div>
        </header>
        <nav className="mobile-nav" aria-label="Mobile navigation">
          {navigation.map(([href, text]) => <Link href={href} key={href}>{text}</Link>)}
        </nav>
        {children}
      </div>
    </div>
  );
}

export function PageHeader({ eyebrow, title, description, actions }: { eyebrow: string; title: string; description: string; actions?: ReactNode }) {
  return (
    <header className="page-heading page-heading-row">
      <div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p className="muted">{description}</p></div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  );
}
