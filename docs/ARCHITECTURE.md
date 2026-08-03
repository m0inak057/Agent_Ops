# Architecture — AgentOps

This document covers the full system architecture: how data flows through an audit, what the folder structure actually contains, what state each MCP server is in, and what the database looks like.

---

## Core Design Principles

**1. The backend is a dispatcher, not a monolith.**
`FastAPI` receives a repo URL, creates an `AuditJob` row, and fires a background task (`backend/services/dispatcher.py`) that runs the pipeline to completion. The backend does not contain agent logic itself — it imports and calls into `agents/` and `evaluation/`.

**2. One LLM call replaces seven.**
`agents/unified_agent.py` sends the repo map to the LLM once, asking it to reason about all 7 audit dimensions (security, code_quality, architecture, performance, testing, devops, documentation) in a single prompt. The 7 individual specialist agent files (`security.py`, `code_quality.py`, etc.) still exist in the codebase but are not called by the dispatcher — see [AGENTS.md](./AGENTS.md).

**3. Confidence validation is rule-based, not LLM-based.**
`evaluation/confidence_pipeline.py` checks evidence quality (detail length, file existence in the repo tree) and adjusts each finding's confidence score. It makes zero LLM calls — this was a deliberate change to cut per-audit cost and latency.

**4. Evaluation is a second, independent LLM call.**
After an audit completes, `evaluation/framework.py` computes deterministic agent/finding/system metrics and makes exactly one more LLM call (`evaluation/metrics/llm_judge.py`) to score overall audit quality. This is the second and last LLM call per audit.

**5. Agents never touch external systems directly.**
`repo_analyzer.py` reaches GitHub only through `github_mcp`, over the MCP stdio protocol. This is the only MCP server actually exercised during an audit today.

---

## System Data Flow

This is the actual 9-step flow implemented in `backend/services/dispatcher.py`:

```
1. FastAPI receives POST /api/audits, validates the GitHub URL,
   creates an AuditJob (status: pending), and fires a background task.
                              │
                              ▼
2. repo_analyzer.py spawns github_mcp over MCP stdio, fetches the
   repo tree and up to 5 key files (requirements.txt/package.json,
   Dockerfile, docker-compose.yml, a CI workflow file, README.md).
                              │
                              ▼
3. unified_agent.py sends the repo_map to the LLM in ONE call
   covering all 7 dimensions at once. Returns 5-15 findings.
                              │
                              ▼
4. confidence_pipeline.py runs RULE-BASED validation only
   (no LLM call) — checks title/detail quality, whether the cited
   file_path exists in the repo tree, and discards or downgrades
   confidence accordingly.
                              │
                              ▼
5. manager.py deduplicates findings by title, sorts by severity
   and confidence, and calculates a 0–100 health score from
   severity-weighted penalties. Pure Python — no LLM call.
                              │
                              ▼
6. All findings + the AgentRun records are written to PostgreSQL.
   AuditJob is marked complete.
                              │
                              ▼
7. notifier.py diffs the new findings against the previous
   completed audit for the same repo_url, and logs new/resolved
   findings.
                              │
                              ▼
8. evaluation/framework.py runs 4 metric groups concurrently
   (agent_metrics, finding_metrics, system_metrics — all
   deterministic — plus llm_judge, one LLM call), and writes each
   scored metric as a row in the evaluations table.
                              │
                              ▼
9. prompt_optimizer.py checks the average agent_success_rate over
   the last 5 completed audits; if it's below 0.80, it drafts and
   benchmarks an improved prompt for the worst-performing agent
   role and promotes it if the benchmark score improves.
```

Every step from 6 onward is wrapped in its own try/except in `dispatcher.py` — a notifier, evaluation, or prompt-optimizer failure never fails the audit itself.

**Total LLM calls per audit: 2** — the unified agent call (step 3) and the audit-quality judge call (step 8).

**LLM provider:** OpenRouter, or any OpenAI-compatible endpoint, configured via `OPENAI_BASE_URL`. Model is set via `AUTOGEN_MODEL`.

---

## Folder Structure — Actual

```
agentops/
│
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── page.tsx                # Landing / submit-audit page
│       │   ├── dashboard/page.tsx      # Health score dashboard
│       │   ├── audits/[id]/page.tsx    # Individual audit viewer
│       │   ├── findings/page.tsx       # All findings
│       │   └── evaluations/page.tsx    # Evaluation history
│       └── components/
│           ├── Navbar.tsx, AuditCard.tsx, FindingCard.tsx
│           ├── SeverityBadge.tsx, StatusBadge.tsx
│           ├── HealthScoreRing.tsx, ConfidenceBar.tsx
│           ├── CategoryScores.tsx, LiveAuditProgress.tsx
│
├── backend/
│   ├── main.py                     # FastAPI app entry point
│   ├── db.py                       # Async SQLAlchemy engine, session factory
│   ├── schemas.py                  # Pydantic request/response models
│   ├── alembic/                    # DB migrations
│   ├── api/
│   │   ├── audits.py                # POST/GET /api/audits
│   │   ├── findings.py              # GET /api/findings/{audit_id} (+ /summary)
│   │   ├── evaluations.py           # GET /api/evaluations/{audit_id}
│   │   ├── fixes.py                 # POST /api/fixes/{finding_id}/approve
│   │   └── webhooks.py              # POST /api/webhooks/github, GET /health
│   ├── models/                     # SQLAlchemy ORM models (one file per table)
│   ├── services/
│   │   ├── dispatcher.py            # Runs the full pipeline for one AuditJob
│   │   ├── evaluator.py             # Thin wrapper used by the evaluations API
│   │   ├── notifier.py              # Diffs findings against the previous audit
│   │   └── prompt_optimizer.py      # Self-improvement loop
│   └── tests/                      # test_api.py, test_manager.py
│
├── agents/
│   ├── unified_agent.py            # ACTIVE — single LLM call, all 7 dimensions
│   ├── repo_analyzer.py            # ACTIVE — fetches repo via github_mcp
│   ├── manager.py                  # ACTIVE — dedup, sort, health score (no LLM)
│   ├── developer.py                # Auto-fix agent — not wired into the pipeline
│   ├── _llm_common.py              # Shared OpenAI-client call/parse helper
│   ├── team.py                     # Legacy grouping of agent references
│   ├── security.py, code_quality.py, architecture.py,
│   │   performance.py, testing.py, devops.py, documentation.py
│   │                               # NOT called by the dispatcher today —
│   │                               # preserved for a future specialist mode
│   ├── prompts/                    # Per-agent system prompt text files
│   └── tools/                      # MCP client connectors
│       ├── github_client.py        # Used by repo_analyzer.py
│       ├── filesystem_client.py, test_client.py, devops_client.py
│
├── mcp_servers/
│   ├── github_mcp/                 # ACTIVE — used on every audit
│   │   ├── server.py
│   │   └── tools/ (clone_repository, get_repository_tree, read_file,
│   │                search_code, create_branch, create_commit,
│   │                create_pull_request)
│   ├── filesystem_mcp/             # Built + running, standby for auto-fix
│   ├── test_mcp/                   # Built + running, standby for auto-fix
│   └── devops_mcp/                 # Built + running, standby for auto-fix
│
├── evaluation/
│   ├── framework.py                 # Orchestrates all metric groups + LLM judge
│   ├── confidence_pipeline.py       # Rule-based finding validation (no LLM)
│   ├── seed_benchmarks.py
│   ├── metrics/
│   │   ├── agent_metrics.py         # success rate, turns, cost, tokens (from DB)
│   │   ├── finding_metrics.py       # avg confidence, severity mix, auto-fix rate
│   │   ├── system_metrics.py        # latency, health score, finding count
│   │   └── llm_judge.py             # 1 LLM call: relevance/depth/coverage/actionability
│   ├── benchmarks/
│   │   └── dataset.json             # Known repos with known_findings
│   └── tests/                       # test_confidence_pipeline.py + conftest.py
│
├── infrastructure/
│   ├── Dockerfile.backend, Dockerfile.frontend
│   ├── Dockerfile.github_mcp, Dockerfile.filesystem_mcp
│   ├── Dockerfile.test_mcp, Dockerfile.devops_mcp
│
├── .github/
│   └── workflows/
│       ├── ci.yml                  # Lint (flake8+black), pytest, Docker builds, frontend build
│       └── eval_gate.yml           # Runs check_threshold.py as a quality gate
│
├── check_threshold.py              # Reads Evaluations table, fails CI if below threshold
├── docker-compose.yml
└── .env.example
```

---

## MCP Server Status

| Server | Status | Used By |
|---|---|---|
| `github_mcp` | **Active** | `repo_analyzer.py` on every audit — fetches repo tree and key files over MCP stdio |
| `filesystem_mcp` | Built, running in Docker Compose | Standby — reserved for the auto-fix pipeline |
| `test_mcp` | Built, running in Docker Compose | Standby — reserved for the auto-fix pipeline |
| `devops_mcp` | Built, running in Docker Compose | Standby — reserved for the auto-fix pipeline |

All four servers pass their own `/health` checks in `docker-compose.yml`. Only `github_mcp` is imported and called from the audit dispatch path (`backend/services/dispatcher.py` → `agents/repo_analyzer.py` → `agents/tools/github_client.py`).

---

## PostgreSQL Database Schema

### audit_jobs

| Column | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| repo_url | TEXT | Target GitHub repository URL |
| repo_name | TEXT | Nullable |
| status | ENUM | pending / analyzing / complete / failed |
| health_score | INT | Nullable until complete |
| created_at | TIMESTAMP | |
| completed_at | TIMESTAMP | Nullable |

### findings

| Column | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| audit_id | UUID | FK → audit_jobs |
| agent_role | TEXT | Which agent/category produced this (unified agent tags by category) |
| category | ENUM | security / code_quality / architecture / performance / testing / devops / documentation |
| severity | ENUM | critical / high / medium / low |
| title | TEXT | |
| detail | TEXT | Full explanation with evidence |
| file_path | TEXT | Nullable |
| line_number | INT | Nullable |
| confidence | FLOAT | 0.0 – 1.0 |
| auto_fix_available | BOOLEAN | Forced false by the confidence pipeline below 0.95 |
| fix_status | ENUM | none / suggested / approved / pr_created / merged |
| pr_url | TEXT | Nullable |
| created_at | TIMESTAMP | |

### agent_runs

| Column | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| audit_id | UUID | FK → audit_jobs |
| agent_role | TEXT | `repo_analyzer` or `unified` |
| tokens_used | INT | Always 0 today — not yet instrumented |
| cost_usd | FLOAT | Always 0 today — not yet instrumented |
| turns | INT | Always 0 today (no multi-turn loop) |
| findings_produced | INT | |
| status | ENUM | running / success / failed / retried |
| started_at | TIMESTAMP | |
| ended_at | TIMESTAMP | Nullable |

### tool_executions

| Column | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| run_id | UUID | FK → agent_runs |
| mcp_server | TEXT | e.g. github_mcp |
| tool_name | TEXT | e.g. read_file |
| input_args | JSON | Nullable |
| output | JSON | Nullable |
| status | ENUM | success / failed / timeout |
| latency_ms | INT | Nullable |
| called_at | TIMESTAMP | |

### evaluations

| Column | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| audit_id | UUID | FK → audit_jobs |
| metric | TEXT | e.g. agent_success_rate, average_confidence, audit_quality_finding_relevance |
| score | FLOAT | |
| feedback | TEXT | Nullable — LLM judge reasoning, or a human-readable note for deterministic metrics |
| evaluated_at | TIMESTAMP | |

### prompt_variations

| Column | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| agent_role | TEXT | Which agent role this prompt is for |
| prompt_text | TEXT | Full system prompt |
| avg_score | FLOAT | Nullable |
| is_active | BOOLEAN | Currently deployed prompt |
| created_at | TIMESTAMP | |
| promoted_at | TIMESTAMP | Nullable |

---

## API Endpoints (all implemented)

| Endpoint | Purpose |
|---|---|
| `POST /api/audits` | Submit a repo URL, creates an AuditJob and dispatches the background task |
| `GET /api/audits` | List all audits |
| `GET /api/audits/{id}` | Get a single audit's details |
| `GET /api/findings/{audit_id}` | List findings for an audit |
| `GET /api/findings/{audit_id}/summary` | Severity counts for an audit |
| `GET /api/evaluations/{audit_id}` | Evaluation metric rows for an audit |
| `POST /api/fixes/{finding_id}/approve` | Approve a `confidence >= 0.95` finding's auto-fix — queues a background task that currently only logs (see [ROADMAP.md](./ROADMAP.md)) |
| `POST /api/webhooks/github` | GitHub push webhook — verifies HMAC signature, triggers a re-audit for pushes to main/master |
| `GET /api/webhooks/health` | Webhook endpoint health check |
| `GET /health` | Backend health check |

---

## Docker Services

| Service | Port | Status |
|---|---|---|
| `agentops_backend` | 8000 | FastAPI |
| `agentops_db` | 5432 | PostgreSQL 15 |
| `agentops_redis` | 6380→6379 | Built, standby (not read from anywhere yet) |
| `agentops_frontend` | 3000 | Next.js dashboard |
| `agentops_github_mcp` | 8001 | Active in the audit pipeline |
| `agentops_filesystem_mcp` | 8002 | Running, standby |
| `agentops_test_mcp` | 8003 | Running, standby |
| `agentops_devops_mcp` | 8004 | Running, standby |
