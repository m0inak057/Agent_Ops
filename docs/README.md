# AgentOps 🤖

> **AI-Powered Autonomous Codebase Auditor & Engineering Assistant**

AgentOps is a production-style LLMOps platform where a coordinated team of AI agents autonomously investigates an entire GitHub repository — identifying bugs, security vulnerabilities, performance bottlenecks, architectural problems, testing gaps, and DevOps issues — explains why they matter, prioritises them by severity and confidence, and optionally fixes high-confidence issues by creating a Pull Request.

**The core value proposition:**
> "You don't need to know what's wrong with your project. AgentOps investigates it for you."

This is not a demo. Every finding includes evidence, severity, and a confidence score. Findings below the confidence threshold are never auto-fixed. The agents themselves are continuously evaluated through a CI/CD quality gate.

---

## The Problem It Solves

Solo developers and small teams build projects without a senior engineer looking over their shoulder. They push code with hardcoded secrets, N+1 queries, no tests on critical paths, and Docker containers running as root — not because they don't care, but because they don't know.

AgentOps is that senior engineer. Point it at your repository and it tells you exactly what's wrong, why it matters, and how to fix it.

---

## Live Demo Flow

```
User pastes: https://github.com/username/my-project
```

**Step 1 — Repository Understanding**
```
Project Type:     Django + React
Languages:        Python, JavaScript
Database:         PostgreSQL
Infrastructure:   Docker
Testing:          pytest
CI/CD:            None detected
Dependencies:     42
Files:            137
Lines of Code:    28,431
```

**Step 2 — 7 Specialist Agents audit in parallel**

```
Manager Agent
      │
      ▼
Repository Analyzer
      │
      ├── Code Quality Agent
      ├── Security Agent        (+ Bandit, Semgrep, Trivy)
      ├── Architecture Agent
      ├── Performance Agent
      ├── Testing Agent
      ├── DevOps Agent
      └── Documentation Agent
      │
      ▼
Manager synthesises all findings
      │
      ▼
Evaluation Pipeline validates confidence of every finding
      │
      ▼
Health Report delivered
```

**Step 3 — You receive a Health Report**
```
PROJECT HEALTH SCORE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Overall:          71 / 100

Security          82
Code Quality      76
Architecture      68
Performance       61
Testing           43
DevOps            58
Documentation     81

🔴 CRITICAL — Fix Immediately
  1. JWT secret hardcoded in users/auth.py (Confidence: 99%)
  2. SQL injection risk in search/views.py (Confidence: 94%)

🟠 HIGH — Fix Soon
  3. N+1 query on every orders request (Confidence: 96%)
  4. Payment processing has 0% test coverage (Confidence: 91%)
  5. Docker container runs as root (Confidence: 98%)

🟡 MEDIUM
  6. No CI/CD pipeline configured
  7. Cyclomatic complexity 18 in checkout.py
  8. API endpoints undocumented
```

**Step 4 — Optional: Auto-fix high-confidence issues**
```
Issue #1 — Hardcoded JWT Secret   Confidence: 99%
[Explain]  [Show Code]  [Fix Automatically]

→ Developer Agent writes fix to sandbox
→ Test Agent verifies nothing breaks
→ Pull Request created on your repository
```

---

## Architecture Overview

```
User pastes GitHub repo URL
            │
            ▼
     FastAPI Backend
     (event dispatcher)
            │
            ▼
   AutoGen Multi-Agent Team
            │
     ┌──────┴──────┐
     │             │
     ▼             ▼
Repository    7 Specialist
 Analyzer       Agents
     │             │
     └──────┬──────┘
            │
     Manager synthesises
            │
   Evaluation Pipeline
   (confidence scoring)
            │
       ┌────┴────┐
       │         │
    Report    Auto-fix
       │         │
       ▼         ▼
   Dashboard   PR on
              GitHub
```

> Agents never access external systems directly. All interactions go through isolated **MCP Servers** that expose controlled, typed tools.

---

## Confidence Threshold System

Every finding goes through the evaluation pipeline before reaching the user.

```
Confidence > 95%  →  Auto-fix allowed
85% – 95%         →  Suggest fix, requires user approval
< 85%             →  Explain and show evidence only, no auto-fix
```

This is AI evaluation as a core product feature, not a checkbox.

---

## Key Features

| Feature | Description |
|---|---|
| **Multi-Agent Audit** | 7 specialist agents cover code quality, security, architecture, performance, testing, DevOps, and documentation |
| **Confidence-Gated Fixes** | Findings below confidence threshold are never auto-fixed |
| **MCP Tool Architecture** | Agents interact with GitHub, filesystem, test runners, and DevOps tools via isolated MCP servers |
| **Static Analysis Integration** | Security Agent runs Bandit, Semgrep, and Trivy — LLM interprets results in context |
| **AI Evaluation Framework** | LLM-as-a-Judge + deterministic metrics validate every agent finding |
| **CI/CD Quality Gate** | GitHub Actions blocks deployment if agent quality degrades |
| **Self-Improvement Loop** | Failed evaluation triggers automated prompt optimisation and benchmarking |
| **Real-Time Dashboard** | Live audit progress, health scores, finding history, agent performance |
| **Continuous Monitoring (V5)** | GitHub webhook re-audits on every commit and notifies of new issues |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js, TypeScript, Tailwind CSS, Shadcn UI |
| Backend | FastAPI, PostgreSQL, Redis |
| Agents | Microsoft AutoGen, Python MCP SDK |
| Static Analysis | Bandit, Semgrep, Trivy, Flake8 |
| Evaluation | Custom framework, LLM-as-a-Judge, RAGAS |
| Observability | OpenTelemetry, Langfuse |
| Infrastructure | Docker, Docker Compose, GitHub Actions |
| Deployment | AWS / GCP |

---

## Repository Structure

```
agentops/
├── frontend/                 # Next.js dashboard
├── backend/                  # FastAPI orchestrator, DB models, API routes
├── agents/                   # AutoGen agent configs and workflows
│   ├── prompts/              # System messages per agent role
│   └── tools/                # MCP client connectors
├── mcp_servers/              # Isolated MCP tool servers
│   ├── github_mcp/           # Clone, read, branch, commit, PR
│   ├── filesystem_mcp/       # Secure sandbox file operations
│   ├── test_mcp/             # Pytest, coverage, Bandit, Semgrep, Trivy
│   └── devops_mcp/           # Docker inspection, CI/CD pipeline checks
├── evaluation/               # Evaluation framework and benchmark datasets
├── infrastructure/           # Dockerfiles
├── .github/workflows/        # CI/CD pipelines and quality gates
└── docker-compose.yml
```

For a detailed breakdown of every folder, see [ARCHITECTURE.md](./ARCHITECTURE.md).

---

## Documentation Index

| File | What It Covers |
|---|---|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Folder structure, data flow, MCP design, DB schema, confidence system |
| [AGENTS.md](./AGENTS.md) | Each agent's role, tools, inputs, outputs, and prompt strategy |
| [EVALUATION.md](./EVALUATION.md) | Full evaluation framework: metrics, LLM-as-a-Judge, quality gate, self-improvement |
| [SETUP.md](./SETUP.md) | Local dev setup, environment variables, Docker, running the stack |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | How to add new agents, MCP tools, or evaluation metrics |
| [ROADMAP.md](./ROADMAP.md) | 5-version implementation plan with weekly milestones |

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/agentops.git
cd agentops

# Copy environment variables
cp .env.example .env
# Fill in your API keys (see SETUP.md)

# Start the full stack
docker compose up --build

# Access the dashboard
open http://localhost:3000
```

Full setup instructions: [SETUP.md](./SETUP.md)

---

## Why This Project Exists

Built to demonstrate production-grade skills across:

- Multi-agent AI systems (AutoGen)
- MCP server design and implementation
- AI evaluation, confidence scoring, and LLMOps
- CI/CD pipeline engineering with AI quality gates
- Static analysis tool integration
- Full-stack development
- Docker and cloud deployment

This project targets roles in **LLMOps**, **AI Engineering**, and **Full-Stack AI** development.
