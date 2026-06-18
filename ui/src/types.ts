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

export interface ApprovalItem {
  id: string;
  action: string;
  vendor: string;
  amount: number;
  context: string;
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
