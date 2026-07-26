# Agents — AgentOps

This document defines every agent in the AutoGen team: what they are responsible for, what MCP tools they can access, what they take as input, and what they produce as output.

---

## Orchestration Model

All agents run inside a **Microsoft AutoGen GroupChat**. The Manager Agent acts as the group chat manager — it controls the audit sequence, decides which specialist agents run, and synthesises all findings into the final health report.

Agents communicate by passing structured JSON messages. All tool calls go through MCP clients. No agent directly accesses GitHub, the filesystem, or any external system.

```
AutoGen GroupChat
│
├── Manager Agent              (orchestrates + synthesises)
├── Repository Analyzer        (maps the codebase first)
├── Code Quality Agent         (bugs, complexity, smells)
├── Security Agent             (vulnerabilities + static scanners)
├── Architecture Agent         (system design concerns)
├── Performance Agent          (N+1, blocking calls, memory)
├── Testing Agent              (coverage, missing tests)
├── DevOps Agent               (Docker, CI/CD, secrets)
├── Documentation Agent        (README, API docs, comments)
└── Developer Agent            (auto-fix only, triggered on demand)
```

---

## Agent 1 — Manager

**Role:** Orchestration and synthesis. The Manager runs twice — first to plan the audit sequence, last to synthesise all findings from all specialist agents into the final health report. It never calls tools.

**MCP Access:** None.

**First pass input:**
```json
{
  "audit_id": "uuid",
  "repo_url": "https://github.com/username/my-project",
  "repo_map": { "languages": ["Python", "JS"], "files": 137, "has_docker": true }
}
```

**First pass output — audit plan:**
```json
{
  "audit_sequence": ["repo_analyzer", "code_quality", "security", "architecture", "performance", "testing", "devops", "documentation"],
  "parallel_groups": [
    ["code_quality", "security", "performance"],
    ["architecture", "testing", "devops", "documentation"]
  ],
  "focus_areas": ["No CI/CD detected — DevOps agent should prioritise", "Python project — run Bandit"]
}
```

**Second pass — synthesis output:**
```json
{
  "health_score": 71,
  "category_scores": {
    "security": 82, "code_quality": 76, "architecture": 68,
    "performance": 61, "testing": 43, "devops": 58, "documentation": 81
  },
  "findings_by_severity": {
    "critical": ["finding_id_1", "finding_id_2"],
    "high": ["finding_id_3", "finding_id_4", "finding_id_5"],
    "medium": ["finding_id_6", "finding_id_7", "finding_id_8"]
  },
  "duplicates_removed": 3,
  "fix_order": ["finding_id_1", "finding_id_3", "finding_id_6"]
}
```

---

## Agent 2 — Repository Analyzer

**Role:** Understands the repository before any specialist agent runs. Maps the full structure, identifies the tech stack, detects what's present and what's missing, and builds the context all other agents will use.

**MCP Access:** `github_mcp` (read)

**Available Tools:**
- `github_mcp.clone_repository()` — clones the repo to a temporary read-only sandbox
- `github_mcp.get_repository_tree()` — full file tree
- `github_mcp.read_file()` — reads specific files (requirements.txt, package.json, Dockerfile etc.)
- `github_mcp.search_code()` — finds patterns across the codebase

**Output:**
```json
{
  "project_type": "Django + React",
  "languages": ["Python", "JavaScript"],
  "database": "PostgreSQL",
  "infrastructure": "Docker",
  "testing_framework": "pytest",
  "ci_cd": "None detected",
  "total_files": 137,
  "total_lines": 28431,
  "dependencies": 42,
  "has_env_example": true,
  "has_dockerfile": true,
  "has_docker_compose": true,
  "architecture_map": {
    "React Frontend": ["Django API"],
    "Django API": ["PostgreSQL", "Redis"],
    "Background Workers": ["Redis"]
  },
  "missing_detected": ["CI/CD pipeline", "API documentation", "test coverage report"]
}
```

---

## Agent 3 — Code Quality Agent

**Role:** Finds bugs, dead code, duplicate logic, poor error handling, overly complex functions, code smells, and violations of language best practices.

**MCP Access:** `github_mcp` (read), `test_mcp` (lint only)

**Available Tools:**
- `github_mcp.read_file()` — reads source files
- `github_mcp.search_code()` — finds patterns (e.g. bare `except:`, unused imports)
- `test_mcp.run_linter()` — Flake8 for Python, ESLint for JS

**Example Finding Output:**
```json
{
  "category": "code_quality",
  "severity": "high",
  "title": "Cyclomatic complexity too high in checkout.py",
  "detail": "The checkout() function has a cyclomatic complexity of 18. Functions above 10 are hard to test and maintain. Recommend splitting into validate_order(), calculate_total(), process_payment(), create_order().",
  "file_path": "orders/checkout.py",
  "line_number": 142,
  "confidence": 0.94,
  "auto_fix_available": false
}
```

---

## Agent 4 — Security Agent

**Role:** Finds hardcoded secrets, injection vulnerabilities, authentication issues, insecure configurations, and dependency vulnerabilities. Integrates Bandit, Semgrep, and Trivy — the LLM interprets and contextualises their output rather than replacing them.

**MCP Access:** `github_mcp` (read), `test_mcp` (Bandit, Semgrep, Trivy)

**Available Tools:**
- `github_mcp.read_file()` — reads source files for context
- `github_mcp.search_code()` — finds patterns like hardcoded strings
- `test_mcp.run_bandit()` — Python security linter
- `test_mcp.run_semgrep()` — multi-language static analysis
- `test_mcp.run_trivy()` — dependency vulnerability scanner

**How static tools integrate:**
```
test_mcp.run_bandit() returns raw JSON results
         │
         ▼
Security Agent reads the results
         │
         ▼
Reads the relevant file via github_mcp.read_file()
         │
         ▼
LLM interprets: Is this a real issue in this context?
What is the actual impact? What's the exact fix?
         │
         ▼
Produces a contextualised finding with evidence
```

**Example Finding Output:**
```json
{
  "category": "security",
  "severity": "critical",
  "title": "JWT secret hardcoded in source code",
  "detail": "users/auth.py line 47 contains SECRET_KEY = 'my-secret-key'. Anyone with repository access can forge authentication tokens. Move this to an environment variable loaded via os.environ.get('JWT_SECRET_KEY').",
  "file_path": "users/auth.py",
  "line_number": 47,
  "confidence": 0.99,
  "auto_fix_available": true,
  "tool_source": "bandit + manual verification"
}
```

---

## Agent 5 — Architecture Agent

**Role:** Evaluates whether the system architecture makes sense. Looks for tight coupling, missing abstractions, synchronous processing where async is needed, poor separation of concerns, and scalability risks.

**MCP Access:** `github_mcp` (read)

**Available Tools:**
- `github_mcp.read_file()` — reads key architectural files (views, models, settings, urls)
- `github_mcp.get_repository_tree()` — understands overall structure
- `github_mcp.search_code()` — finds coupling patterns

**Example Finding Output:**
```json
{
  "category": "architecture",
  "severity": "high",
  "title": "AI inference running synchronously in API request handler",
  "detail": "api/views.py runs model inference directly in the request handler. This will cause API timeouts under load and prevents horizontal scaling. Recommend moving inference to a Celery task queue with Redis as the broker.",
  "file_path": "api/views.py",
  "line_number": 89,
  "confidence": 0.91,
  "auto_fix_available": false
}
```

---

## Agent 6 — Performance Agent

**Role:** Finds N+1 database queries, blocking operations, inefficient algorithms, missing indexes, large API payloads, and memory issues.

**MCP Access:** `github_mcp` (read)

**Available Tools:**
- `github_mcp.read_file()` — reads views, models, serializers
- `github_mcp.search_code()` — finds queryset patterns, loop structures

**Example Finding Output:**
```json
{
  "category": "performance",
  "severity": "critical",
  "title": "N+1 query problem in orders list endpoint",
  "detail": "orders/views.py line 112 fetches orders then executes a separate query per order to get the user. For 10,000 orders this is 10,001 database queries per request. Add select_related('user') to the queryset. Estimated improvement: ~95% reduction in database queries.",
  "file_path": "orders/views.py",
  "line_number": 112,
  "confidence": 0.96,
  "auto_fix_available": true
}
```

---

## Agent 7 — Testing Agent

**Role:** Analyses test coverage, identifies critical untested paths, finds flaky tests, and assesses the overall testing health of the project.

**MCP Access:** `github_mcp` (read), `test_mcp` (full)

**Available Tools:**
- `github_mcp.read_file()` — reads test files and source files
- `test_mcp.run_tests()` — executes the test suite
- `test_mcp.run_coverage()` — produces coverage report

**Example Finding Output:**
```json
{
  "category": "testing",
  "severity": "high",
  "title": "Payment processing has 0% test coverage",
  "detail": "payments/service.py contains 247 lines of payment processing logic with zero test coverage. This is the highest risk-to-coverage ratio in the codebase. A failure here affects revenue directly.",
  "file_path": "payments/service.py",
  "line_number": null,
  "confidence": 0.99,
  "auto_fix_available": true,
  "coverage_data": {
    "overall_coverage": 42,
    "authentication": 23,
    "payment_processing": 0,
    "order_management": 71
  }
}
```

---

## Agent 8 — DevOps Agent

**Role:** Inspects Docker configuration, CI/CD setup, environment variable management, secrets handling, health checks, logging, and monitoring setup.

**MCP Access:** `github_mcp` (read), `devops_mcp` (full)

**Available Tools:**
- `github_mcp.read_file()` — reads Dockerfile, docker-compose, workflow files
- `devops_mcp.inspect_dockerfile()` — analyses Dockerfile for security and best practices
- `devops_mcp.inspect_docker_compose()` — checks compose configuration
- `devops_mcp.inspect_ci_pipeline()` — analyses GitHub Actions / CI config
- `devops_mcp.check_env_files()` — checks for exposed secrets in .env files
- `devops_mcp.get_dependency_vulnerabilities()` — checks for known CVEs

**Example Finding Output:**
```json
{
  "category": "devops",
  "severity": "high",
  "title": "Docker container runs as root",
  "detail": "The Dockerfile does not create a non-root user. If the container is compromised, the attacker has root access to the container filesystem. Add a USER directive after package installation.",
  "file_path": "Dockerfile",
  "line_number": null,
  "confidence": 0.98,
  "auto_fix_available": true
}
```

---

## Agent 9 — Documentation Agent

**Role:** Evaluates README quality, API documentation, setup instructions, environment variable documentation, and inline code comments.

**MCP Access:** `github_mcp` (read)

**Available Tools:**
- `github_mcp.read_file()` — reads README, docs folder, docstrings
- `github_mcp.get_repository_tree()` — checks for docs folder presence

**Example Finding Output:**
```json
{
  "category": "documentation",
  "severity": "medium",
  "title": "Environment variables undocumented",
  "detail": "The project uses 14 environment variables but .env.example only documents 6. A new developer cannot set up the project without reading the source code. Document all variables with descriptions and example values.",
  "file_path": ".env.example",
  "line_number": null,
  "confidence": 0.97,
  "auto_fix_available": false
}
```

---

## Agent 10 — Developer Agent (Auto-Fix Only)

**Role:** Triggered only when a user approves an auto-fix for a high-confidence finding. Writes the fix to a sandboxed filesystem, never to the actual repository directly. The Test Agent verifies the fix before a PR is created.

**MCP Access:** `github_mcp` (read + write), `filesystem_mcp` (read + write)

**Trigger:** User clicks "Fix Automatically" on a finding where `confidence > 0.95` and `auto_fix_available = true`

**Flow:**
```
User approves fix for Finding #1 (JWT hardcoded secret, confidence: 99%)
         │
         ▼
Developer Agent reads the file via github_mcp.read_file()
         │
         ▼
Writes corrected file to sandbox via filesystem_mcp.write_file()
         │
         ▼
Test Agent runs full test suite via test_mcp.run_tests()
         │
    ┌────┴────┐
    │         │
  PASS       FAIL
    │         │
    ▼         ▼
github_mcp  Developer
.create_pr  retries
            (max 2)
    │
    ▼
Finding status → pr_created
PR link shown to user
```

**Output:**
```json
{
  "finding_id": "uuid",
  "pr_url": "https://github.com/username/my-project/pull/43",
  "files_changed": ["users/auth.py"],
  "tests_passed": 24,
  "tests_failed": 0,
  "confidence": 0.99
}
```
