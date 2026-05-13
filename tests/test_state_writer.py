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


def test_initialize_scene_state_writes_correct_fields(tmp_path):
    from showrunner.tools.state_writer import initialize_scene_state
    initialize_scene_state(0, "opening", state_dir=str(tmp_path))
    with open(tmp_path / "scene_state.yaml") as f:
        data = yaml.safe_load(f)
    assert data["current_scene"] == 0
    assert data["current_beat"] == "opening"
    assert data["ticking_clocks"] == []
    assert data["character_plans"] == {}


def test_advance_beat_updates_current_beat(tmp_path):
    from showrunner.tools.state_writer import initialize_scene_state, advance_beat
    initialize_scene_state(0, "opening", state_dir=str(tmp_path))
    advance_beat("audience", state_dir=str(tmp_path))
    with open(tmp_path / "scene_state.yaml") as f:
        data = yaml.safe_load(f)
    assert data["current_beat"] == "audience"


def test_update_party_stats_deep_merge_preserves_other_characters(tmp_path):
    from showrunner.tools.state_writer import update_party_stats
    outfile = str(tmp_path / "party_stats.yaml")
    initial = {"characters": {"Z-4P0": {"wounds": 0, "strain": 0}, "Kae": {"wounds": 0, "strain": 0}}}
    update_party_stats(initial, path=outfile)
    update_party_stats({"characters": {"Z-4P0": {"wounds": 3}}}, path=outfile)
    with open(outfile) as f:
        data = yaml.safe_load(f)
    assert data["characters"]["Z-4P0"]["wounds"] == 3
    assert "Kae" in data["characters"], "Kae was wiped by shallow merge"


def test_update_scene_state_deep_merge_preserves_other_clocks(tmp_path):
    from showrunner.tools.state_writer import update_scene_state
    outfile = str(tmp_path / "scene_state.yaml")
    initial = {"ticking_clocks": [{"id": "storm", "destroyed": 0}], "character_plans": {"Kae": "find cover"}}
    update_scene_state(initial, path=outfile)
    update_scene_state({"character_plans": {"Z-4P0": "beep frantically"}}, path=outfile)
    with open(outfile) as f:
        data = yaml.safe_load(f)
    assert data["character_plans"]["Z-4P0"] == "beep frantically"
    assert "Kae" in data["character_plans"], "Kae's plan was wiped by shallow merge"


def test_advance_beat_preserves_other_fields(tmp_path):
    from showrunner.tools.state_writer import initialize_scene_state, advance_beat, update_scene_state
    initialize_scene_state(0, "opening", state_dir=str(tmp_path))
    outfile = str(tmp_path / "scene_state.yaml")
    update_scene_state({"ticking_clocks": [{"id": "storm_barriers", "destroyed": 1}]}, path=outfile)
    advance_beat("audience", state_dir=str(tmp_path))
    with open(tmp_path / "scene_state.yaml") as f:
        data = yaml.safe_load(f)
    assert data["current_beat"] == "audience"
    assert data["ticking_clocks"][0]["destroyed"] == 1
