"""FastAPI application entrypoint for the AgentOps backend.

Wires together the API routers (audits, findings, evaluations, fixes),
application startup/shutdown lifecycle, and middleware.
"""

from fastapi import FastAPI

app = FastAPI(title="AgentOps", description="AI-powered autonomous codebase auditor")


@app.get("/health")
async def health_check():
    """Return service health status."""
    pass
