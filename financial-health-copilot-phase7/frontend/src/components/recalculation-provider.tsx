"use client";

import Link from "next/link";
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/components/auth-provider";
import { api } from "@/lib/api";
import type {
  FinancialSummary,
  Recommendation,
  Risk,
} from "@/lib/types";
import { label, money } from "@/lib/types";

type Snapshot = {
  summary: FinancialSummary | null;
  risks: Risk[];
  recommendations: Recommendation[];
};

type RecalculationCause = {
  label: string;
  detail?: string;
};

type ToastState = {
  cause: RecalculationCause;
  changes: string[];
};

type RecalculationContextValue = {
  captureSnapshot: () => Promise<Snapshot>;
  completeRecalculation: (
    before: Snapshot,
    cause: RecalculationCause,
  ) => Promise<void>;
};

const RecalculationContext = createContext<RecalculationContextValue | null>(
  null,
);

const financialQueryKeys = [
  "accounts",
  "transactions",
  "financial-summary",
  "spending",
  "forecast",
  "recurring",
  "risks",
  "recommendations",
  "recommendation-history",
  "debt",
] as const;

export function RecalculationProvider({ children }: { children: ReactNode }) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [toast, setToast] = useState<ToastState | null>(null);

  const captureSnapshot = useCallback(async (): Promise<Snapshot> => {
    if (!token) return { summary: null, risks: [], recommendations: [] };
    const [summary, risks, recommendations] = await Promise.all([
      api<FinancialSummary>("/financial-summary", {}, token).catch(() => null),
      api<{ risks: Risk[] }>("/risks", {}, token).then((value) => value.risks).catch(() => []),
      api<{ recommendations: Recommendation[] }>("/recommendations", {}, token)
        .then((value) => value.recommendations)
        .catch(() => []),
    ]);
    return { summary, risks, recommendations };
  }, [token]);

  const completeRecalculation = useCallback(
    async (before: Snapshot, cause: RecalculationCause) => {
      await Promise.all(
        financialQueryKeys.map((queryKey) =>
          queryClient.invalidateQueries({ queryKey: [queryKey] }),
        ),
      );
      const after = await captureSnapshot();
      if (after.summary) {
        queryClient.setQueryData(["financial-summary"], after.summary);
      }
      queryClient.setQueryData(["risks"], { risks: after.risks });
      queryClient.setQueryData(
        ["recommendations"],
        { recommendations: after.recommendations },
      );
      setToast({ cause, changes: describeChanges(before, after) });
    },
    [captureSnapshot, queryClient],
  );

  const value = useMemo(
    () => ({ captureSnapshot, completeRecalculation }),
    [captureSnapshot, completeRecalculation],
  );

  return (
    <RecalculationContext.Provider value={value}>
      {children}
      {toast && (
        <RecalculationToast value={toast} dismiss={() => setToast(null)} />
      )}
    </RecalculationContext.Provider>
  );
}

export function useRecalculation() {
  const value = useContext(RecalculationContext);
  if (!value) throw new Error("RecalculationProvider is required");
  return value;
}

function describeChanges(before: Snapshot, after: Snapshot): string[] {
  const changes: string[] = [];
  const beforeFacts = before.summary?.facts;
  const afterFacts = after.summary?.facts;
  if (
    beforeFacts?.total_expenses !== afterFacts?.total_expenses &&
    beforeFacts?.total_expenses != null &&
    afterFacts?.total_expenses != null
  ) {
    changes.push(
      `Expenses changed from ${money(beforeFacts.total_expenses)} to ${money(afterFacts.total_expenses)}.`,
    );
  }
  if (
    beforeFacts?.cash_buffer_days !== afterFacts?.cash_buffer_days &&
    beforeFacts?.cash_buffer_days != null &&
    afterFacts?.cash_buffer_days != null
  ) {
    changes.push(
      `Cash buffer changed from ${beforeFacts.cash_buffer_days} to ${afterFacts.cash_buffer_days} days.`,
    );
  }

  const beforeRiskTypes = new Set(before.risks.map((risk) => risk.risk_type));
  const afterRiskTypes = new Set(after.risks.map((risk) => risk.risk_type));
  const newRisks = [...afterRiskTypes].filter((item) => !beforeRiskTypes.has(item));
  if (newRisks.length) {
    changes.push(`New risk detected: ${newRisks.map(label).join(", ")}.`);
  }
  const resolvedRisks = [...beforeRiskTypes].filter(
    (item) => !afterRiskTypes.has(item),
  );
  if (resolvedRisks.length) {
    changes.push(`Resolved risk: ${resolvedRisks.map(label).join(", ")}.`);
  }

  const beforeTop = before.recommendations[0]?.title;
  const afterTop = after.recommendations[0]?.title;
  if (afterTop && beforeTop !== afterTop) {
    changes.push(
      beforeTop
        ? `Top recommendation changed to “${afterTop}”.`
        : `New recommendation: “${afterTop}”.`,
    );
  }
  return changes.slice(0, 3);
}

function RecalculationToast({
  value,
  dismiss,
}: {
  value: ToastState;
  dismiss: () => void;
}) {
  return (
    <aside className="recalculation-toast" role="status" aria-live="polite">
      <div className="toast-icon" aria-hidden="true">↻</div>
      <div className="toast-content">
        <p className="eyebrow">FINANCIAL PICTURE UPDATED</p>
        <h2>{value.cause.label}</h2>
        {value.cause.detail && <p>{value.cause.detail}</p>}
        {value.changes.length ? (
          <ul>{value.changes.map((change) => <li key={change}>{change}</li>)}</ul>
        ) : (
          <p>The latest data is now included across your analysis.</p>
        )}
        <div className="toast-actions">
          <Link href="/recommendations" onClick={dismiss}>See what changed →</Link>
          <button className="text-button" onClick={dismiss}>Dismiss</button>
        </div>
      </div>
    </aside>
  );
}
