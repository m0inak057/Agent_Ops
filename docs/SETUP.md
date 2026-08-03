# Setup Guide — AgentOps

This guide walks you through running the full AgentOps stack locally using Docker Compose.

---

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Docker | ≥ 24.0 | https://docs.docker.com/get-docker/ |
| Docker Compose | ≥ 2.20 | Included with Docker Desktop |
| Python | ≥ 3.11 | https://python.org (only needed for running services outside Docker) |
| Node.js | ≥ 20 | https://nodejs.org (only needed for running the frontend outside Docker) |
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

These match `.env.example` exactly:

```env
# --- Database ---
POSTGRES_USER=agentops
POSTGRES_PASSWORD=              # Required — set a strong password, no default
POSTGRES_DB=agentops
DATABASE_URL=postgresql+asyncpg://agentops:<POSTGRES_PASSWORD>@db:5432/agentops

# --- Redis ---
REDIS_URL=redis://redis:6379/0   # Internal container port; host-mapped to 6380 (see docker-compose.yml)

# --- LLM Providers ---
OPENAI_API_KEY=                 # Required — used against OPENAI_BASE_URL (e.g. an OpenRouter key)
ANTHROPIC_API_KEY=              # Optional — not currently wired into any call path
OPENAI_BASE_URL=                # OpenAI-compatible endpoint, e.g. https://openrouter.ai/api/v1
AUTOGEN_MODEL=                  # Model id passed to the chat completions call, e.g. an OpenRouter model slug

# --- Observability ---
LANGFUSE_PUBLIC_KEY=            # Not currently used by any code path
LANGFUSE_SECRET_KEY=            # Not currently used by any code path
LANGFUSE_HOST=https://cloud.langfuse.com
OTEL_EXPORTER_OTLP_ENDPOINT=    # Not currently used by any code path

# --- GitHub Integration ---
GITHUB_TOKEN=                   # Required — used by github_mcp to read repos (and open PRs once auto-fix is wired)
GITHUB_APP_ID=                  # Optional, unused today
GITHUB_APP_PRIVATE_KEY=         # Optional, unused today

# --- MCP Server URLs ---
GITHUB_MCP_URL=http://github_mcp:8001
FILESYSTEM_MCP_URL=http://filesystem_mcp:8002
TEST_MCP_URL=http://test_mcp:8003
DEVOPS_MCP_URL=http://devops_mcp:8004

# --- Webhooks ---
WEBHOOK_SECRET=your-webhook-secret-here   # Verifies GitHub's X-Hub-Signature-256 header; if unset, signature check is skipped

# --- Backend ---
BACKEND_PORT=8000
ENVIRONMENT=development         # development | staging | production
LOG_LEVEL=INFO
SECRET_KEY=                     # Required — used for signing/session security

# --- Evaluation ---
EVAL_CONFIDENCE_THRESHOLD=0.7   # Reference threshold; the enforced gate rules live in check_threshold.py

# --- CORS ---
ALLOWED_ORIGINS=http://localhost:3000

# --- Frontend ---
NEXT_PUBLIC_API_URL=http://localhost:8000
```

> `OPENAI_API_KEY` and `OPENAI_BASE_URL` together are how AgentOps talks to an LLM — point `OPENAI_BASE_URL` at OpenRouter (or any OpenAI-compatible provider) and set `AUTOGEN_MODEL` to that provider's model id.

---

## Step 3 — Start the Stack

```bash
docker compose up --build
```

This starts:
- PostgreSQL on host port 5432
- Redis on host port **6380** (mapped from container port 6379 — chosen to avoid conflicting with a local Redis instance; internal container-to-container traffic still uses 6379)
- FastAPI backend on port 8000
- github_mcp server on port 8001
- filesystem_mcp server on port 8002 (standby — not called during an audit)
- test_mcp server on port 8003 (standby — not called during an audit)
- devops_mcp server on port 8004 (standby — not called during an audit)
- Next.js frontend on port 3000

Wait for all services to show `healthy` in Docker logs before proceeding. Each service has a `/health` check defined in `docker-compose.yml`.

All MCP servers work automatically as part of the audit pipeline (or sit standby, in the case of `filesystem_mcp`/`test_mcp`/`devops_mcp`) — there's no manual step needed to connect them to agents.

---

## Step 4 — Initialize the Database

The backend runs `init_db()` automatically on startup (see `backend/main.py`), creating tables from the SQLAlchemy models if they don't exist. No separate migration step is required for a fresh local setup, though Alembic migrations exist under `backend/alembic/` if you need to evolve the schema.

---

## Step 5 — Verify Everything Is Running

```bash
# Backend health check
curl http://localhost:8000/health
# Expected: {"status": "ok", "db": "connected", "version": "0.1.0"}

# MCP server health checks
curl http://localhost:8001/health    # github_mcp
curl http://localhost:8002/health    # filesystem_mcp
curl http://localhost:8003/health    # test_mcp
curl http://localhost:8004/health    # devops_mcp

# Webhook health check
curl http://localhost:8000/api/webhooks/health

# Open the dashboard
open http://localhost:3000
```

---

## Step 6 — Submit Your First Audit

Via the dashboard UI, or directly via the API:

```bash
curl -X POST http://localhost:8000/api/audits -H "Content-Type: application/json" -d "{\"repo_url\": \"https://github.com/your-username/your-project\"}"
```

(Single-line form above so it runs unmodified in both PowerShell and bash/Git Bash on Windows.)

Response:
```json
{
  "audit_id": "uuid",
  "status": "pending",
  "repo_url": "https://github.com/your-username/your-project",
  "repo_name": "your-username/your-project"
}
```

Poll `GET /api/audits/{audit_id}` until `status` is `complete`, then fetch findings:

```bash
curl http://localhost:8000/api/findings/{audit_id}
curl http://localhost:8000/api/findings/{audit_id}/summary
curl http://localhost:8000/api/evaluations/{audit_id}
```

An audit makes 2 LLM calls total and typically completes in well under a minute, though this depends entirely on the LLM provider's latency.

---

## Running Without Docker (Development Mode)

```bash
# Terminal 1 — PostgreSQL + Redis (still use Docker for these)
docker compose up db redis

# Terminal 2 — Backend
cd backend
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000

# Terminal 3 — github_mcp (spawned automatically by repo_analyzer.py over stdio;
# only run it standalone if you need to test it directly)
python mcp_servers/github_mcp/server.py

# Terminal 4 — Frontend
cd frontend
npm install
npm run dev
```

---

## Setting Up GitHub Webhook (Continuous Monitoring)

To enable automatic re-auditing on every push to `main` or `master`:

1. Go to your repository → Settings → Webhooks → Add webhook
2. Payload URL: `https://your-agentops-domain.com/api/webhooks/github`
3. Content type: `application/json`
4. Secret: the value you set in `WEBHOOK_SECRET`
5. Events: select "Push"

AgentOps verifies the `X-Hub-Signature-256` header (skipped if `WEBHOOK_SECRET` is empty), ignores non-`push` events and pushes to branches other than main/master, and skips re-triggering if an audit was already created for that repo in the last 5 minutes.

---

## Common Issues

**`github_mcp` returns an error / repo not found**
Your `GITHUB_TOKEN` may lack access, or the repo may be private. Generate a token at https://github.com/settings/tokens with `repo` read scope.

**LLM call fails or returns no findings**
Check `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `AUTOGEN_MODEL` are all set correctly. `agents/_llm_common.py` retries up to 3 times and logs failures, then returns an empty finding list rather than crashing the audit — check backend logs if an audit completes with 0 findings.

**`DATABASE_URL connection refused`**
PostgreSQL container isn't ready yet. `docker-compose.yml` has the backend wait on the db healthcheck, but if running components manually, wait 10–15 seconds after `docker compose up db` before starting the backend.

**Auto-fix approval returns 400**
`POST /api/fixes/{finding_id}/approve` requires `auto_fix_available = true` and `confidence >= 0.95`. Note that even an approved fix currently only logs — it does not yet write code or open a PR (see [ROADMAP.md](./ROADMAP.md)).

---

## Resetting the Database

```bash
docker compose down -v      # Removes volumes including DB data
docker compose up --build   # Starts fresh — tables are recreated on backend startup
```

---

## Project Ports Reference

| Service | Host Port | Container Port |
|---|---|---|
| Frontend (Next.js) | 3000 | 3000 |
| Backend (FastAPI) | 8000 | 8000 |
| github_mcp | 8001 | 8001 |
| filesystem_mcp | 8002 | 8002 |
| test_mcp | 8003 | 8003 |
| devops_mcp | 8004 | 8004 |
| PostgreSQL | 5432 | 5432 |
| Redis | **6380** | 6379 |
