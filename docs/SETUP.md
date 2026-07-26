# Setup Guide — AgentOps

This guide walks you through running the full AgentOps stack locally using Docker Compose.

---

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Docker | ≥ 24.0 | https://docs.docker.com/get-docker/ |
| Docker Compose | ≥ 2.20 | Included with Docker Desktop |
| Python | ≥ 3.11 | https://python.org |
| Node.js | ≥ 20 | https://nodejs.org |
| Git | Any | https://git-scm.com |

---

## Step 1 — Clone and Configure

```bash
git clone https://github.com/yourusername/agentops.git
cd agentops

# Copy the environment template
cp .env.example .env
```

Open `.env` and fill in the required values. See the Environment Variables section below.

---

## Step 2 — Environment Variables

```env
# ── LLM ────────────────────────────────────────────
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...         # Used for LLM-as-a-Judge in evaluation pipeline
AUTOGEN_MODEL=gpt-4o                 # Model used by AutoGen agents

# ── GitHub ─────────────────────────────────────────
GITHUB_TOKEN=ghp_...                 # Personal access token with repo scope (read)
                                     # Needs write scope only for auto-fix PR creation

# ── Database ────────────────────────────────────────
POSTGRES_USER=agentops
POSTGRES_PASSWORD=changeme
POSTGRES_DB=agentops
DATABASE_URL=postgresql://agentops:changeme@db:5432/agentops

# ── Redis ───────────────────────────────────────────
REDIS_URL=redis://redis:6379/0

# ── Observability ────────────────────────────────────
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com

# ── MCP Servers ─────────────────────────────────────
FILESYSTEM_SANDBOX_PATH=/sandbox     # Root path agents can write to during auto-fix
GITHUB_MCP_PORT=8001
FILESYSTEM_MCP_PORT=8002
TEST_MCP_PORT=8003
DEVOPS_MCP_PORT=8004

# ── Backend ─────────────────────────────────────────
BACKEND_PORT=8000
FRONTEND_PORT=3000

# ── Evaluation ──────────────────────────────────────
CONFIDENCE_THRESHOLD_AUTOFIX=0.95    # Minimum confidence for auto-fix to be offered
CONFIDENCE_THRESHOLD_SUGGEST=0.85    # Minimum confidence for suggested fix
QUALITY_GATE_FINDING_VALIDITY=0.85   # Minimum finding accuracy to pass CI gate
QUALITY_GATE_FINDING_COVERAGE=0.80   # Minimum recall to pass CI gate

# ── GitHub Webhook (V5 — continuous monitoring) ─────
WEBHOOK_SECRET=your-webhook-secret   # Set in GitHub repo settings
```

---

## Step 3 — Start the Stack

```bash
docker compose up --build
```

This starts:
- PostgreSQL database on port 5432
- Redis on port 6379
- FastAPI backend on port 8000
- github_mcp server on port 8001
- filesystem_mcp server on port 8002
- test_mcp server on port 8003
- devops_mcp server on port 8004
- Next.js frontend on port 3000

Wait for all services to show `healthy` in Docker logs before proceeding.

---

## Step 4 — Initialize the Database

```bash
# Run database migrations
docker compose exec backend alembic upgrade head

# Seed the benchmark dataset
docker compose exec backend python -m evaluation.seed_benchmarks
```

---

## Step 5 — Verify Everything Is Running

```bash
# Backend health check
curl http://localhost:8000/health
# Expected: {"status": "ok", "db": "connected", "redis": "connected"}

# MCP server health checks
curl http://localhost:8001/health    # github_mcp
curl http://localhost:8002/health    # filesystem_mcp
curl http://localhost:8003/health    # test_mcp
curl http://localhost:8004/health    # devops_mcp

# Open the dashboard
open http://localhost:3000
```

---

## Step 6 — Submit Your First Audit

Via the dashboard UI or directly via API:

```bash
curl -X POST http://localhost:8000/api/audits \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/your-username/your-project"
  }'
```

Response:
```json
{
  "audit_id": "uuid",
  "status": "pending",
  "repo_url": "https://github.com/your-username/your-project"
}
```

The audit will appear in the dashboard immediately and update in real time via WebSocket as agents complete their analysis. A typical audit takes 45–90 seconds.

---

## Running Without Docker (Development Mode)

```bash
# Terminal 1 — PostgreSQL + Redis (still use Docker for these)
docker compose up db redis

# Terminal 2 — Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Terminal 3 — github_mcp
cd mcp_servers/github_mcp
pip install -r requirements.txt
python server.py

# Terminal 4 — filesystem_mcp
cd mcp_servers/filesystem_mcp
pip install -r requirements.txt
python server.py

# Terminal 5 — test_mcp
cd mcp_servers/test_mcp
pip install -r requirements.txt
python server.py

# Terminal 6 — devops_mcp
cd mcp_servers/devops_mcp
pip install -r requirements.txt
python server.py

# Terminal 7 — Frontend
cd frontend
npm install
npm run dev
```

---

## Running the Evaluation Benchmark

To evaluate agent accuracy against the benchmark dataset:

```bash
docker compose exec backend python -m evaluation.framework --benchmark
```

Output:
```
Running benchmark on 3 repositories (15 known issues)...

Repo bench_001   Found: 5/5    Precision: 0.91   Recall: 1.00   F1: 0.95
Repo bench_002   Found: 3/4    Precision: 0.88   Recall: 0.75   F1: 0.81
Repo bench_003   Found: 4/6    Precision: 0.80   Recall: 0.67   F1: 0.73

Benchmark Summary
─────────────────────────────────────
Total Known Issues:    15
Found:                 12   (80.0%)
False Positives:        2   (11.8%)
Overall Precision:     0.86
Overall Recall:        0.80
Overall F1:            0.83
Avg Cost per Audit:    $0.17
Avg Latency:           58s

Quality Gate: PASS ✓
```

---

## Setting Up GitHub Webhook (V5 — Continuous Monitoring)

To enable automatic re-auditing on every commit:

1. Go to your repository → Settings → Webhooks → Add webhook
2. Payload URL: `https://your-agentops-domain.com/api/webhooks/github`
3. Content type: `application/json`
4. Secret: the value you set in `WEBHOOK_SECRET`
5. Events: select "Push" and "Pull requests"

AgentOps will now automatically re-audit your repository on every push and notify you of new issues introduced by the commit.

---

## Common Issues

**`github_mcp: 401 Unauthorized`**
Your `GITHUB_TOKEN` doesn't have the required `repo` scope. Generate a new token at https://github.com/settings/tokens with at least `repo:read`. Add `repo:write` if you want auto-fix PR creation.

**`github_mcp: Repository not found`**
The repo may be private. Ensure your `GITHUB_TOKEN` belongs to an account with access to the repository.

**`test_mcp: bandit not found`**
Bandit is installed inside the test_mcp Docker container. If running without Docker, install manually: `pip install bandit semgrep`.

**`devops_mcp: docker not found`**
The devops_mcp server needs Docker available to inspect Dockerfiles. When running in Docker Compose this is handled automatically via volume mount.

**`DATABASE_URL connection refused`**
PostgreSQL container isn't ready yet. Wait 10–15 seconds after `docker compose up` before running migrations.

**`filesystem_mcp: path outside sandbox`**
The Developer Agent (auto-fix) tried to write outside `FILESYSTEM_SANDBOX_PATH`. This is the security boundary working correctly. All auto-fix writes are sandboxed.

---

## Resetting the Database

```bash
docker compose down -v      # Removes volumes including DB data
docker compose up --build   # Starts fresh
docker compose exec backend alembic upgrade head
docker compose exec backend python -m evaluation.seed_benchmarks
```

---

## Project Ports Reference

| Service | Port | URL |
|---|---|---|
| Frontend (Next.js) | 3000 | http://localhost:3000 |
| Backend (FastAPI) | 8000 | http://localhost:8000/docs |
| github_mcp | 8001 | http://localhost:8001 |
| filesystem_mcp | 8002 | http://localhost:8002 |
| test_mcp | 8003 | http://localhost:8003 |
| devops_mcp | 8004 | http://localhost:8004 |
| PostgreSQL | 5432 | localhost:5432 |
| Redis | 6379 | localhost:6379 |
