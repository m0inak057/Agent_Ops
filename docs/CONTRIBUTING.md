# Contributing — AgentOps

This guide explains how to extend AgentOps: switching between unified and specialist audit modes, adding new MCP tools, and adding new evaluation metrics.

---

## Switching Between Unified and Specialist Mode

Today, `backend/services/dispatcher.py` calls exactly one agent module for the audit itself:

```python
# backend/services/dispatcher.py

from agents.manager import synthesise_findings
from agents.repo_analyzer import analyze_repository
from agents.unified_agent import run_unified_audit
...

repo_map = await analyze_repository(audit_job.repo_url)
all_findings = await run_unified_audit(repo_map)          # 1 LLM call, all 7 dimensions
validated_findings = await validate_findings(all_findings, repo_map)
result = await synthesise_findings(validated_findings, repo_map)
```

This is "unified mode" — 1 LLM call per audit, cheap and fast, but each dimension gets shallower attention than a dedicated specialist would give it.

The individual specialist agents (`agents/security.py`, `code_quality.py`, `architecture.py`, `performance.py`, `testing.py`, `devops.py`, `documentation.py`) already exist and work in isolation — each exposes a `run_*_audit(repo_map)` function using the same `call_llm_for_findings` helper as `unified_agent.py`. To re-enable "specialist mode" (7 LLM calls per audit instead of 1):

```python
# backend/services/dispatcher.py — specialist mode

import asyncio
from agents.security import run_security_audit
from agents.code_quality import run_code_quality_audit
from agents.architecture import run_architecture_audit
from agents.performance import run_performance_audit
from agents.testing import run_testing_audit
from agents.devops import run_devops_audit
from agents.documentation import run_documentation_audit

repo_map = await analyze_repository(audit_job.repo_url)

results = await asyncio.gather(
    run_security_audit(repo_map),
    run_code_quality_audit(repo_map),
    run_architecture_audit(repo_map),
    run_performance_audit(repo_map),
    run_testing_audit(repo_map),
    run_devops_audit(repo_map),
    run_documentation_audit(repo_map),
    return_exceptions=True,
)
all_findings = [f for r in results if isinstance(r, list) for f in r]
```

You'd want a matching `AgentRun` row per specialist call instead of the single `unified` row, mirroring what the dispatcher currently does around the `unified_agent` call. This is a real trade-off — before switching, check current evaluation scores in the `evaluations` table (`agent_success_rate`, `average_confidence`) so you have a baseline to compare against after the change.

---

## Adding a New MCP Tool

**1. Create the tool file**

```python
# mcp_servers/your_mcp/tools/your_tool.py

from mcp.server import Server
from mcp.types import Tool, TextContent

def register_your_tool(server: Server):

    @server.list_tools()
    async def list_tools():
        return [
            Tool(
                name="your_tool_name",
                description="What this tool does — be specific so agents use it correctly",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "param_one": {
                            "type": "string",
                            "description": "What this parameter is and what values are valid"
                        }
                    },
                    "required": ["param_one"]
                }
            )
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        if name == "your_tool_name":
            result = do_something(arguments["param_one"])
            return [TextContent(type="text", text=str(result))]
```

**2. Register in the MCP server**

```python
# mcp_servers/your_mcp/server.py

from mcp_servers.your_mcp.tools.your_tool import register_your_tool
register_your_tool(server)
```

**3. Add or extend the MCP client connector**

Follow the pattern in `agents/tools/github_client.py`: open one `stdio_client` session per logical unit of work (e.g. per repo analysis) rather than spawning a fresh subprocess per tool call, and expose thin async wrapper functions that call `session.call_tool(...)` and parse the JSON result.

**4. Test the tool directly before connecting it to any agent**

Each MCP server exposes an HTTP `/health` check via Docker Compose, but the tools themselves are called over MCP stdio, not HTTP. Write a small standalone script that opens a session and calls the tool directly, and confirm the output shape before wiring it into an agent module.

---

## Adding a New Evaluation Metric

**1. Choose the metric category:**
- **Finding-level rule** (validates individual findings before they're persisted): add to `evaluation/confidence_pipeline.py`
- **Agent-level deterministic** (computed from `agent_runs`): add to `evaluation/metrics/agent_metrics.py`
- **Finding-level deterministic** (computed from `findings`): add to `evaluation/metrics/finding_metrics.py`
- **System-level deterministic** (computed from `audit_jobs`): add to `evaluation/metrics/system_metrics.py`
- **LLM-as-a-Judge** (requires an LLM call): add to `evaluation/metrics/llm_judge.py` — be mindful this is the second and last LLM call in the whole pipeline; don't add a second judge call without good reason

**2. Implement the metric**

Each metric function returns a list of dicts shaped like:

```python
{
    "metric": "your_metric_name",
    "score": 0.0,          # float
    "feedback": None,      # str explanation or None
}
```

Follow the existing pattern in `evaluation/metrics/*.py`: wrap the whole function body in a try/except that logs and returns `[]` on failure, since `evaluation/framework.py::run_evaluation` must never let a single metric group's failure block the others.

**3. It's picked up automatically**

`evaluation/framework.py::run_evaluation` already calls all four metric groups via `asyncio.gather` and persists whatever they return as `Evaluation` rows. If you add a function to an existing metrics module, no further registration is needed. If you add a new metrics *module*, import and call it from `run_evaluation` alongside the existing four.

**4. (Optional) Add to the quality gate**

```python
# check_threshold.py

QUALITY_GATE_RULES = {
    ...
    "your_metric_name": {"operator": ">=", "threshold": 0.85},
}
```

---

## Adding a Benchmark Case

`evaluation/benchmarks/dataset.json` is currently empty (`"cases": []`). Each case should point to a repository with known, documented issues:

```json
{
  "id": "bench_001",
  "repo_url": "https://github.com/agentops-benchmarks/your-repo",
  "description": "Brief description of what issues are planted",
  "known_findings": [
    {
      "category": "security",
      "title": "Short title matching what the agent should report",
      "file_path": "path/to/file.py",
      "line_number": 42,
      "severity": "critical"
    }
  ]
}
```

`evaluation/seed_benchmarks.py` loads this file into the database. There is currently no automated scoring pipeline that runs the audit against these cases and compares output — that would be a good next contribution alongside populating real cases.

---

## Code Standards

- All Python code must pass `flake8` and `black` before committing (enforced in `.github/workflows/ci.yml`)
- Every finding a metric or agent produces should include enough context (title, detail, evidence) to be independently checkable
- Metric and pipeline functions must not raise — they should log and return an empty result on failure, matching the existing pattern throughout `evaluation/`
- Test new MCP tools in isolation before wiring them into any agent module

---

## Running Tests Locally

```bash
# Backend unit tests
cd backend && pytest

# Evaluation framework tests
cd evaluation && pytest tests/

# All tests from repo root
pytest backend/tests evaluation/tests
```

11 tests currently pass across both suites.
