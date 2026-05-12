# ABOUTME: Tests for state_writer — writing party stats, scene state, and session log files.
# ABOUTME: Uses pytest tmp_path for all file writes; never touches live state/ files.

import yaml


def test_update_party_stats_writes_yaml(tmp_path):
    from showrunner.tools.state_writer import update_party_stats
    outfile = str(tmp_path / "party_stats.yaml")
    update_party_stats({"rix": {"wounds": 2}}, path=outfile)
    with open(outfile) as f:
        data = yaml.safe_load(f)
    assert data["rix"]["wounds"] == 2


def test_update_party_stats_merges_not_replaces(tmp_path):
    from showrunner.tools.state_writer import update_party_stats
    outfile = str(tmp_path / "party_stats.yaml")
    update_party_stats({"rix": {"wounds": 0}, "kaelen": {"wounds": 0}}, path=outfile)
    update_party_stats({"rix": {"wounds": 3}}, path=outfile)
    with open(outfile) as f:
        data = yaml.safe_load(f)
    assert data["rix"]["wounds"] == 3
    assert "kaelen" in data


def test_append_session_log_creates_if_missing(tmp_path):
    from showrunner.tools.state_writer import append_session_log
    logfile = str(tmp_path / "session_log.md")
    append_session_log("Turn 1: party enters the hall.", path=logfile)
    with open(logfile) as f:
        content = f.read()
    assert "Turn 1" in content


def test_append_session_log_appends_not_overwrites(tmp_path):
    from showrunner.tools.state_writer import append_session_log
    logfile = str(tmp_path / "session_log.md")
    append_session_log("Turn 1: party enters.", path=logfile)
    append_session_log("Turn 2: guard approaches.", path=logfile)
    with open(logfile) as f:
        content = f.read()
    assert "Turn 1" in content
    assert "Turn 2" in content


def test_update_scene_state(tmp_path):
    from showrunner.tools.state_writer import update_scene_state
    outfile = str(tmp_path / "scene_state.yaml")
    update_scene_state({"location": "Hangar Bay"}, path=outfile)
    with open(outfile) as f:
        data = yaml.safe_load(f)
    assert data["location"] == "Hangar Bay"
