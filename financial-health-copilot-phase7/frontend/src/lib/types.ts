export type Confidence = "low" | "medium" | "high";
export type Account = {
  id: string;
  type: string;
  name: string;
  balance: string;
  currency: string;
};
export type Category = { id: string; name: string; type: string };
export type Transaction = {
  id: string;
  account_id: string;
  txn_date: string;
  amount: string;
  direction: "debit" | "credit";
  raw_description: string;
  merchant_id: string | null;
  category_id: string | null;
  is_manual_override: boolean;
};
export type TransactionIngestResponse = {
  ingested: number;
  duplicates_skipped: number;
  rejected: Array<{ row: number; errors: Array<{ field: string; message: string }> }>;
  warnings: Array<{ row: number; code: string }>;
  recalculation_triggered: boolean;
};
export type FinancialSummary = {
  period: { start: string; end: string };
  facts: Record<string, string | null>;
  ratios: Record<string, string | null>;
  health_score: { value: number; confidence: Confidence; confidence_score: string };
  data_quality: {
    observation_periods: number;
    insufficient_history: boolean;
    uncategorized_transactions: number;
  };
};
export type SpendingCategory = {
  name: string;
  amount: string;
  pct_of_total: string;
  type: string;
};
export type ForecastPoint = {
  date: string;
  projected_balance: string;
  lower_bound: string;
  upper_bound: string;
  scheduled_inflow: string;
  scheduled_outflow: string;
  unscheduled_spend: string;
};
export type Forecast = {
  as_of_date: string;
  horizon_days: number;
  daily_projection: ForecastPoint[];
  confidence: Confidence;
  method: string;
  history_days: number;
  spending_cv: string;
  recurring_coverage_pct: string;
  assumptions: string[];
};
export type Risk = {
  id: string;
  risk_type: string;
  severity: "low" | "medium" | "high";
  evidence: Record<string, unknown>;
  confidence: string;
  detected_at: string;
  status: string;
};
export type Recommendation = {
  id: string;
  risk_event_id: string | null;
  title: string;
  reason: string;
  evidence: Array<Record<string, unknown>>;
  action: Record<string, unknown> & { type?: string };
  expected_impact: Record<string, unknown>;
  confidence: string;
  priority: string;
  assumptions: string[];
  generated_at: string;
  status: string;
};
export type Recurring = {
  id: string;
  merchant: string;
  amount: string;
  amount_variance_pct: string | null;
  frequency: string;
  next_expected_date: string | null;
  status: "candidate" | "confirmed";
  confirmed_cycles: number;
};
export type DebtSummary = {
  total_debt: string;
  dti: string;
  debt_service_ratio: string;
  credit_utilization: string;
  loans: Array<{
    id: string;
    principal: string;
    interest_rate: string;
    term_months: number;
    monthly_installment: string;
    outstanding_balance: string;
  }>;
  credit_cards: Array<{
    id: string;
    credit_limit: string;
    current_balance: string;
    statement_date: number;
    minimum_due: string;
    apr: string | null;
  }>;
};
export type Simulation = {
  action: Record<string, unknown>;
  baseline: Record<string, unknown>;
  proposed: Record<string, unknown>;
  delta: Record<string, unknown>;
  confidence: Confidence;
  trade_off_note: string;
};
export type Claim = {
  type: "fact" | "prediction" | "recommendation" | "assumption";
  label: string;
  value: unknown;
  source: string;
  confidence?: string | null;
  basis?: string | null;
};
export type ChatResponse = {
  answer_text: string;
  intent: string;
  facts: Claim[];
  predictions: Claim[];
  recommendations: Claim[];
  assumptions: Claim[];
  missing_information: string[];
  provider: string;
  grounded: boolean;
};
export type ChatHistoryMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  structured_answer: ChatResponse | null;
  created_at: string;
};

export function money(value: unknown): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(numeric);
}

export function label(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (part) => part.toUpperCase());
}
