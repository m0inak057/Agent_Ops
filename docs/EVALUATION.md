# Evaluation Framework — AgentOps

This document covers how agent findings are validated, what the confidence pipeline does, what the CI quality gate enforces, and how the self-improvement loop works — as actually implemented.

---

## Why Evaluation Matters Here

A codebase auditor that produces false positives is worse than no auditor at all. AgentOps runs two independent layers of evaluation:

1. **Finding-level validation** (`evaluation/confidence_pipeline.py`) — every finding produced by `unified_agent.py` passes through rule-based checks before it's written to the database. This costs zero extra LLM calls.

2. **Audit-level evaluation** (`evaluation/framework.py`) — after an audit completes, deterministic metrics are computed from the database and one additional LLM call scores the overall quality of the audit's findings. These scores feed the CI quality gate and the self-improvement loop.

**Total LLM calls per audit: 2** — the unified audit call, and the audit-quality judge call.

---

## Layer 1 — The Confidence Pipeline (Rule-Based Only)

`evaluation/confidence_pipeline.py::validate_single_finding` runs 3 rule-based steps on every finding. There is no LLM call anywhere in this pipeline.

```
Agent produces a finding
         │
         ▼
Step 1: Title/detail sanity check
  - Discard if title is empty
  - Discard if detail is under 20 characters
  - Subtract 0.1 confidence if detail is under 50 characters
         │
         ▼
Step 2: Evidence check
  - If file_path is given but not present in repo_map["file_tree"],
    subtract 0.15 confidence
         │
         ▼
Step 3: Threshold enforcement
  - Clamp confidence to [0.0, 1.0]
  - Discard the finding entirely if confidence < 0.40
  - Force auto_fix_available = False if confidence < 0.95
         │
         ▼
Finding written to the findings table with its adjusted confidence
```

### Confidence Thresholds

| Threshold | Effect |
|---|---|
| < 0.40 | Finding is discarded entirely — never written to the DB |
| 0.40 – 0.95 | Finding is shown, `auto_fix_available` is forced to `false` regardless of what the LLM said |
| >= 0.95 | Finding is shown, `auto_fix_available` may remain `true`; `POST /api/fixes/{id}/approve` will accept it |

---

## Layer 2 — Audit-Level Evaluation Metrics

`evaluation/framework.py::run_evaluation` runs after every completed audit and writes each computed metric as a row in the `evaluations` table. It never raises — a failure here is logged and swallowed so it can't take down the audit pipeline.

Four metric groups run concurrently via `asyncio.gather`:

### Agent Metrics (deterministic, from `agent_runs`)

| Metric | Computed As |
|---|---|
| `agent_success_rate` | successful `AgentRun` rows / total rows for the audit |
| `average_turn_count` | average `turns` across runs (currently always 0 — turns aren't tracked) |
| `finding_production_rate` | total findings produced / number of agent runs |
| `total_cost_usd` | sum of `cost_usd` across runs (currently always 0 — not instrumented) |
| `total_tokens` | sum of `tokens_used` across runs (currently always 0 — not instrumented) |

### Finding Metrics (deterministic, from `findings`)

| Metric | Computed As |
|---|---|
| `average_confidence` | mean `confidence` across the audit's findings |
| `finding_distribution_{severity}` | one row per severity present, % of findings at that severity |
| `auto_fix_rate` | % of findings with `auto_fix_available = true` |

### System Metrics (deterministic, from `audit_jobs` + `findings`)

| Metric | Computed As |
|---|---|
| `total_latency_seconds` | `completed_at - created_at` |
| `health_score` | copied from `AuditJob.health_score` |
| `finding_count` | count of findings for the audit |

### LLM-as-a-Judge (1 LLM call — `evaluation/metrics/llm_judge.py`)

A single call sends up to 10 findings (title/severity/category only) plus the repo type to the LLM and asks it to score four dimensions from 0.0–1.0:

```json
{
  "finding_relevance": 0.0-1.0,
  "finding_depth": 0.0-1.0,
  "coverage": 0.0-1.0,
  "actionability": 0.0-1.0,
  "reasoning": "..."
}
```

Each dimension is written as its own `evaluations` row, prefixed `audit_quality_` (e.g. `audit_quality_finding_relevance`), sharing the same `reasoning` text as feedback. If the call fails or the response can't be parsed, this metric group simply contributes no rows — it never fails the audit.

A typical completed audit ends up with roughly 5 (agent) + up to 6 (finding, depending on how many severities are present) + 3 (system) + 4 (judge) ≈ **16 evaluation rows**.

---

## The Quality Gate (`check_threshold.py`)

Runs in CI (`.github/workflows/eval_gate.yml`, chained after `ci.yml` via `workflow_run`). Reads the last 5 completed `audit_jobs`, averages each metric across their `evaluations` rows, and compares against:

```python
QUALITY_GATE_RULES = {
    "agent_success_rate":              {"operator": ">=", "threshold": 0.80},
    "average_confidence":              {"operator": ">=", "threshold": 0.70},
    "audit_quality_finding_relevance": {"operator": ">=", "threshold": 0.70},
}
```

If there's no `DATABASE_URL` configured, or no completed audits exist yet, the check exits `0` (skip, don't fail) — the gate is designed not to block CI before there's any real audit history. If evaluations exist but any rule's average falls below its threshold, the script prints a pass/fail table and exits `1`, blocking the merge.

---

## Benchmark Dataset

`evaluation/benchmarks/dataset.json` currently contains no cases:

```json
{
  "version": "0.1.0",
  "description": "Benchmark dataset of labeled repositories and expected findings used to evaluate AgentOps audit quality.",
  "cases": []
}
```

The schema is designed around a `known_findings` list per benchmark repo (category, title, file_path, line_number, severity), but no benchmark repos have been populated yet. `evaluation/seed_benchmarks.py` exists to load this file into the database once cases are added.

---

## Self-Improvement Loop

Implemented in `backend/services/prompt_optimizer.py::check_and_improve_prompts`, called at the end of every audit dispatch (best-effort — a failure here is logged and never fails the audit).

```
1. Average agent_success_rate over the last 5 completed audits
   If >= 0.80 → do nothing
                          │
                          ▼
2. Find the agent_role with the most FAILED AgentRun rows
   If none found → do nothing
                          │
                          ▼
3. Load that role's currently active prompt
   (PromptVariations.is_active=True, falling back to the static
    agents/prompts/{role}.txt file)
                          │
                          ▼
4. One LLM call drafts an improved prompt given the current prompt
   and a human-readable failure reason (e.g. "3 recent agent runs
   failed for role 'unified'")
                          │
                          ▼
5. Save the new prompt as an inactive PromptVariation
                          │
                          ▼
6. Score both old and new via a simplified benchmark:
   average confidence of that role's last 3 findings
                          │
                    ┌─────┴─────┐
              new > old      new <= old
                    │             │
                    ▼             ▼
          Promote (is_active=True,   Keep old prompt active,
          old variation deactivated)  new one saved for review
```

Note: because a brand-new prompt has no findings history of its own yet, its "new" benchmark score is computed against the same (currently empty) history as before it existed — a real improvement is only visible once the new prompt has been promoted and used in production audits for a while. This is a known limitation of the simplified benchmark, not a bug.

---

## Tests

- `evaluation/tests/test_confidence_pipeline.py` — 2 tests validating the confidence pipeline's discard/keep behavior, plus a check that `check_threshold.py` defines `QUALITY_GATE_RULES`.
- `backend/tests/test_api.py` and `backend/tests/test_manager.py` — API structure and `manager.py` dedup/health-score logic.
- 11 tests total across `backend/tests/` and `evaluation/tests/`, all passing.
