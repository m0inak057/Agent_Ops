import {
  AuditJob,
  AuditJobCreateResponse,
  Finding,
  FindingSummary,
  Evaluation,
  FixApproveResponse,
  HealthCheckResponse,
  FindingSeverity,
  FindingCategory,
  AuditStatus,
} from "@/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Audits ──────────────────────────────────────────────────────────────────

export async function createAudit(repoUrl: string): Promise<AuditJobCreateResponse> {
  return apiFetch("/api/audits", {
    method: "POST",
    body: JSON.stringify({ repo_url: repoUrl }),
  });
}

export async function listAudits(status?: AuditStatus): Promise<AuditJob[]> {
  const qs = status ? `?status=${status}` : "";
  return apiFetch(`/api/audits${qs}`);
}

export async function getAudit(auditId: string): Promise<AuditJob> {
  return apiFetch(`/api/audits/${auditId}`);
}

export async function listAuditsForRepo(repoName: string): Promise<AuditJob[]> {
  return apiFetch(`/api/audits?repo_name=${encodeURIComponent(repoName)}`);
}

// ── Timeline ─────────────────────────────────────────────────────────────────

export interface AuditSpan {
  id: string;
  span_name: string;
  status: "running" | "success" | "failed" | "skipped";
  started_at: string;
  ended_at: string | null;
  duration_ms: number | null;
  input_summary: string | null;
  output_summary: string | null;
  error: string | null;
  metadata: Record<string, unknown> | null;
}

export interface AuditTimeline {
  audit_id: string;
  repo_name: string;
  status: string;
  total_duration_ms: number;
  spans: AuditSpan[];
}

export async function getAuditTimeline(auditId: string): Promise<AuditTimeline> {
  return apiFetch<AuditTimeline>(`/api/audits/${auditId}/timeline`);
}

// ── Findings ─────────────────────────────────────────────────────────────────

export async function listFindings(
  auditId: string,
  filters?: { severity?: FindingSeverity; category?: FindingCategory }
): Promise<Finding[]> {
  const params = new URLSearchParams();
  if (filters?.severity) params.set("severity", filters.severity);
  if (filters?.category) params.set("category", filters.category);
  const qs = params.toString() ? `?${params}` : "";
  return apiFetch(`/api/findings/${auditId}${qs}`);
}

export async function findingsSummary(auditId: string): Promise<FindingSummary> {
  return apiFetch(`/api/findings/${auditId}/summary`);
}

// ── Evaluations ──────────────────────────────────────────────────────────────

export async function listEvaluations(auditId: string): Promise<Evaluation[]> {
  return apiFetch(`/api/evaluations/${auditId}`);
}

// ── Fixes ────────────────────────────────────────────────────────────────────

export async function approveFix(findingId: string): Promise<FixApproveResponse> {
  return apiFetch(`/api/fixes/${findingId}/approve`, { method: "POST" });
}

// ── Health ───────────────────────────────────────────────────────────────────

export async function healthCheck(): Promise<HealthCheckResponse> {
  return apiFetch("/health");
}

// ── Mock Data (fallback when backend is unavailable) ─────────────────────────

export const MOCK_AUDITS: AuditJob[] = [
  {
    id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    repo_url: "https://github.com/example/django-ecommerce",
    repo_name: "example/django-ecommerce",
    status: "complete",
    health_score: 71,
    created_at: new Date(Date.now() - 3600000).toISOString(),
    completed_at: new Date(Date.now() - 3000000).toISOString(),
  },
  {
    id: "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    repo_url: "https://github.com/example/fastapi-starter",
    repo_name: "example/fastapi-starter",
    status: "complete",
    health_score: 88,
    created_at: new Date(Date.now() - 7200000).toISOString(),
    completed_at: new Date(Date.now() - 6000000).toISOString(),
  },
  {
    id: "c3d4e5f6-a7b8-9012-cdef-123456789012",
    repo_url: "https://github.com/example/node-api",
    repo_name: "example/node-api",
    status: "analyzing",
    health_score: null,
    created_at: new Date(Date.now() - 120000).toISOString(),
    completed_at: null,
  },
  {
    id: "d4e5f6a7-b8c9-0123-defa-234567890123",
    repo_url: "https://github.com/example/react-dashboard",
    repo_name: "example/react-dashboard",
    status: "complete",
    health_score: 54,
    created_at: new Date(Date.now() - 86400000).toISOString(),
    completed_at: new Date(Date.now() - 85000000).toISOString(),
  },
];

export const MOCK_FINDINGS: Finding[] = [
  {
    id: "f1a2b3c4-d5e6-7890-abcd-ef1234567890",
    audit_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    agent_role: "security",
    category: "security",
    severity: "critical",
    title: "JWT secret hardcoded in source code",
    detail:
      "Found hardcoded JWT secret 'super_secret_key_123' in users/auth.py line 42. This exposes session tokens and allows attackers to forge authentication tokens. Replace with an environment variable and rotate immediately.",
    file_path: "users/auth.py",
    line_number: 42,
    confidence: 0.99,
    auto_fix_available: true,
    fix_status: "none",
    pr_url: null,
    created_at: new Date(Date.now() - 2900000).toISOString(),
  },
  {
    id: "f2b3c4d5-e6f7-8901-bcde-f12345678901",
    audit_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    agent_role: "security",
    category: "security",
    severity: "critical",
    title: "SQL injection risk in search endpoint",
    detail:
      "Raw string interpolation used in search/views.py:87 `query = f\"SELECT * FROM products WHERE name LIKE '%{search_term}%'\"`. This is directly exploitable. Use parameterized queries instead.",
    file_path: "search/views.py",
    line_number: 87,
    confidence: 0.94,
    auto_fix_available: false,
    fix_status: "none",
    pr_url: null,
    created_at: new Date(Date.now() - 2900000).toISOString(),
  },
  {
    id: "f3c4d5e6-f7a8-9012-cdef-123456789012",
    audit_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    agent_role: "performance",
    category: "performance",
    severity: "high",
    title: "N+1 query on every orders request",
    detail:
      "orders/views.py:34 fetches all orders then iterates, making one DB query per order to fetch the user. Use select_related('user') to resolve in a single JOIN query. Impacts every /api/orders/ call.",
    file_path: "orders/views.py",
    line_number: 34,
    confidence: 0.96,
    auto_fix_available: true,
    fix_status: "none",
    pr_url: null,
    created_at: new Date(Date.now() - 2900000).toISOString(),
  },
  {
    id: "f4d5e6f7-a8b9-0123-defa-234567890123",
    audit_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    agent_role: "devops",
    category: "devops",
    severity: "high",
    title: "Docker container running as root",
    detail:
      "Dockerfile has no USER directive, meaning the application runs as root inside the container. A container escape would give the attacker root access. Add USER appuser and create a non-root user.",
    file_path: "Dockerfile",
    line_number: null,
    confidence: 0.98,
    auto_fix_available: true,
    fix_status: "none",
    pr_url: null,
    created_at: new Date(Date.now() - 2900000).toISOString(),
  },
  {
    id: "f5e6f7a8-b9c0-1234-efab-345678901234",
    audit_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    agent_role: "testing",
    category: "testing",
    severity: "high",
    title: "Payment processing has 0% test coverage",
    detail:
      "payments/ module handles all financial transactions but has no test files. Critical path with no safety net. Add unit tests for charge_card(), refund(), and webhook_handler() at minimum.",
    file_path: "payments/",
    line_number: null,
    confidence: 0.91,
    auto_fix_available: false,
    fix_status: "none",
    pr_url: null,
    created_at: new Date(Date.now() - 2900000).toISOString(),
  },
  {
    id: "f6f7a8b9-c0d1-2345-fabc-456789012345",
    audit_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    agent_role: "code_quality",
    category: "code_quality",
    severity: "medium",
    title: "Cyclomatic complexity 18 in checkout.py",
    detail:
      "checkout/views.py:process_order() has cyclomatic complexity of 18, far above the recommended max of 10. Split into separate functions for validation, payment, inventory, and notification.",
    file_path: "checkout/views.py",
    line_number: 12,
    confidence: 0.87,
    auto_fix_available: false,
    fix_status: "none",
    pr_url: null,
    created_at: new Date(Date.now() - 2900000).toISOString(),
  },
  {
    id: "f7a8b9c0-d1e2-3456-abcd-567890123456",
    audit_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    agent_role: "devops",
    category: "devops",
    severity: "medium",
    title: "No CI/CD pipeline configured",
    detail:
      "No .github/workflows/ directory found. Deployments are likely manual. Add a GitHub Actions workflow with at minimum: linting, test execution, and Docker build validation on every pull request.",
    file_path: null,
    line_number: null,
    confidence: 0.82,
    auto_fix_available: false,
    fix_status: "none",
    pr_url: null,
    created_at: new Date(Date.now() - 2900000).toISOString(),
  },
  {
    id: "f8b9c0d1-e2f3-4567-bcde-678901234567",
    audit_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    agent_role: "documentation",
    category: "documentation",
    severity: "low",
    title: "API endpoints undocumented",
    detail:
      "No OpenAPI schema annotations or docstrings on any API endpoint. FastAPI can auto-generate docs with proper type hints and docstrings. Add response_model and descriptions to all routers.",
    file_path: null,
    line_number: null,
    confidence: 0.78,
    auto_fix_available: false,
    fix_status: "none",
    pr_url: null,
    created_at: new Date(Date.now() - 2900000).toISOString(),
  },
];

export const MOCK_EVALUATIONS: Evaluation[] = [
  { id: "e1", audit_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890", metric: "agent_success_rate", score: 0.857, feedback: "6 out of 7 agents completed successfully", evaluated_at: new Date(Date.now() - 2800000).toISOString() },
  { id: "e2", audit_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890", metric: "average_confidence", score: 0.893, feedback: null, evaluated_at: new Date(Date.now() - 2800000).toISOString() },
  { id: "e3", audit_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890", metric: "audit_quality_finding_relevance", score: 0.921, feedback: "LLM judge rated findings as highly relevant and specific", evaluated_at: new Date(Date.now() - 2800000).toISOString() },
  { id: "e4", audit_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890", metric: "false_positive_rate", score: 0.062, feedback: null, evaluated_at: new Date(Date.now() - 2800000).toISOString() },
];
