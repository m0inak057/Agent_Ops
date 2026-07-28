"""FastAPI application entrypoint for the AgentOps backend.

Wires together the API routers (audits, findings, evaluations, fixes),
application startup/shutdown lifecycle, and middleware.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from backend.api import audits, evaluations, findings, fixes
from backend.api.webhooks import router as webhooks_router
from backend.db import SessionLocal, init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

API_VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize the database schema on application startup."""
    await init_db()
    yield


app = FastAPI(title="AgentOps API", version=API_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(audits.router, prefix="/api")
app.include_router(findings.router, prefix="/api")
app.include_router(evaluations.router, prefix="/api")
app.include_router(fixes.router, prefix="/api")
app.include_router(webhooks_router)


@app.get("/health")
async def health_check() -> dict:
    """Report service health, including database connectivity."""
    db_status = "connected"
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Database connectivity check failed")
        db_status = "disconnected"

    return {"status": "ok", "db": db_status, "version": API_VERSION}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch unhandled exceptions and return a generic 500 response."""
    logger.exception(
        "Unhandled exception while processing %s %s", request.method, request.url
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
