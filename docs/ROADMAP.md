# Roadmap — AgentOps

What was actually built across V1–V5, and what's planned next.

---

## Status Summary

| Version | Focus | Status |
|---|---|---|
| V1 | Core audit pipeline (repo analysis → findings → health score) | ✅ Complete |
| V2 | MCP server architecture (`github_mcp` active; 3 more built) | ✅ Complete (auto-fix wiring pending) |
| V3 | Confidence pipeline + consolidated unified audit | ✅ Complete |
| V4 | CI/CD quality gate + self-improvement loop | ✅ Complete |
| V5 | GitHub webhook + continuous monitoring | ✅ Complete |
| V6 | Auto-fix end-to-end | 🔲 Planned, not started |

---

## What's Done

- FastAPI backend with async SQLAlchemy models for all 6 tables (`audit_jobs`, `findings`, `agent_runs`, `tool_executions`, `evaluations`, `prompt_variations`)
- Full REST API: audit submission/listing/detail, findings + summary, evaluations, fix approval, GitHub webhook + health checks
- `repo_analyzer.py` fetching real repo data through `github_mcp` over the MCP stdio protocol
- `unified_agent.py` — a single LLM call covering all 7 audit dimensions, replacing what was originally planned as 7 separate specialist LLM calls (those specialist modules still exist, unused, for a future specialist mode — see [AGENTS.md](./AGENTS.md))
- `manager.py` — pure-Python deduplication, sorting, and health-score calculation
- `confidence_pipeline.py` — rule-based-only finding validation (no LLM call, deliberately, to control cost)
- `notifier.py` — new/resolved finding diffing against the previous audit for a repo
- `evaluation/framework.py` — 3 deterministic metric groups + 1 LLM-judge call, persisted as ~16 evaluation rows per audit
- `check_threshold.py` + `.github/workflows/eval_gate.yml` — a real CI quality gate reading live evaluation data from Postgres
- `prompt_optimizer.py` — self-improvement loop that drafts and conditionally promotes new prompts when `agent_success_rate` degrades
- GitHub push webhook with HMAC signature verification, branch filtering, and duplicate-audit suppression
- 4 MCP servers built and containerized (`github_mcp` active; `filesystem_mcp`, `test_mcp`, `devops_mcp` running standby)
- Next.js dashboard: audit list, audit detail, findings, evaluations
- CI (`ci.yml`): flake8 + black, pytest, Docker builds for all 5 images, frontend build
- 11 passing tests across `backend/tests/` and `evaluation/tests/`

---

## Honest Gaps

These are real, not hidden:

1. **Auto-fix is not wired end-to-end.** `POST /api/fixes/{finding_id}/approve` validates confidence and queues a background task, but that task (`_queue_auto_fix` in `backend/api/fixes.py`) only logs — it doesn't call `filesystem_mcp`, run tests via `test_mcp`, or create a PR via `github_mcp`. `agents/developer.py` and `agents/team.py` are stub files (`pass`) with no implementation.
2. **`filesystem_mcp`, `test_mcp`, and `devops_mcp` are idle.** All three run and pass health checks in Docker Compose, but no code in the repo currently calls their tools.
3. **No audit timeline / observability tracing.** You get the final findings and evaluation scores, not a step-by-step trace of what the pipeline did along the way.
4. **Token/cost tracking always reports 0.** `AgentRun.tokens_used` and `cost_usd` columns exist and are read by `evaluation/metrics/agent_metrics.py`, but the OpenAI/OpenRouter call site in `agents/_llm_common.py` never populates them.
5. **No cloud deployment.** Everything runs via local Docker Compose; there's no live URL.
6. **The benchmark dataset is empty** (`evaluation/benchmarks/dataset.json` has `"cases": []`) — there's no automated precision/recall measurement against known issues yet, so `prompt_optimizer.py`'s "benchmark" is a simplified proxy (average confidence of recent findings), not a true benchmark run.

---

## Next Priorities

1. **Observability / audit timeline** — surface a step-by-step trace of each audit (repo fetch → unified call → validation → synthesis → evaluation) instead of only the final result.
2. **Activate `filesystem_mcp` and `devops_mcp` in the audit pipeline** — start using their tools for real DevOps/dependency inspection rather than leaving them standby.
3. **Auto-fix end-to-end (V6)** — implement `agents/developer.py`, wire `_queue_auto_fix` in `backend/api/fixes.py` to actually write a fix via `filesystem_mcp`, verify it with `test_mcp`, and open a PR via `github_mcp`'s `create_pull_request` tool.
4. **Cloud deployment** — get a live URL up, even a minimal one, for demo purposes.
5. **Token/cost tracking** — populate `tokens_used` and `cost_usd` on `AgentRun` from the actual OpenAI/OpenRouter response usage data, so `total_cost_usd` and `total_tokens` evaluation metrics become meaningful instead of always reading 0.
6. **Populate the benchmark dataset** — add real `known_findings` cases to `evaluation/benchmarks/dataset.json` and build an actual precision/recall benchmark runner, replacing the current simplified proxy score used by `prompt_optimizer.py`.
