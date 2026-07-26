# Implementation Roadmap — AgentOps

5-version build plan. Build in this order — each version is a complete, working product. Never skip ahead.

---

## Version Overview

| Version | Focus | What You Can Demo |
|---|---|---|
| V1 | 4 agents + health report | Paste repo → get structured audit report |
| V2 | MCP servers + sandbox + auto-fix + PR | "Fix this automatically" creates a real PR |
| V3 | Confidence pipeline + full agent team | Every finding has a validated confidence score |
| V4 | CI/CD quality gate + self-improvement | Agents evaluate themselves, bad prompts get replaced |
| V5 | GitHub webhook + continuous monitoring | System watches your repo and alerts on new commits |

---

## Version 1 — Core Audit Pipeline

**Goal:** A user pastes a GitHub repo URL and receives a structured health report with findings across 4 categories. No auto-fix yet, no MCP servers. Agents call GitHub API directly to keep complexity low while establishing the pipeline.

**Weeks 1–2**

**Infrastructure tasks:**
- Initialise monorepo folder structure
- Set up `docker-compose.yml` with PostgreSQL, Redis, FastAPI
- Write all SQLAlchemy models: AuditJobs, Findings, AgentRuns, ToolExecutions, Evaluations, PromptVariations
- Run Alembic migrations
- Build FastAPI endpoints: `POST /api/audits`, `GET /api/audits/{id}`, `GET /api/findings`
- Write `.env.example`

**Agent tasks:**
- Install Microsoft AutoGen
- Build Repository Analyzer agent (maps tech stack, files, architecture)
- Build Code Quality Agent (complexity, dead code, error handling)
- Build Security Agent (hardcoded secrets, injection risks — direct Bandit call, no MCP yet)
- Build Testing Agent (coverage analysis, untested critical paths)
- Build Manager Agent (synthesises findings, produces health score)
- Wire agents to FastAPI: POST /api/audits triggers the team

**Definition of Done:**
```bash
curl -X POST http://localhost:8000/api/audits \
  -d '{"repo_url": "https://github.com/username/my-project"}'

# 60 seconds later:
curl http://localhost:8000/api/audits/{audit_id}
# Returns: health_score, category_scores, findings list
```

---

## Version 2 — MCP Servers + Auto-Fix + PR Creation

**Goal:** All agent tool calls go through isolated MCP servers. Add the Developer Agent for auto-fix. A user can click "Fix Automatically" on a finding and receive a real Pull Request.

**Weeks 3–4**

**MCP server tasks:**
- Install Python MCP SDK
- Build `github_mcp`: `clone_repository`, `get_repository_tree`, `read_file`, `search_code`, `create_branch`, `create_commit`, `create_pull_request`
- Build `filesystem_mcp`: `read_file`, `write_file`, `list_directory`, `search_files` (sandbox enforced)
- Build `test_mcp`: `run_tests`, `run_coverage`, `run_linter`, `run_bandit`, `run_semgrep`, `run_trivy`
- Build `devops_mcp`: `inspect_dockerfile`, `inspect_docker_compose`, `inspect_ci_pipeline`, `check_env_files`
- Add `/health` endpoint to each MCP server
- Dockerise all 4 MCP servers
- Add to `docker-compose.yml`
- Migrate all agents from direct API calls to MCP client connectors

**Auto-fix tasks:**
- Build Developer Agent (filesystem_mcp read/write, triggered only on user approval)
- Add `POST /api/fixes/{finding_id}` endpoint
- Wire fix flow: approve → Developer writes to sandbox → Test Agent verifies → PR created
- Add `fix_status` tracking to Findings table

**Definition of Done:**
- All 4 MCP servers respond to direct cURL tests
- All agents use MCP clients (no direct API calls)
- Approve a finding → PR appears on the target GitHub repo within 2 minutes

---

## Version 3 — Full Agent Team + Confidence Pipeline

**Goal:** Add all remaining specialist agents. Build the confidence pipeline that validates every finding and assigns a confidence score. Users see confidence on every finding and the auto-fix threshold is enforced.

**Weeks 5–6**

**Agent tasks:**
- Build Architecture Agent (coupling, missing async, scalability risks)
- Build Performance Agent (N+1 queries, blocking operations, missing indexes)
- Build DevOps Agent (Docker security, CI/CD gaps, secrets management)
- Build Documentation Agent (README quality, API docs, env var coverage)
- Update Manager Agent to synthesise findings from all 8 specialist agents
- Add deduplication logic to Manager (remove duplicate findings across agents)

**Confidence pipeline tasks:**
- Build `evaluation/confidence_pipeline.py`:
  - Step 1: Rule-based verification (does cited evidence actually exist?)
  - Step 2: Static tool cross-check (Bandit/Semgrep confirms security findings?)
  - Step 3: LLM-as-a-Judge validity scoring
  - Step 4: Cross-agent agreement check
- Apply confidence thresholds to all findings before writing to DB
- Update frontend to show confidence score on every finding card
- Enforce: `auto_fix_available = true` only when `confidence > 0.95`
- Build `evaluation/benchmarks/dataset.json` with 3 benchmark repos and 15+ known issues

**Definition of Done:**
- Full 9-agent pipeline runs end-to-end (excluding Developer Agent)
- Every finding in the database has a confidence score
- Benchmark run correctly identifies ≥ 80% of known issues
- Auto-fix button only appears on findings with confidence > 95%

---

## Version 4 — CI/CD Quality Gate + Self-Improvement Loop

**Goal:** GitHub Actions evaluates the agents after every push. If agent quality drops, the pipeline blocks deployment. The self-improvement loop automatically attempts to fix degraded agents by improving their prompts.

**Weeks 7–8**

**CI/CD tasks:**
- Write `.github/workflows/ci.yml`: Flake8, Black, Pytest, Docker build
- Write `.github/workflows/eval_gate.yml`:
  - Runs benchmark dataset against agent team
  - Calls `check_threshold.py`
  - Posts evaluation report as PR comment
- Implement `check_threshold.py`: reads Evaluations table, exits 1 if any gate fails
- Configure branch protection: main requires both workflows to pass

**Self-improvement loop tasks:**
- Build `backend/services/prompt_optimizer.py`:
  - Queries Findings table for low-validity findings per agent
  - Identifies false positive patterns
  - Calls LLM to draft improved system prompt
  - Saves to PromptVariations (is_active = false)
  - Runs benchmark with old vs new prompt
  - Promotes if F1 score improves
- Wire trigger: eval_gate failure for specific agent → prompt_optimizer runs for that agent
- Add prompt version history to dashboard
- Build `evaluation/metrics/` module with all metric implementations

**Definition of Done:**
- Deliberately degrade a prompt → watch quality gate catch it → pipeline fails
- Watch self-improvement loop draft and benchmark a new prompt
- Verify next audit uses promoted prompt from PromptVariations table
- All quality gate rules enforced in CI

---

## Version 5 — Continuous Monitoring + Polish

**Goal:** GitHub webhook enables automatic re-auditing on every commit. The system watches your repository and alerts you to new issues introduced by new code. Full dashboard, demo video, portfolio-ready.

**Weeks 9–10**

**Webhook tasks:**
- Build `POST /api/webhooks/github` endpoint
- Validate webhook signature with `WEBHOOK_SECRET`
- On push event: trigger new audit for the affected repository
- Compare new findings against previous audit — highlight what's new vs existing
- Send notification (dashboard alert, or email/Slack if configured)

**Frontend tasks:**
- Main dashboard: overall health score, category scores, finding counts by severity
- Audit viewer: finding-by-finding walkthrough with evidence, confidence, fix button
- Finding detail: full evidence, file preview, suggested fix, approve button
- Evaluation history: agent performance trends over time with charts
- Prompt version history: score evolution per agent
- Real-time audit progress via WebSocket (watch agents run live)

**Polish tasks:**
- Write comprehensive `README.md` with architecture diagram and demo GIF
- Record 3–5 minute demo video: paste repo → watch agents → review findings → approve auto-fix → PR appears
- Deploy to AWS/GCP with live URL
- Add live demo link to README

**Definition of Done:**
- Push a commit with a planted bug → receive dashboard alert within 90 seconds
- Demo video recorded and linked
- Live deployment accessible at public URL
- All 7 documentation files accurate and complete
- Repository is public and portfolio-ready

---

## Week-by-Week Schedule

| Week | Version | Focus |
|---|---|---|
| 1 | V1 | Infrastructure, DB models, FastAPI skeleton |
| 2 | V1 | 4 agents + Manager, full audit pipeline working |
| 3 | V2 | All 4 MCP servers built and tested in isolation |
| 4 | V2 | Agents migrated to MCP, Developer Agent + auto-fix + PR |
| 5 | V3 | Architecture, Performance, DevOps, Documentation agents |
| 6 | V3 | Confidence pipeline, benchmark dataset, threshold enforcement |
| 7 | V4 | CI/CD quality gate, eval_gate workflow |
| 8 | V4 | Self-improvement loop, prompt version history |
| 9 | V5 | GitHub webhook, continuous monitoring, notifications |
| 10 | V5 | Frontend polish, demo video, deployment, README |

---

## Milestone Checkpoints

| Checkpoint | Week | How to Verify |
|---|---|---|
| Stack running | End of Week 1 | `docker compose up` healthy, migrations complete |
| First audit working | End of Week 2 | Paste repo URL → health report with findings in DB |
| MCP servers ready | End of Week 3 | All 4 servers respond to cURL, all tools return valid responses |
| Auto-fix working | End of Week 4 | Approve finding → PR appears on target repo |
| Full team running | End of Week 5 | All 9 agents produce findings, Manager synthesises correctly |
| Confidence pipeline | End of Week 6 | Every finding has confidence score, benchmark at ≥ 80% recall |
| CI gate blocking | End of Week 7 | Degrade a prompt → pipeline fails |
| Self-improvement | End of Week 8 | Degraded agent detects failure and promotes better prompt |
| Monitoring live | End of Week 9 | Commit triggers re-audit within 90 seconds |
| Portfolio ready | End of Week 10 | Live URL, demo video, complete docs, public repo |
