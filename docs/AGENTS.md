# Agents — AgentOps

This document describes what actually runs when an audit executes, module by module, based on the current implementation in `agents/` and `backend/services/`.

The most important correction versus earlier drafts of this doc: **there is no multi-agent group chat and no 9-agent parallel run.** The pipeline that actually executes for every audit is two agent-shaped modules plus a pure-Python synthesis step. A set of individual specialist agent files also exists in the codebase but is currently dead code from the dispatcher's point of view.

---

## What Actually Runs (per audit)

```
backend/services/dispatcher.py
        │
        ▼
1. repo_analyzer.py     — fetches repo via github_mcp, builds repo_map
        │
        ▼
2. unified_agent.py     — ONE LLM call, all 7 dimensions
        │
        ▼
3. confidence_pipeline.py — rule-based validation (evaluation/, not agents/)
        │
        ▼
4. manager.py           — dedup, sort, health score (pure Python, no LLM)
        │
        ▼
5. notifier.py          — diffs against previous audit (backend/services/)
        │
        ▼
6. evaluation/framework.py — metrics + 1 LLM judge call
        │
        ▼
7. prompt_optimizer.py  — self-improvement loop (backend/services/)
```

---

## repo_analyzer.py

**Role:** Understands the repository before the LLM sees anything. Fetches the file tree and reads a small set of key files.

**MCP Access:** `github_mcp` (read only), via `agents/tools/github_client.py`.

**What it actually does (`analyze_repository`):**
- Opens one `github_mcp` session, fetches repo metadata and the full file tree
- Detects languages by file extension
- Detects presence of a Dockerfile, docker-compose.yml, README, tests directory, and a `.github/workflows/*.yml` CI config
- Reads the contents of: the first matching dependency file (`requirements.txt` or `package.json`), the Dockerfile, the README, and the first CI workflow file it finds
- Guesses a `project_type` string (e.g. "Django + React", "FastAPI") from the dependency file content and detected languages

**Output (`repo_map`):**
```json
{
  "project_type": "Django + React",
  "languages": ["JavaScript", "Python"],
  "has_dockerfile": true,
  "has_docker_compose": true,
  "has_ci_cd": false,
  "has_tests": true,
  "has_readme": true,
  "total_files": 137,
  "dependency_file_content": "...",
  "dockerfile_content": "...",
  "readme_content": "...",
  "ci_cd_content": null,
  "file_tree": ["path/to/file.py", "..."]
}
```

No LLM call happens in this module.

---

## unified_agent.py

**Role:** Replaces the 7 specialist agents described further below. A single LLM call is given the entire `repo_map` and asked to reason about security, code_quality, architecture, performance, testing, devops, and documentation simultaneously, and to return 5-15 findings across those categories.

**MCP Access:** None directly — it only sees the `repo_map` dict already assembled by `repo_analyzer.py`.

**LLM calls:** Exactly 1, via `agents/_llm_common.py::call_llm_for_findings`, which retries up to 3 times on empty responses or rate limits and returns `[]` on any unrecoverable failure (an LLM failure never crashes the audit — it just produces zero findings).

**Prompt strategy:** One system prompt lists all 7 dimensions and the required JSON schema for each finding (`category`, `severity`, `title`, `detail` ≥ 50 chars, `file_path`, `line_number`, `confidence`, `auto_fix_available`). The user prompt packs in the file tree (first 80 entries), dependency file content, Dockerfile content, and README content, each truncated to a few thousand characters to control token usage.

**Output:** A flat list of finding dicts tagged with `agent_role = category` (e.g. a security finding gets `agent_role: "security"` even though it came from the single unified call).

---

## manager.py (`synthesise_findings`)

**Role:** Pure Python synthesis — no LLM call. Deduplicates findings by exact title match (keeping the higher-confidence copy), sorts by severity then confidence, and computes a health score.

**Health score formula:** Starts at 100. For each severity level, subtracts `count * penalty`, capped per severity (`critical`: 12/finding up to −36, `high`: 6/finding up to −18, `medium`: 3/finding up to −15, `low`: 1/finding up to −7), floored at 0.

**Output:**
```json
{
  "health_score": 71,
  "findings": [ /* deduped, sorted findings */ ],
  "summary": {"critical": 2, "high": 3, "medium": 3, "low": 0, "total": 8}
}
```

---

## confidence_pipeline.py (`evaluation/`)

Not in `agents/`, but part of the same per-audit flow — see [EVALUATION.md](./EVALUATION.md) for the full rule set. In short: 3 rule-based checks (non-empty title, substantial detail, evidence file exists in the repo tree), no LLM call, findings below 0.40 confidence are discarded, and `auto_fix_available` is forced to `false` below 0.95 confidence.

---

## notifier.py (`backend/services/`)

**Role:** After findings are written to the DB, looks up the most recent previous *completed* audit for the same `repo_url`, diffs finding titles, and logs which findings are new and how many were resolved. Currently logs only (console/structured logging) — no email/Slack integration exists.

---

## prompt_optimizer.py (`backend/services/`)

**Role:** Self-improvement loop, triggered at the end of every audit. Looks at the average `agent_success_rate` evaluation score across the last 5 completed audits. If it's below 0.80, finds the agent role with the most failed `AgentRun` rows, asks the LLM to draft an improved system prompt addressing that failure, saves it as an inactive `PromptVariation`, and promotes it (marks `is_active = true`) only if a simplified benchmark score (average confidence of that role's last 3 findings) beats the current active prompt's score.

---

## Individual Specialist Agents — NOT Currently Used

`agents/security.py`, `code_quality.py`, `architecture.py`, `performance.py`, `testing.py`, `devops.py`, and `documentation.py` all still exist, each making its own single LLM call scoped to one category (e.g. `security.py::run_security_audit` only asks about hardcoded secrets, injection risk, auth issues). They are fully functional in isolation and share the same `call_llm_for_findings` helper as `unified_agent.py`.

**They are not imported by `backend/services/dispatcher.py`.** The dispatcher only calls `unified_agent.run_unified_audit`. These files are preserved so the system can be switched back to a "specialist mode" (7 LLM calls instead of 1) if per-category depth becomes more valuable than per-audit cost — see [CONTRIBUTING.md](./CONTRIBUTING.md) for how to re-enable them.

`agents/team.py` (meant to assemble a multi-agent group) and `agents/developer.py` (meant to propose and submit fixes) are both stub files — `build_agent_team()` and `DeveloperAgent.propose_fix()` are unimplemented (`pass`). There is no group-chat orchestration framework in this codebase; agent modules are called directly as async functions from `dispatcher.py`.

---

## MCP Tool Access Summary

| Module | github_mcp | filesystem_mcp | test_mcp | devops_mcp |
|---|---|---|---|---|
| repo_analyzer.py | Read (active) | — | — | — |
| unified_agent.py | — (works off repo_map only) | — | — | — |
| Individual specialists (unused) | — (work off repo_map only) | — | — | — |
| developer.py (stub) | Intended read+write | Intended read+write | Intended | — |

`filesystem_mcp`, `test_mcp`, and `devops_mcp` are running standby servers with no current caller in the codebase.
