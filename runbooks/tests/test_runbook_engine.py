"""
Tests for RunbookEngine and Runbook definitions.
"""

import sys
import asyncio
from pathlib import Path
import pytest

RUNBOOKS_ROOT = Path(__file__).resolve().parent.parent
if str(RUNBOOKS_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNBOOKS_ROOT))

PROJECT_ROOT = RUNBOOKS_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from runbooks.engine import RunbookEngine


@pytest.fixture
def engine():
    definitions_dir = RUNBOOKS_ROOT / "definitions"
    return RunbookEngine(runbooks_dir=definitions_dir)


def test_runbook_engine_loads_all(engine):
    runbooks = engine.list_runbooks()
    assert len(runbooks) >= 7
    names = [rb["name"] for rb in runbooks]
    assert "Memory Leak Remediation" in names
    assert "Service Crash Remediation" in names
    assert "Disk Exhaustion Remediation" in names
    assert "High CPU Remediation" in names
    assert "Cascading Failure Remediation" in names
    assert "Database Overload Remediation" in names
    assert "Network Degradation Remediation" in names


def test_runbook_validation_no_errors(engine):
    errors = engine.validate()
    assert len(errors) == 0, f"Runbook validation failed with errors: {errors}"


def test_get_runbook_by_failure_type(engine):
    rb = engine.get_runbook("memory_leak")
    assert rb is not None
    assert rb.name == "Memory Leak Remediation"
    assert len(rb.steps) > 0

    rb_crash = engine.get_runbook("service_crash")
    assert rb_crash is not None
    assert rb_crash.name == "Service Crash Remediation"


def test_dry_run_execution(engine):
    result = asyncio.run(
        engine.execute(
            failure_type="service_crash",
            service_name="order-service",
            incident_id="INC-TEST-01",
            risk_score=85.0,
            dry_run=True,
        )
    )
    assert result["status"] == "SUCCESS"
    assert result["runbook"] == "Service Crash Remediation"
    assert len(result["step_results"]) > 0
    for step in result["step_results"]:
        assert step["status"] == "DRY_RUN"


def test_unmapped_failure_type(engine):
    result = asyncio.run(
        engine.execute(
            failure_type="nonexistent_failure",
            service_name="order-service",
            dry_run=True,
        )
    )
    assert result["status"] == "NO_RUNBOOK"
