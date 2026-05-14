# ABOUTME: Tests for CLI entry point — argument parsing and session reset.
# ABOUTME: Verifies --reset wipes logs and scene state before starting.

from pathlib import Path


def _make_logs(tmp_path: Path) -> tuple[Path, Path]:
    """Create a fake logs dir and state dir with files, return (logs_dir, state_dir)."""
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    (logs_dir / "session_20260514_120000.log").write_text("old log")
    (logs_dir / "prompts_20260514_120000.log").write_text("old prompts log")
    (logs_dir / "00_01_summons_0001_checks.txt").write_text("old checks")

    prompts_dir = logs_dir / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "0001_narrator_run_beat_opener.md").write_text("old dump")

    state_dir = tmp_path / "state"
    state_dir.mkdir()
    (state_dir / "scene_state.yaml").write_text("current_beat: gamorrean_rumble\n")
    (state_dir / "session_log.md").write_text("old narrative")
    (state_dir / "party_stats.yaml").write_text("characters: {}")  # should survive

    return logs_dir, state_dir


def test_reset_session_removes_scene_state(tmp_path):
    from showrunner.main import reset_session
    logs_dir, state_dir = _make_logs(tmp_path)
    reset_session(state_dir=str(state_dir), logs_dir=str(logs_dir))
    assert not (state_dir / "scene_state.yaml").exists()


def test_reset_session_removes_session_log(tmp_path):
    from showrunner.main import reset_session
    logs_dir, state_dir = _make_logs(tmp_path)
    reset_session(state_dir=str(state_dir), logs_dir=str(logs_dir))
    assert not (state_dir / "session_log.md").exists()


def test_reset_session_clears_log_files(tmp_path):
    from showrunner.main import reset_session
    logs_dir, state_dir = _make_logs(tmp_path)
    reset_session(state_dir=str(state_dir), logs_dir=str(logs_dir))
    remaining = list(logs_dir.rglob("*"))
    # logs/ dir itself stays; prompts/ subdir may stay; no files
    assert all(p.is_dir() for p in remaining), f"Files remain: {remaining}"


def test_reset_session_preserves_party_stats(tmp_path):
    from showrunner.main import reset_session
    logs_dir, state_dir = _make_logs(tmp_path)
    reset_session(state_dir=str(state_dir), logs_dir=str(logs_dir))
    assert (state_dir / "party_stats.yaml").exists()


def test_reset_session_logs_dir_still_exists(tmp_path):
    from showrunner.main import reset_session
    logs_dir, state_dir = _make_logs(tmp_path)
    reset_session(state_dir=str(state_dir), logs_dir=str(logs_dir))
    assert logs_dir.exists()


def test_reset_session_tolerates_missing_logs_dir(tmp_path):
    from showrunner.main import reset_session
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    (state_dir / "scene_state.yaml").write_text("current_beat: rumble\n")
    # no logs_dir created
    reset_session(state_dir=str(state_dir), logs_dir=str(tmp_path / "logs"))
    assert not (state_dir / "scene_state.yaml").exists()


def test_reset_session_tolerates_missing_state_files(tmp_path):
    from showrunner.main import reset_session
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    # scene_state.yaml and session_log.md don't exist — should not raise
    reset_session(state_dir=str(state_dir), logs_dir=str(logs_dir))
