# Architecture — AgentOps

This document covers the full system architecture: how data flows, how agents are isolated, how MCP servers are structured, and what the database looks like.

---

## Core Design Principles

**1. Agents never touch external systems directly.**
Every agent action goes through an MCP server. This creates a controlled, auditable boundary between thinking (AutoGen) and doing (MCP tools).

**2. Every finding has a confidence score.**
The evaluation pipeline validates every agent finding before it reaches the user. Findings below 85% confidence are shown with evidence only. Auto-fixes are only allowed above 95% confidence.

**3. The backend is an event dispatcher, not a monolith.**
FastAPI receives a repo URL, emits an event, and the AutoGen team picks it up. The backend does not contain agent logic.

**4. Evaluation is a first-class citizen.**
Every agent run produces structured evaluation data. The CI/CD pipeline consumes this data. The self-improvement loop reads it. The dashboard visualises it.

**5. Static analysis tools are integrated, not replaced.**
The Security Agent runs Bandit, Semgrep, and Trivy. The LLM interprets and contextualises the results. It does not try to replace these tools with pure LLM judgment.

---

## System Data Flow

```
┌─────────────────────────────────────────────────────────┐
│                  User / GitHub Webhook                   │
│           (pastes repo URL or commit triggers audit)     │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Backend                        │
│  - Receives repo URL                                     │
│  - Writes to PostgreSQL (AuditJobs table)                │
│  - Dispatches event to AutoGen team                      │
│  - Exposes REST + WebSocket API for frontend             │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│               AutoGen Multi-Agent Team                   │
│                                                          │
│  Manager ──► Repository Analyzer                         │
│                      │                                   │
│       ┌──────────────┼──────────────┐                   │
│       │              │              │                    │
│  Code Quality    Security      Architecture              │
│  Agent           Agent         Agent                     │
│       │              │              │                    │
│  Performance    Testing        DevOps                    │
│  Agent          Agent          Agent                     │
│       │              │              │                    │
│  Documentation Agent                                     │
│       │                                                  │
│  Manager synthesises all findings                        │
│       │                                                  │
│  Evaluation Pipeline (confidence scoring)                │
│       │                                                  │
│  [Optional] Developer Agent → auto-fix → PR              │
└───────────────────────────┬─────────────────────────────┘
                            │
              ┌─────────────┼──────────────┐
              │             │              │
              ▼             ▼              ▼
        github_mcp   filesystem_mcp   test_mcp
              │                           │
              ▼                           ▼
         GitHub API               Pytest/Bandit/
                                  Semgrep/Trivy
                            │
                            ▼
                       devops_mcp
                            │
                            ▼
                   Docker / CI inspection
```

---

## Folder Structure — Detailed

```
agentops/
│
├── frontend/
│   ├── app/
│   │   ├── dashboard/              # Main health score dashboard
│   │   ├── audits/                 # Individual audit viewer (finding by finding)
│   │   ├── findings/               # All findings across all audits
│   │   └── evaluations/            # Agent evaluation history and trends
│   ├── components/                 # Shadcn UI components
│   └── lib/                        # API client, WebSocket hooks
│
├── backend/
│   ├── main.py                     # FastAPI app entry point
│   ├── api/
│   │   ├── audits.py               # POST /audits — submit repo URL
│   │   ├── findings.py             # GET /findings — audit findings
│   │   ├── evaluations.py          # GET /evaluations — agent scores
│   │   └── fixes.py                # POST /fixes — trigger auto-fix
│   ├── models/
│   │   ├── audit_job.py            # AuditJob model
│   │   ├── agent_run.py            # AgentRun model
│   │   ├── finding.py              # Finding model
│   │   ├── tool_execution.py       # ToolExecution model
│   │   ├── evaluation.py           # Evaluation model
│   │   └── prompt_variation.py     # PromptVariation model
│   ├── services/
│   │   ├── dispatcher.py           # Emits events to AutoGen
│   │   ├── evaluator.py            # Runs confidence scoring pipeline
│   │   └── prompt_optimizer.py     # Self-improvement loop
│   └── db.py                       # PostgreSQL connection, session factory
│
├── agents/
│   ├── team.py                     # AutoGen GroupChat configuration
│   ├── manager.py                  # Manager + synthesis agent
│   ├── repo_analyzer.py            # Repository understanding agent
│   ├── code_quality.py             # Code Quality agent
│   ├── security.py                 # Security agent
│   ├── architecture.py             # Architecture agent
│   ├── performance.py              # Performance agent
│   ├── testing.py                  # Testing agent
│   ├── devops.py                   # DevOps agent
│   ├── documentation.py            # Documentation agent
│   ├── developer.py                # Developer agent (auto-fix only)
│   ├── prompts/
│   │   ├── manager.txt
│   │   ├── repo_analyzer.txt
│   │   ├── code_quality.txt
│   │   ├── security.txt
│   │   ├── architecture.txt
│   │   ├── performance.txt
│   │   ├── testing.txt
│   │   ├── devops.txt
│   │   ├── documentation.txt
│   │   └── developer.txt
│   └── tools/
│       ├── github_client.py
│       ├── filesystem_client.py
│       ├── test_client.py
│       └── devops_client.py
│
├── mcp_servers/
│   ├── github_mcp/
│   │   ├── server.py
│   │   └── tools/
│   │       ├── clone_repository.py
│   │       ├── get_repository_tree.py
│   │       ├── read_file.py
│   │       ├── search_code.py
│   │       ├── create_branch.py
│   │       ├── create_commit.py
│   │       └── create_pull_request.py
│   ├── filesystem_mcp/
│   │   ├── server.py
│   │   └── tools/
│   │       ├── read_file.py
│   │       ├── write_file.py
│   │       ├── list_directory.py
│   │       └── search_files.py
│   ├── test_mcp/
│   │   ├── server.py
│   │   └── tools/
│   │       ├── run_tests.py
│   │       ├── run_coverage.py
│   │       ├── run_linter.py
│   │       ├── run_bandit.py
│   │       ├── run_semgrep.py
│   │       └── run_trivy.py
│   └── devops_mcp/
│       ├── server.py
│       └── tools/
│           ├── inspect_dockerfile.py
│           ├── inspect_docker_compose.py
│           ├── inspect_ci_pipeline.py
│           ├── check_env_files.py
│           └── get_dependency_vulnerabilities.py
│
├── evaluation/
│   ├── framework.py
│   ├── confidence_pipeline.py      # Validates agent findings
│   ├── metrics/
│   │   ├── finding_metrics.py      # Finding accuracy, false positive rate
│   │   ├── agent_metrics.py        # Tool accuracy, turn count, retries
│   │   ├── llm_judge.py            # LLM-as-a-Judge scoring
│   │   └── system_metrics.py       # Latency, token cost, failure rate
│   └── benchmarks/
│       └── dataset.json            # Known repos with known issues
│
├── infrastructure/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   ├── Dockerfile.github_mcp
│   ├── Dockerfile.filesystem_mcp
│   ├── Dockerfile.test_mcp
│   └── Dockerfile.devops_mcp
│
├── .github/
│   └── workflows/
│       ├── ci.yml                  # Lint, test, Docker build
│       └── eval_gate.yml           # AI evaluation quality gate
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## MCP Server Design

Each MCP server is a completely isolated Python process. Agents communicate with them via the Python MCP SDK — they cannot call arbitrary shell commands or access systems outside what the MCP server explicitly exposes.

### Why This Matters

```
# Without MCP (dangerous)
agent.run("git clone https://github.com/... && cat secrets.env")

# With MCP (controlled)
agent.call_tool("github_mcp", "read_file", {
    "repo": "org/repo",
    "path": "users/auth.py"
})
# The MCP server validates the path, enforces read-only access, logs the call
```

### Tool Permissions Per Agent

| Agent | github_mcp | filesystem_mcp | test_mcp | devops_mcp |
|---|---|---|---|---|
| Repository Analyzer | Read | ✗ | ✗ | ✗ |
| Code Quality Agent | Read | ✗ | Lint only | ✗ |
| Security Agent | Read | ✗ | Bandit/Semgrep/Trivy | ✗ |
| Architecture Agent | Read | ✗ | ✗ | ✗ |
| Performance Agent | Read | ✗ | ✗ | ✗ |
| Testing Agent | Read | ✗ | Full | ✗ |
| DevOps Agent | Read | ✗ | ✗ | Full |
| Documentation Agent | Read | ✗ | ✗ | ✗ |
| Developer Agent (fix) | Read + Write | Read + Write | Run tests | ✗ |

---

## PostgreSQL Database Schema

### AuditJobs

Tracks every repository audit submitted to the platform.

| Column | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| repo_url | TEXT | Target GitHub repository URL |
| repo_name | TEXT | Extracted repo name |
| status | ENUM | pending / analyzing / complete / failed |
| health_score | INT | Overall score 0–100, nullable until complete |
| created_at | TIMESTAMP | |
| completed_at | TIMESTAMP | Nullable |

### Findings

One record per issue found by any agent.

| Column | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| audit_id | UUID | FK → AuditJobs |
| agent_role | TEXT | Which agent found this |
| category | TEXT | security / code_quality / architecture / performance / testing / devops / documentation |
| severity | ENUM | critical / high / medium / low |
| title | TEXT | Short description |
| detail | TEXT | Full explanation with evidence |
| file_path | TEXT | Relevant file, nullable |
| line_number | INT | Nullable |
| confidence | FLOAT | 0.0 – 1.0 |
| auto_fix_available | BOOLEAN | |
| fix_status | ENUM | none / suggested / approved / pr_created / merged |
| created_at | TIMESTAMP | |

### AgentRuns

One record per agent invocation within an audit.

| Column | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| audit_id | UUID | FK → AuditJobs |
| agent_role | TEXT | repo_analyzer / security / code_quality / etc. |
| tokens_used | INT | |
| cost_usd | FLOAT | |
| turns | INT | Number of AutoGen turns |
| findings_produced | INT | How many findings this agent raised |
| status | ENUM | success / failed / retried |
| started_at | TIMESTAMP | |
| ended_at | TIMESTAMP | |

### ToolExecutions

Granular log of every MCP tool call made.

| Column | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| run_id | UUID | FK → AgentRuns |
| mcp_server | TEXT | github_mcp / filesystem_mcp / test_mcp / devops_mcp |
| tool_name | TEXT | e.g. read_file, run_bandit |
| input_args | JSONB | Arguments passed |
| output | JSONB | Tool response |
| status | ENUM | success / failed / timeout |
| latency_ms | INT | |
| called_at | TIMESTAMP | |

### Evaluations

Stores every evaluation score produced by the confidence pipeline.

| Column | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| audit_id | UUID | FK → AuditJobs |
| metric | TEXT | e.g. finding_accuracy, tool_selection_accuracy |
| score | FLOAT | 0.0 – 1.0 or raw value |
| feedback | TEXT | LLM judge reasoning, nullable |
| evaluated_at | TIMESTAMP | |

### PromptVariations

Powers the self-improvement loop.

| Column | Type | Notes |
|---|---|---|
| id | UUID | Primary key |
| agent_role | TEXT | Which agent this prompt is for |
| prompt_text | TEXT | Full system prompt |
| avg_score | FLOAT | Average score across benchmark runs |
| is_active | BOOLEAN | Currently deployed prompt |
| created_at | TIMESTAMP | |
| promoted_at | TIMESTAMP | Nullable |

---

## End-to-End Event Flow

```
1.  User submits GitHub repo URL via dashboard or webhook
2.  FastAPI creates AuditJob record (status: pending)
3.  FastAPI dispatches event to AutoGen team
4.  Repository Analyzer clones and maps the repo structure
5.  Manager creates analysis plan, updates AuditJob (status: analyzing)
6.  7 specialist agents run (parallel where possible):
      Each agent reads the repo via github_mcp
      Each agent uses its specific tools (test_mcp, devops_mcp, etc.)
      Each agent produces a list of findings
7.  Manager receives all findings, deduplicates and prioritises
8.  Confidence Pipeline validates every finding:
      > 95%  → auto-fix allowed
      85–95% → suggest to user
      < 85%  → show evidence only
9.  Findings written to database, health score calculated
10. AuditJob marked complete, dashboard updates via WebSocket
11. User reviews findings
      └── If user approves auto-fix:
            Developer Agent writes fix to sandbox
            Test Agent verifies nothing breaks
            github_mcp creates PR
            Finding status updated to pr_created
12. CI/CD evaluates the agents themselves after each audit
      └── If agent quality drops → deployment blocked
             → self-improvement loop triggered
```
