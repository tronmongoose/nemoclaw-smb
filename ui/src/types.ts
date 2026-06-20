/** API shape definitions for NemoClaw SMB Ops Agent dashboard. */

export interface HealthResponse {
  status: string;
  service: string;
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  category: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  amount: number;
  date: string;
  category: string;
  anomaly_flag: boolean;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface Invoice {
  invoice_id: string;
  vendor: string;
  description: string;
  amount: number;
  date: string;
  category: string;
}

export interface AnomalyRecord {
  vendor: string;
  current_amount: number;
  baseline_mean: number;
  z_score: number;
  pct_change: number;
  is_anomaly: boolean;
  reason: string;
}

export interface ApprovalContext {
  invoice_id?: string;
  threshold?: number;
  policy_reason?: string;
  anomaly_reason?: string;
}

export interface ApprovalItem {
  id: string;
  action: string;
  vendor: string;
  amount: number;
  context: ApprovalContext;
  created_at: string;
  expires_at: string;
  status: string;
}

export interface ApprovalDecideBody {
  approved: boolean;
  decided_by: string;
}

export interface SavingsSummary {
  total_spend: number;
  monthly_savings: number;
  annual_savings: number;
  nemoclaw_fee: number;
  fee_rate: number;
  currency: string;
}

export interface VendorAlternative {
  vendor: string;
  amount: number;
  monthly_savings: number;
  annual_savings: number;
  rank: number;
}

export interface AlternativesResponse {
  current: { vendor: string; amount: number };
  ranked: VendorAlternative[];
}

export interface AuditVerify {
  ok: boolean;
  message: string;
}

export interface AuditEntry {
  [key: string]: unknown;
}

export interface AuditResponse {
  count: number;
  entries: AuditEntry[];
  verify: AuditVerify;
}

// --- Tenant Dashboard ---

export interface AnalysisTotals {
  income: number;
  expense: number;
  net: number;
  margin_pct: number;
}

export interface AnalysisByMonth {
  month: string;
  income: number;
  expense: number;
  net: number;
}

export interface AnalysisByCategory {
  category: string;
  amount: number;
}

export interface AnalysisFinding {
  title: string;
  category: string;
  monthly_impact: number;
  annual_impact: number;
  confidence: "high" | "medium" | "low";
  why: string;
}

export interface AnalysisPnl {
  totals: AnalysisTotals;
  by_month: AnalysisByMonth[];
  expense_by_category: AnalysisByCategory[];
}

export interface TenantAnalysis {
  tenant: string;
  generated_at: string;
  pnl: AnalysisPnl;
  findings: AnalysisFinding[];
}
