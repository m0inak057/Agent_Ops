# Contributing — AgentOps

This guide explains how to extend AgentOps: adding new specialist agents, new MCP tools, new evaluation metrics, or new benchmark repositories.

---

## Adding a New Specialist Agent

**1. Create the agent file**

```python
# agents/your_agent.py

from autogen import AssistantAgent
from agents.tools.github_client import github_tools
from agents.tools.your_mcp_client import your_tools   # if needed

def create_your_agent(llm_config: dict) -> AssistantAgent:
    return AssistantAgent(
        name="your_agent",
        system_message=open("agents/prompts/your_agent.txt").read(),
        llm_config={
            **llm_config,
            "tools": github_tools + your_tools,
        }
    )
```

**2. Write the system prompt**

```
# agents/prompts/your_agent.txt

You are the [Role] Agent in the AgentOps codebase audit team.

Your sole responsibility is: [one clear sentence about what category of issues you find]

You have access to the following tools:
- github_mcp.read_file: read source files to find evidence
- github_mcp.search_code: search patterns across the codebase

You must NOT:
- Report issues you cannot find direct evidence for in the code
- Call tools outside your permitted set
- Modify any files (read only)
- Report the same issue more than once

For every finding you produce, you MUST include:
- The exact file path and line number (if applicable)
- A quote or description of the specific code that is the problem
- Why this matters (impact on the user/system)
- How to fix it

Output each finding as JSON:
{
  "category": "your_category",
  "severity": "critical|high|medium|low",
  "title": "Short, specific title",
  "detail": "Full explanation with evidence, impact, and fix",
  "file_path": "path/to/file.py or null",
  "line_number": 42 or null,
  "confidence": 0.0-1.0,
  "auto_fix_available": true or false
}
```

**3. Register the agent in the team**

```python
# agents/team.py

from agents.your_agent import create_your_agent

your_agent = create_your_agent(llm_config)

groupchat = GroupChat(
    agents=[
        manager, repo_analyzer,
        code_quality, security, architecture,
        performance, testing, devops, documentation,
        your_agent,   # add here
        developer
    ],
    ...
)
```

**4. Add to the Manager's audit plan**

```python
# agents/prompts/manager.txt
# Add your agent to the audit_sequence and parallel_groups
```

**5. Define MCP access permissions**

Update the permissions table in `ARCHITECTURE.md`. Your system prompt must explicitly list what tools the agent may and may not call.

**6. Add to benchmark evaluation**

Add findings from your agent's category to at least one benchmark repository in `evaluation/benchmarks/dataset.json`.

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

**3. Add the MCP client connector**

```python
# agents/tools/your_mcp_client.py

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def call_your_tool(param_one: str) -> str:
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_servers/your_mcp/server.py"]
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("your_tool_name", {"param_one": param_one})
            return result.content[0].text
```

**4. Test the tool directly before connecting to any agent**

```bash
curl -X POST http://localhost:{your_mcp_port}/tools/your_tool_name \
  -H "Content-Type: application/json" \
  -d '{"param_one": "test_value"}'
```

Never connect a new tool to an agent before verifying it works in isolation.

---

## Adding a New Evaluation Metric

**1. Choose the metric category:**
- **Finding-level** (validates individual findings): add to `evaluation/confidence_pipeline.py`
- **Agent-level deterministic** (computed from DB logs): add to `evaluation/metrics/agent_metrics.py`
- **LLM-as-a-Judge** (requires LLM scoring): add to `evaluation/metrics/llm_judge.py`
- **System-level** (latency, cost): add to `evaluation/metrics/system_metrics.py`

**2. Implement the metric**

```python
# evaluation/metrics/your_category.py

def compute_your_metric(audit_data: dict) -> dict:
    """
    Computes [metric name].

    Args:
        audit_data: Dict containing relevant AuditJob, AgentRun,
                    Finding, or ToolExecution data

    Returns:
        Dict with keys: metric (str), score (float), feedback (str or None)
    """
    score = your_calculation(audit_data)

    return {
        "metric": "your_metric_name",
        "score": score,        # float, normalised 0.0–1.0 or raw value
        "feedback": None       # str explanation or None
    }
```

**3. Register in the evaluation framework**

```python
# evaluation/framework.py

from evaluation.metrics.your_category import compute_your_metric

def run_evaluation(audit_id: str) -> list[dict]:
    ...
    metrics.append(compute_your_metric(audit_data))
    ...
```

**4. (Optional) Add to quality gate**

```python
# check_threshold.py

QUALITY_GATE_RULES = {
    ...
    "your_metric_name": {"operator": ">=", "threshold": 0.85},
}
```

---

## Adding a Benchmark Repository

The benchmark dataset lives at `evaluation/benchmarks/dataset.json`. Each entry points to a repository with known, documented issues that agents should find.

```json
{
  "id": "bench_NNN",
  "repo_url": "https://github.com/agentops-benchmarks/your-repo",
  "description": "Brief description of what issues are planted",
  "known_findings": [
    {
      "category": "security",
      "title": "Short title matching what the agent should report",
      "file_path": "path/to/file.py",
      "line_number": 42,
      "severity": "critical|high|medium|low"
    }
  ]
}
```

**Rules for good benchmark repos:**
- Issues must be definitively present — no ambiguous "might be a problem" findings
- Cover at least 3 different categories per repo
- Include at least one issue per severity level
- The repo must be publicly accessible (or accessible with the configured GITHUB_TOKEN)
- Known findings must be specific enough that agent output can be matched against them

---

## Code Standards

- All Python code must pass `flake8` and `black` before committing
- All new MCP tools must have a corresponding manual cURL test documented in the PR
- All new evaluation metrics must have a unit test in `evaluation/tests/`
- System prompts must explicitly state what the agent **cannot** do, not just what it can
- Every finding an agent produces must include file_path, evidence, impact, and a fix recommendation
- Never connect a new tool to an agent before testing it in isolation first

---

## Running Tests Locally

```bash
# Backend unit tests
cd backend && pytest

# Evaluation framework tests
cd evaluation && pytest tests/

# MCP server tests
cd mcp_servers/github_mcp && pytest
cd mcp_servers/filesystem_mcp && pytest
cd mcp_servers/test_mcp && pytest
cd mcp_servers/devops_mcp && pytest

# Full benchmark run
docker compose exec backend python -m evaluation.framework --benchmark
```
