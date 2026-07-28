import pytest

from evaluation.confidence_pipeline import validate_single_finding


@pytest.mark.asyncio
async def test_finding_with_good_evidence():
    finding = {
        "agent_role": "security",
        "category": "security",
        "severity": "critical",
        "title": "Hardcoded JWT secret key",
        "detail": (
            "The file auth.py contains a hardcoded JWT secret key on line 47. This allows "
            "anyone with repository access to forge authentication tokens. Move to "
            "environment variable."
        ),
        "file_path": None,
        "line_number": 47,
        "confidence": 0.99,
        "auto_fix_available": True,
    }
    repo_map = {
        "project_type": "Django REST API",
        "file_tree": ["auth.py", "models.py", "views.py"],
    }
    result = await validate_single_finding(finding, repo_map)
    # Should not be discarded (confidence is high)
    assert result is not None
    assert result["confidence"] > 0.40


@pytest.mark.asyncio
async def test_finding_with_vague_detail():
    finding = {
        "agent_role": "code_quality",
        "category": "code_quality",
        "severity": "low",
        "title": "Bad code",
        "detail": "Code is bad",
        "file_path": None,
        "line_number": None,
        "confidence": 0.30,
        "auto_fix_available": False,
    }
    repo_map = {
        "project_type": "FastAPI",
        "file_tree": [],
    }
    result = await validate_single_finding(finding, repo_map)
    # Should be discarded — confidence below 0.40 after evidence check
    assert result is None


def test_quality_gate_rules_exist():
    import sys

    sys.path.insert(0, ".")
    # Just verify check_threshold.py is importable and has rules
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "check_threshold", "check_threshold.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "QUALITY_GATE_RULES")
    assert len(mod.QUALITY_GATE_RULES) > 0
    print("Quality gate rules verified")
