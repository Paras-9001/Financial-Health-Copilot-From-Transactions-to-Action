"use client";
import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/components/auth-provider";
import { api, ApiError, type User } from "@/lib/api";

export default function Dashboard() {
  const { user, token, logout } = useAuth();
  const router = useRouter();
  const profile = useQuery({
    queryKey: ["me", user?.id],
    queryFn: () => api<User>("/users/me", {}, token!),
    enabled: Boolean(token),
    retry: false,
    refetchInterval: 60000,
  });
  useEffect(() => {
    if (!token) router.replace("/login");
  }, [token, router]);
  if (!user || !token)
    return (
      <main className="loading" role="status">
        Opening your workspace…
      </main>
    );
  const sessionExpired =
    profile.error instanceof ApiError && profile.error.status === 401;
  if (sessionExpired)
    return (
      <main className="loading">
        <h1>Your session has ended</h1>
        <p>Please log in again to continue.</p>
        <button
          className="primary"
          onClick={() => {
            logout();
            router.replace("/login");
          }}
        >
          Return to login
        </button>
      </main>
    );
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-icon" aria-hidden="true">
            ↗
          </span>
          <span>
            Financial Health
            <br />
            Copilot
          </span>
        </div>
        <p className="eyebrow nav-label">YOUR WORKSPACE</p>
        <nav aria-label="Main navigation">
          <Link className="nav-active" href="/" aria-current="page">
            ◈ <span>Overview</span>
          </Link>
        </nav>
        <div className="sidebar-note">
          <span className="small-dot" aria-hidden="true" /> A fresh start for
          your finances.
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <span>Overview</span>
          <div className="user-menu">
            <span>{user.name ?? user.email}</span>
            <button
              className="secondary"
              onClick={() => {
                logout();
                router.replace("/login");
              }}
            >
              Log out
            </button>
          </div>
        </header>
        <main className="dashboard">
          <div className="page-heading">
            <p className="eyebrow">YOUR FINANCIAL PICTURE</p>
            <h1>Welcome, {user.name?.split(" ")[0] ?? "there"}.</h1>
            <p className="muted">
              A clear starting point for your next financial decision.
            </p>
          </div>
          {profile.error && (
            <div className="error" role="alert">
              We couldn’t refresh your profile.{" "}
              <button className="text-button" onClick={() => profile.refetch()}>
                Try again
              </button>
            </div>
          )}
          <section className="empty-hero" aria-labelledby="empty-heading">
            <div className="empty-icon" aria-hidden="true">
              ◎
            </div>
            <p className="eyebrow">YOUR WORKSPACE IS READY</p>
            <h2 id="empty-heading">Your financial picture starts here</h2>
            <p>
              There’s no financial data in your workspace yet. Once accounts and
              transactions are added, this space will help you understand your
              money and explore what to do next.
            </p>
            <div className="empty-note">
              Account and transaction entry will be available in the next
              release.
            </div>
          </section>
          <section className="overview-grid" aria-label="Financial overview">
            {[
              [
                "Where am I?",
                "Income, spending and savings",
                "Add financial history to see your current position.",
              ],
              [
                "What might happen?",
                "Upcoming cash-flow pressure",
                "A forecast will appear when enough data is available.",
              ],
              [
                "What can I do?",
                "Actions and expected impact",
                "Recommendations will include the effect of each action.",
              ],
            ].map(([title, subtitle, body], index) => (
              <article className="overview-card" key={title}>
                <span className="step-number">0{index + 1}</span>
                <h2>{title}</h2>
                <h3>{subtitle}</h3>
                <p>{body}</p>
                <span className="unavailable">Awaiting financial data</span>
              </article>
            ))}
          </section>
          <footer className="dashboard-footer">
            You stay in control. The copilot helps you plan; it doesn’t move
            your money.
          </footer>
        </main>
      </div>
    </div>
  );
}
