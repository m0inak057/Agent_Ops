"""Tests for the manager agent synthesis logic."""

import pytest

from agents.manager import synthesise_findings


@pytest.mark.asyncio
async def test_synthesise_empty_findings():
    """Empty findings should return health score 100."""
    result = await synthesise_findings([], {})
    assert result["health_score"] == 100
    assert result["summary"]["total"] == 0


@pytest.mark.asyncio
async def test_synthesise_deduplication():
    """Duplicate titles should be deduplicated keeping highest confidence."""
    findings = [
        {
            "agent_role": "security",
            "category": "security",
            "severity": "critical",
            "title": "Hardcoded secret",
            "detail": "JWT key hardcoded in auth.py line 47",
            "file_path": "auth.py",
            "line_number": 47,
            "confidence": 0.99,
            "auto_fix_available": True,
        },
        {
            "agent_role": "security",
            "category": "security",
            "severity": "critical",
            "title": "Hardcoded secret",
            "detail": "JWT key hardcoded in auth.py line 47",
            "file_path": "auth.py",
            "line_number": 47,
            "confidence": 0.75,
            "auto_fix_available": True,
        },
    ]
    result = await synthesise_findings(findings, {})
    assert result["summary"]["total"] == 1
    assert result["findings"][0]["confidence"] == 0.99


@pytest.mark.asyncio
async def test_health_score_calculation():
    """Health score should decrease correctly per severity."""
    findings = [
        {
            "agent_role": "security",
            "category": "security",
            "severity": "critical",
            "title": "Issue 1",
            "detail": "Critical security issue found in the codebase",
            "file_path": None,
            "line_number": None,
            "confidence": 0.99,
            "auto_fix_available": False,
        },
        {
            "agent_role": "devops",
            "category": "devops",
            "severity": "high",
            "title": "Issue 2",
            "detail": "High severity devops issue found",
            "file_path": None,
            "line_number": None,
            "confidence": 0.90,
            "auto_fix_available": False,
        },
    ]
    result = await synthesise_findings(findings, {})
    # 100 - 12 (critical) - 6 (high) = 82
    assert result["health_score"] == 82


@pytest.mark.asyncio
async def test_severity_sort_order():
    """Critical findings should appear before high, medium, low."""
    findings = [
        {
            "agent_role": "testing",
            "category": "testing",
            "severity": "low",
            "title": "Low issue",
            "detail": "Low severity testing issue",
            "file_path": None,
            "line_number": None,
            "confidence": 0.80,
            "auto_fix_available": False,
        },
        {
            "agent_role": "security",
            "category": "security",
            "severity": "critical",
            "title": "Critical issue",
            "detail": "Critical security vulnerability found",
            "file_path": None,
            "line_number": None,
            "confidence": 0.99,
            "auto_fix_available": False,
        },
    ]
    result = await synthesise_findings(findings, {})
    assert result["findings"][0]["severity"] == "critical"
    assert result["findings"][1]["severity"] == "low"
