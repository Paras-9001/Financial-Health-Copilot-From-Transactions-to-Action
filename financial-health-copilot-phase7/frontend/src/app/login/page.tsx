"use client";
import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";
export default function LoginPage() {
  const router = useRouter();
  const { authenticate, token, ready } = useAuth();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    if (ready && token) router.replace("/");
  }, [ready, token, router]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    const values = new FormData(event.currentTarget);
    const password = String(values.get("password"));
    if (new TextEncoder().encode(password).length > 72) {
      setError("Use a password of at most 72 UTF-8 bytes.");
      setBusy(false);
      return;
    }
    try {
      await authenticate(
        mode,
        String(values.get("email")),
        password,
        String(values.get("name") ?? ""),
      );
      router.replace(mode === "signup" ? "/onboarding" : "/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Please try again.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="auth-layout">
      <section className="intro-panel">
        <div className="brand">
          <span className="brand-icon" aria-hidden="true">
            ↗
          </span>{" "}
          Financial Health Copilot
        </div>
        <div className="intro-copy">
          <p className="eyebrow">FROM TRANSACTIONS TO ACTION</p>
          <h1>
            A clearer view.
            <br />A better next step.
          </h1>
          <p>
            Bring your financial picture together, understand what may happen
            next, and explore your options.
          </p>
        </div>
        <p className="intro-foot">Your money. Your decisions.</p>
      </section>
      <section className="form-panel" aria-label="Account access">
        <div className="auth-card">
          <p className="eyebrow">LET’S GET STARTED</p>
          <h2>{mode === "login" ? "Welcome back" : "Create your account"}</h2>
          <p className="muted">
            {mode === "login"
              ? "Log in to your financial workspace."
              : "Start with a private workspace for your financial picture."}
          </p>
          <form onSubmit={submit} aria-busy={busy}>
            {mode === "signup" && (
              <label>
                Your name
                <input
                  name="name"
                  autoComplete="name"
                  required
                  maxLength={100}
                  placeholder="Your name"
                  disabled={busy}
                />
              </label>
            )}
            <label>
              Email address
              <input
                name="email"
                type="email"
                autoComplete="email"
                required
                placeholder="you@example.com"
                disabled={busy}
              />
            </label>
            <label>
              Password
              <input
                name="password"
                type="password"
                autoComplete={
                  mode === "signup" ? "new-password" : "current-password"
                }
                required
                minLength={mode === "signup" ? 12 : 1}
                maxLength={72}
                aria-describedby={
                  mode === "signup" ? "password-help" : undefined
                }
                disabled={busy}
              />
            </label>
            {mode === "signup" && (
              <p id="password-help" className="hint">
                Use at least 12 characters. A longer passphrase works well.
              </p>
            )}
            {error && (
              <p className="error" role="alert">
                {error}
              </p>
            )}
            <button className="primary" type="submit" disabled={busy}>
              {busy
                ? "Please wait…"
                : mode === "login"
                  ? "Log in"
                  : "Create account"}
            </button>
          </form>
          <p className="switch-text">
            {mode === "login" ? "New here? " : "Already have an account? "}
            <button
              className="text-button"
              disabled={busy}
              onClick={() => {
                setMode(mode === "login" ? "signup" : "login");
                setError("");
              }}
            >
              {mode === "login" ? "Create an account" : "Log in instead"}
            </button>
          </p>
          <p className="hint session-note">Your local demo session remains available after a refresh. Use a demo password you don’t use elsewhere.</p>
        </div>
      </section>
    </main>
  );
}
