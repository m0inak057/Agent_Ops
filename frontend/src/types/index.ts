// TypeScript interfaces matching the AgentOps FastAPI backend schemas

export type AuditStatus = "pending" | "analyzing" | "complete" | "failed";

export type FindingSeverity = "critical" | "high" | "medium" | "low";

export type FindingCategory =
  | "security"
  | "code_quality"
  | "architecture"
  | "performance"
  | "testing"
  | "devops"
  | "documentation";

export type FindingFixStatus =
  | "none"
  | "suggested"
  | "approved"
  | "pr_created"
  | "merged";

export interface AuditJob {
  id: string;
  repo_url: string;
  repo_name: string | null;
  status: AuditStatus;
  health_score: number | null;
  created_at: string;
  completed_at: string | null;
}

export interface AuditJobCreateResponse {
  audit_id: string;
  status: AuditStatus;
  repo_url: string;
  repo_name: string | null;
}

export interface Finding {
  id: string;
  audit_id: string;
  agent_role: string;
  category: FindingCategory;
  severity: FindingSeverity;
  title: string;
  detail: string;
  file_path: string | null;
  line_number: number | null;
  confidence: number;
  auto_fix_available: boolean;
  fix_status: FindingFixStatus;
  pr_url: string | null;
  created_at: string;
}

export interface FindingSummary {
  critical: number;
  high: number;
  medium: number;
  low: number;
  by_category: Record<string, number>;
}

export interface Evaluation {
  id: string;
  audit_id: string;
  metric: string;
  score: number;
  feedback: string | null;
  evaluated_at: string;
}

export interface FixApproveResponse {
  finding_id: string;
  fix_status: FindingFixStatus;
  message: string;
}

export interface HealthCheckResponse {
  status: string;
  db: string;
  version: string;
}
