# Evaluation Framework — AgentOps

This document covers the full evaluation system: how agent findings are validated, what the confidence pipeline does, what the quality gate enforces, and how the self-improvement loop works.

---

## Why Evaluation Is the Core of This Platform

A codebase auditor that produces false positives is worse than no auditor at all. If developers can't trust the findings, they ignore all of them — including the real ones.

AgentOps solves this with a two-layer evaluation system:

1. **Finding-level evaluation:** Every finding produced by a specialist agent goes through a confidence pipeline before reaching the user. Low-confidence findings are shown with evidence only. Auto-fixes are only triggered above 95% confidence.

2. **Agent-level evaluation:** The agents themselves are continuously evaluated. If an agent's false positive rate rises or its finding accuracy drops, the CI/CD pipeline blocks deployment and the self-improvement loop kicks in.

The evaluation framework answers three questions:
1. **Are these findings accurate?** (Finding-level metrics)
2. **Are the agents behaving correctly?** (Agent-level metrics)
3. **Is the overall system healthy?** (System-level metrics)

---

## Layer 1 — The Confidence Pipeline

Every finding produced by a specialist agent passes through this pipeline before being written to the database.

```
Agent produces a finding
         │
         ▼
Step 1: Rule-based verification
(Does the evidence actually exist in the file/line cited?)
         │
         ▼
Step 2: Static analysis cross-check
(For security findings: does Bandit/Semgrep confirm it?)
         │
         ▼
Step 3: LLM-as-a-Judge
(Is this actually a problem in this specific context?)
         │
         ▼
Step 4: Cross-agent agreement
(Did another agent flag the same file/area?)
         │
         ▼
Final Confidence Score (0.0 – 1.0)
         │
    ┌────┴────┬──────────┐
    │         │          │
  > 0.95   0.85–0.95  < 0.85
    │         │          │
Auto-fix   Suggest    Evidence
allowed    to user    only
```

### Confidence Thresholds

| Threshold | User Experience |
|---|---|
| > 95% | Finding shown + "Fix Automatically" button available |
| 85% – 95% | Finding shown + "Suggest Fix" + requires user approval before PR |
| < 85% | Finding shown with evidence and reasoning, no fix option |

This is AI evaluation as a product feature. Users see the confidence score on every finding.

---

## Layer 2 — Agent-Level Evaluation Metrics

### Finding Accuracy Metrics (LLM-as-a-Judge)

These metrics require a separate LLM call — independent of the agent team — to score the quality of what agents produced.

**Finding Validity (0.0 – 1.0)**

For each finding in the benchmark dataset, the judge is given the finding and the actual source code and asks: is this a real issue?

Prompt structure:
```
You are a senior software engineer evaluating whether a reported code issue is genuine.

Finding: {finding_title}
Detail: {finding_detail}
File: {file_path}
Code: {file_content}

Score from 0.0 to 1.0:
- 1.0: Definitely a real issue, evidence is clear
- 0.5: Possibly an issue, context-dependent
- 0.0: False positive, not actually a problem

Respond in JSON: { "score": float, "reasoning": "..." }
```

**Finding Completeness (0.0 – 1.0)**

Did the agents find all the known issues in a benchmark repository? Measures recall — the false negative rate.

**Explanation Quality (1 – 5)**

Did the agent explain *why* the issue matters and *how* to fix it clearly? Rubric:
- 5: Clear, actionable, explains impact and exact fix
- 3: Identifies the issue but vague on impact or fix
- 1: Technically correct but useless to a developer

---

### Agent Behaviour Metrics (Deterministic)

Computed directly from AgentRuns and ToolExecutions table logs.

| Metric | How It's Computed | Target |
|---|---|---|
| Tool Selection Accuracy | % of tool calls where correct tool used for the agent's role | ≥ 85% |
| Tool Argument Accuracy | % of tool calls with valid, correctly formatted arguments | ≥ 90% |
| False Positive Rate | % of findings that fail LLM-judge validity check | ≤ 15% |
| Finding Coverage | % of known benchmark issues found | ≥ 80% |
| Duplicate Rate | % of findings flagged as duplicates by Manager | ≤ 10% |
| Turn Count | AutoGen turns per agent per audit | Logged |

---

### System-Level Metrics (Deterministic)

| Metric | Source | Notes |
|---|---|---|
| Total Audit Latency | `completed_at - created_at` | In seconds |
| Total Token Usage | Sum of `tokens_used` across all AgentRuns | Per audit |
| Total Cost (USD) | Sum of `cost_usd` across all AgentRuns | Per audit |
| Audit Failure Rate | % of audits that errored before completion | Tracked over time |
| Auto-fix Success Rate | % of auto-fixes where PR tests pass first attempt | Tracked over time |

---

## The Quality Gate

The quality gate runs as a step in the GitHub Actions CI/CD pipeline after every push to main. It evaluates the agents against the benchmark dataset and blocks deployment if quality drops.

```python
QUALITY_GATE_RULES = {
    "finding_validity":        {"operator": ">=", "threshold": 0.85},  # < 15% false positives
    "finding_coverage":        {"operator": ">=", "threshold": 0.80},  # finds 80%+ of known issues
    "tool_selection_accuracy": {"operator": ">=", "threshold": 0.85},
    "auto_fix_success_rate":   {"operator": ">=", "threshold": 0.90},  # fixes don't break tests
}
```

If any rule fails:

```
❌ Quality Gate FAILED
─────────────────────────────────────────────────────
finding_validity:        0.71  (required: >= 0.85)  FAIL  ← false positive rate too high
finding_coverage:        0.84  (required: >= 0.80)  PASS
tool_selection_accuracy: 0.89  (required: >= 0.85)  PASS
auto_fix_success_rate:   0.94  (required: >= 0.90)  PASS

Deployment blocked.
Affected agent: security_agent (false positive rate: 29%)
Self-improvement loop triggered for: security_agent
```

---

## Benchmark Dataset

Located at `evaluation/benchmarks/dataset.json`. Contains real (or realistic) repositories with known issues. Used to evaluate agent accuracy in a controlled, repeatable way.

```json
[
  {
    "id": "bench_001",
    "repo_url": "https://github.com/agentops-benchmarks/django-with-issues",
    "description": "Django API with 5 planted known issues",
    "known_findings": [
      {
        "category": "security",
        "title": "Hardcoded JWT secret",
        "file_path": "users/auth.py",
        "line_number": 47,
        "severity": "critical"
      },
      {
        "category": "performance",
        "title": "N+1 query in orders endpoint",
        "file_path": "orders/views.py",
        "line_number": 112,
        "severity": "critical"
      },
      {
        "category": "testing",
        "title": "Payment processing untested",
        "file_path": "payments/service.py",
        "severity": "high"
      },
      {
        "category": "devops",
        "title": "Docker running as root",
        "file_path": "Dockerfile",
        "severity": "high"
      },
      {
        "category": "code_quality",
        "title": "Cyclomatic complexity 18 in checkout",
        "file_path": "orders/checkout.py",
        "line_number": 142,
        "severity": "medium"
      }
    ]
  }
]
```

The benchmark runner in `evaluation/framework.py` runs all benchmark repos through the full agent team, compares found findings against known findings, and produces a precision/recall report.

---

## Self-Improvement Loop

```
Trigger: Quality gate detects finding_validity < 0.85 for a specific agent
         (e.g. Security Agent producing too many false positives)

Step 1 — Failure Analysis
  Query Findings table for the agent
  Filter: findings where LLM judge scored validity < 0.5
  Identify patterns:
    - What categories of false positives?
    - What file types triggered them?
    - What tool outputs led to them?

Step 2 — Prompt Draft
  LLM receives:
    - Current system prompt for the agent
    - 5 example false positives with judge reasoning
    - The identified pattern
  LLM produces a revised prompt that addresses the failure

Step 3 — Benchmark
  New prompt loaded into agent copy
  Benchmark dataset run with old vs new prompt
  Precision, recall, and F1 score compared

Step 4 — Promotion Decision
  If new F1 score > old F1 score:
    - New prompt → PromptVariations (is_active = true)
    - Old prompt archived
    - Score delta logged
    - Dashboard shows "Security Agent improved: false positive rate 29% → 11%"
  Else:
    - New prompt saved with is_active = false
    - Old prompt retained
    - Flagged for human review

Step 5 — Next Audit
  Agent team loads active prompt from PromptVariations table
```

---

## Dashboard Metrics View

```
AgentOps — Evaluation Summary
──────────────────────────────────────────────────────

Overall Agent Health
  Finding Validity (precision)    87.4%   ▲ +2.1% from last 10 audits
  Finding Coverage (recall)       83.2%   ▲ +0.8%
  Auto-fix Success Rate           94.1%
  Avg Cost per Audit              $0.18
  Avg Audit Latency               62 sec

Agent Performance
  Repository Analyzer    96%     ████████████░░
  Code Quality Agent     89%     ███████████░░░
  Security Agent         84%     ██████████░░░░  ← below threshold, loop running
  Architecture Agent     91%     ███████████░░░
  Performance Agent      93%     ███████████░░░
  Testing Agent          95%     ████████████░░
  DevOps Agent           97%     ████████████░░
  Documentation Agent    92%     ███████████░░░

Recent Audits
  github.com/user/project-a    COMPLETE    Score: 71/100    $0.16    58s
  github.com/user/project-b    COMPLETE    Score: 88/100    $0.12    44s
  github.com/user/project-c    COMPLETE    Score: 54/100    $0.21    79s

Prompt History — Security Agent
  v3 (active)   F1: 0.87   promoted 1 day ago
  v2            F1: 0.79
  v1            F1: 0.71
```
