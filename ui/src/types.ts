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
  action: string;
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

// v2 additions

export interface HeadlineSeries {
  month: string;
  value: number;
}

export interface AnalysisHeadline {
  title: string;
  action: string;
  annual_impact: number;
  monthly_impact: number;
  severity: string;
  category: string;
  series: HeadlineSeries[];
}

export interface LongitudinalNetMonth {
  month: string;
  net: number;
}

export interface LongitudinalCategoryMonth {
  month: string;
  value: number;
}

export interface LongitudinalCategory {
  category: string;
  series: LongitudinalCategoryMonth[];
}

export interface AnalysisLongitudinal {
  net_by_month: LongitudinalNetMonth[];
  by_category_monthly: LongitudinalCategory[];
}

export interface TenantAnalysis {
  tenant: string;
  generated_at: string;
  pnl: AnalysisPnl;
  headlines: AnalysisHeadline[];
  findings: AnalysisFinding[];
  longitudinal: AnalysisLongitudinal;
}

// --- STR three-act web view ---

/** Reasoning provenance attached to every model-backed STR result.
 * mode demo => deterministic cached trace; mode live => real Nemotron call. */
export interface ReasoningProvenance {
  mode: "demo" | "live";
  model: string;
  latency_ms: number;
  source: "nemotron" | "cached" | "hermes";
}

// Turnover coordination: the loop, the stall queue, and the Hermes nudge

export interface StrTurnoverStageRow {
  stage: string;
  role: string;
  status: "done" | "in_progress" | "waiting" | "blocked";
  actor: string;
  hours_in_stage: number;
}

export interface StrTurnoverEvent {
  property_id: string;
  property_name: string;
  current_stage: string;
  overall_status: "ready" | "in_progress" | "stalled";
  stages: StrTurnoverStageRow[];
}

export interface StrTurnoverResponse {
  properties: StrTurnoverEvent[];
}

export interface StrCoordinationNudge {
  stalled_actor: string;
  nudge_message: string;
  next_action: string;
  reasoning_provenance: ReasoningProvenance;
}

export interface StrStalledHandoff {
  handoff_id: string;
  property_id: string;
  property_name: string;
  stage: string;
  from_actor: string;
  to_actor: string;
  assigned_to: string;
  reason: string;
  hours_stalled: number;
  nudge: StrCoordinationNudge;
  reasoning_provenance: ReasoningProvenance;
}

export interface StrStallQueueResponse {
  count: number;
  stalls: StrStalledHandoff[];
}

// Performance flagging (Hermes "why")

export interface StrPerformanceAnalysis {
  verdict: "over" | "under" | "on_track";
  summary: string;
  drivers: string[];
  reasoning_provenance: ReasoningProvenance;
}

export interface StrPropertyPerformance {
  property_id: string;
  property_name: string;
  revenue_cents: number;
  portfolio_avg_cents: number;
  pct_vs_avg: number;
  status: "over" | "under" | "on_track";
  occupancy: number;
  analysis: StrPerformanceAnalysis;
  reasoning_provenance: ReasoningProvenance;
}

export interface StrPerformanceResponse {
  count: number;
  properties: StrPropertyPerformance[];
}

// Cleaner scheduling (Hermes reassign + card pre-auth)

export interface StrCleanerCandidate {
  id: string;
  name: string;
  free_from: string | null;
  available: boolean;
}

export interface StrCleanerScheduleDraft {
  suggested_cleaner: string;
  scheduled_start: string;
  reason: string;
  card_action: string;
  reasoning_provenance: ReasoningProvenance;
}

export interface StrCleanerStall {
  handoff_id: string;
  property_id: string;
  property_name: string;
  stage: string;
  assigned_to: string;
  hours_stalled: number;
  reason: string;
  assigned_cleaner: StrCleanerCandidate | null;
  suggested_cleaner: StrCleanerCandidate | null;
  crew_availability: StrCleanerCandidate[];
  schedule: StrCleanerScheduleDraft;
  reasoning_provenance: ReasoningProvenance;
}

export interface StrSchedulingResponse {
  count: number;
  stalls: StrCleanerStall[];
}

export interface StrSchedulingAssignResult {
  ok: boolean;
  reason?: string;
  handoff_id?: string;
  cleaner?: string;
  card_token?: string;
  schedule?: StrCleanerScheduleDraft;
}

// Act I: owner-fee reconciliation

export interface StrLedgerSummary {
  property_id: string;
  month: string;
  revenue_cents: number;
  contract_pct: number;
  charged_pct: number;
  line_items: {
    contracted_fee_cents?: number;
    charged_fee_cents?: number;
    fee_delta_cents?: number;
  };
}

export interface StrAnomalyResult {
  is_anomaly: boolean;
  expected_fee_cents: number;
  charged_fee_cents: number;
  overcharge_cents: number;
  reason: string;
  model_used: string;
  reasoning_trace: string;
  reasoning_provenance: ReasoningProvenance;
}

export interface StrPaymentResult {
  payment_id: string;
  amount_cents: number;
  status: string;
  audit_hash: string;
  held_for_approval: boolean;
  request_id: string;
}

export interface StrReconciliationReport {
  property_id: string;
  month: string;
  summary: StrLedgerSummary;
  anomaly: StrAnomalyResult;
  payment: StrPaymentResult | null;
  audit_ok: boolean;
  audit_detail: string;
  nhi_id: string;
}

// Act II: property-management orchestration

export interface StrCleanerCard {
  card_token: string;
  card_id: string;
  job_id: string;
  property_id: string;
  cleaner_id: string;
  amount_cap_cents: number;
  mcc_list: string[];
  expiry_utc: string;
  backend: string;
}

export interface StrPayoutRecord {
  crew_id: string;
  crew_name: string;
  amount_cents: number;
  month: string;
  transfer_id: string;
  status: string;
  backend: string;
}

export interface StrPayoutBatch {
  month: string;
  records: StrPayoutRecord[];
  total_cents: number;
}

export interface StrInvoiceLine {
  property_id: string;
  property_name: string;
  revenue_cents: number;
  fee_pct: number;
  fee_cents: number;
  description: string;
}

export interface StrOwnerInvoice {
  owner_id: string;
  month: string;
  invoice_id: string;
  line_items: StrInvoiceLine[];
  total_revenue_cents: number;
  total_fee_cents: number;
  backend: string;
}

export interface StrInvoicesResponse {
  month: string;
  invoices: StrOwnerInvoice[];
}

export interface StrPortfolioSummary {
  property_count: number;
  owner_count: number;
  total_monthly_revenue_cents: number;
  property_ids: string[];
  owner_ids: string[];
  properties_by_owner: Record<string, string[]>;
}

// Act III: platform earn server

export interface StrEarnEvent {
  chain_hash: string;
  seq: number;
  timestamp: string;
}

export interface StrPricingRecommendation {
  recommended_rate: number;
  confidence: string;
  reasoning: string;
  suggested_title_tweak: string;
  valid_for_hours: number;
  reasoning_provenance: ReasoningProvenance;
}

export interface StrPriceResponse {
  service: string;
  property_id: string;
  amount_cents: number;
  recommendation: StrPricingRecommendation;
  earn_event: StrEarnEvent;
  c1_authorized: boolean;
}

export interface StrDimensionScores {
  structure_completeness: number;
  agent_parseability: number;
  description_quality: number;
  conflict_free: number;
}

export interface StrAeoResult {
  overall_score: number;
  dimension_scores: StrDimensionScores;
  optimized_opening: string;
  reasoning_trace: string;
  reasoning_provenance: ReasoningProvenance;
}

export interface StrAeoResponse {
  service: string;
  amount_cents: number;
  result: StrAeoResult;
  earn_event: StrEarnEvent;
  c1_authorized: boolean;
}

export interface StrGuestCommsResult {
  intent: string;
  message: string;
  upsell: string;
  reasoning_provenance: ReasoningProvenance;
}

export interface StrGuestCommsResponse {
  service: string;
  amount_cents: number;
  result: StrGuestCommsResult;
  earn_event: StrEarnEvent;
  c1_authorized: boolean;
}

/** The 402 body returned by /str/act3/aeo-audit when no MPP token is presented. */
export interface StrPaymentRequired {
  error: string;
  amount_cents: number;
}

export interface StrMetrics {
  calls_served: number;
  revenue_earned_cents: number;
  revenue_earned_dollars: number;
  properties_optimized: number;
  property_ids: string[];
}

// Audit

export interface StrAuditEntry {
  ts?: string;
  seq?: number;
  event?: string;
  service?: string;
  amount_cents?: number;
  token_id?: string;
  action?: string;
  vendor?: string;
  actor?: string;
  decision?: string;
  prev_hash?: string;
  entry_hash?: string;
  [key: string]: unknown;
}

export interface StrAuditResponse {
  count: number;
  entries: StrAuditEntry[];
  verify: AuditVerify;
}

// Integrations / sponsor stack graph

export type IntegrationStatusKind =
  | "REAL"
  | "LIVE-CAPABLE"
  | "LIVE-OK"
  | "LIVE-FAIL"
  | "DEMO"
  | "NOT-CONFIGURED";

/** One node in the sponsor stack graph: the agent core or a sponsor pillar. */
export interface IntegrationNode {
  id: string;
  label: string;
  vendor?: string;
  kind: string; // core | reasoning | orchestration | payments | governance
  status: IntegrationStatusKind;
  detail: string;
  source?: string;
  skills?: string[];
}

export interface IntegrationStatusResponse {
  agent: IntegrationNode;
  pillars: IntegrationNode[];
}

export interface IntegrationVerify {
  id: string;
  status: IntegrationStatusKind;
  detail: string;
  latency_ms: number;
}

// Sponsor interactions feed (live + historical) -- GET /str/interactions

export type StrSegment = "owner" | "firm" | "agent";

/** The four top-nav destinations: the three portals plus the cross-cutting tech layer. */
export type PortalView = StrSegment | "stack";

/** One logged sponsor interaction (a model call or a Stripe/payment op). */
export interface StrInteraction {
  ts?: string;
  seq?: number;
  sponsor: string; // "Nous Research" | "NVIDIA" | "Stripe" | "C1"
  op: string;
  segment?: string;
  status?: string; // "ok" | "cached" | "fallback" | "fail"
  model?: string | null;
  latency_ms?: number | null;
  mode?: string | null; // "live" | "demo"
  metadata?: Record<string, unknown>;
  entry_hash?: string;
}

export interface StrInteractionsResponse {
  count: number;
  entries: StrInteraction[];
  verify: AuditVerify;
}
