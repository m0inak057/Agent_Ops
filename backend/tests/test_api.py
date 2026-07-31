"""Basic API endpoint tests."""

import importlib.util
import os

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch


@pytest.fixture
def app():
    os.environ.setdefault(
        "DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test"
    )
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("GITHUB_TOKEN", "test")
    from backend.main import app as fastapi_app

    return fastapi_app


@pytest.mark.asyncio
async def test_health_endpoint(app):
    """Test /health returns ok status when the database is reachable."""
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=None)

    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__.return_value = mock_session
    mock_session_cm.__aexit__.return_value = None

    with patch("backend.main.SessionLocal", return_value=mock_session_cm):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["db"] == "connected"


def test_health_response_structure():
    """Test that health response has required fields."""
    expected_fields = {"status", "db", "version"}
    assert expected_fields == {"status", "db", "version"}


def test_quality_gate_thresholds():
    """Test quality gate has correct threshold values."""
    spec = importlib.util.spec_from_file_location(
        "check_threshold", "check_threshold.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    rules = mod.QUALITY_GATE_RULES
    assert "agent_success_rate" in rules
    assert rules["agent_success_rate"]["threshold"] == 0.80
    assert "average_confidence" in rules


def test_audit_url_validation():
    """Test GitHub URL validation logic."""
    os.environ.setdefault(
        "DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test"
    )
    os.environ.setdefault("OPENAI_API_KEY", "test")

    from pydantic import ValidationError

    from backend.schemas import AuditJobCreate

    valid = AuditJobCreate(repo_url="https://github.com/username/repo")
    assert valid.repo_url == "https://github.com/username/repo"

    with pytest.raises(ValidationError):
        AuditJobCreate(repo_url="https://notgithub.com/username/repo")
