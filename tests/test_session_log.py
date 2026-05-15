# ABOUTME: Tests for session log enrichment (100.2) — SR beat decision, checks, rulings, plan writes.
# ABOUTME: Verifies that each turn phase appends structured entries to state/session_log.md.

import pytest
from pathlib import Path
from unittest.mock import patch


def test_beat_prompt_no_longer_exists():
    """_beat_prompt is removed in 100.2; no code path should expose it."""
    import showrunner.orchestrator as orch
    assert not hasattr(orch, "_beat_prompt"), "_beat_prompt should be removed in 100.2"


def test_verbose_flag_rejected_by_cli(monkeypatch, capsys):
    """CLI should reject --verbose since it's removed in 100.2."""
    from showrunner.main import main
    import sys
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(sys, "argv", ["showrunner", "--verbose"])
    with pytest.raises(SystemExit) as exc_info:
        main()
    # argparse exits with code 2 for unrecognised arguments
    assert exc_info.value.code == 2


def test_session_log_sr_decision_written(tmp_path):
    """_write_session_log_sr_decision writes STAY or ADVANCE entry to session_log.md."""
    from showrunner.orchestrator import _write_session_log_sr_decision
    log = tmp_path / "session_log.md"
    _write_session_log_sr_decision(log, beat_id="intro", decision=False, next_id=None)
    content = log.read_text()
    assert "STAY" in content
    assert "intro" in content


def test_session_log_sr_advance_written(tmp_path):
    """_write_session_log_sr_decision writes ADVANCE with target beat."""
    from showrunner.orchestrator import _write_session_log_sr_decision
    log = tmp_path / "session_log.md"
    _write_session_log_sr_decision(log, beat_id="intro", decision=True, next_id="audience")
    content = log.read_text()
    assert "ADVANCE" in content
    assert "audience" in content


def test_session_log_checks_written(tmp_path):
    """_write_session_log_checks appends check spec text to session_log.md."""
    from showrunner.orchestrator import _write_session_log_checks
    log = tmp_path / "session_log.md"
    _write_session_log_checks(log, "1. Bargos | Negotiation | Presence 4 | 2 | Average |")
    content = log.read_text()
    assert "Bargos" in content
    assert "Negotiation" in content


def test_session_log_no_checks_written(tmp_path):
    """_write_session_log_checks writes NO_CHECKS marker when none identified."""
    from showrunner.orchestrator import _write_session_log_checks
    log = tmp_path / "session_log.md"
    _write_session_log_checks(log, "NO_CHECKS")
    content = log.read_text()
    assert "NO_CHECKS" in content


def test_session_log_rulings_written(tmp_path):
    """_write_session_log_rulings appends rulings dict to session_log.md."""
    from showrunner.orchestrator import _write_session_log_rulings
    log = tmp_path / "session_log.md"
    _write_session_log_rulings(log, {"Bargos": "Negotiation passed: gains leverage."})
    content = log.read_text()
    assert "Bargos" in content
    assert "leverage" in content


def test_session_log_plan_update_written(tmp_path):
    """_write_session_log_plans appends plan summaries to session_log.md."""
    from showrunner.orchestrator import _write_session_log_plans
    log = tmp_path / "session_log.md"
    _write_session_log_plans(log, {"bargos": "Bargos plans to stall the party."})
    content = log.read_text()
    assert "bargos" in content
    assert "stall" in content


def test_session_log_appends_not_overwrites(tmp_path):
    """Multiple writes append; earlier content is preserved."""
    from showrunner.orchestrator import _write_session_log_checks, _write_session_log_rulings
    log = tmp_path / "session_log.md"
    _write_session_log_checks(log, "NO_CHECKS")
    _write_session_log_rulings(log, {"Bargos": "No effect."})
    content = log.read_text()
    assert "NO_CHECKS" in content
    assert "Bargos" in content
