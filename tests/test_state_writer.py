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


_SCENE = {"scene_id": "test_scene", "beats": [{"id": "opening"}, {"id": "audience"}]}


def test_initialize_scene_state_writes_correct_fields(tmp_path):
    from showrunner.tools.state_writer import initialize_scene_state
    initialize_scene_state(_SCENE, state_dir=str(tmp_path))
    with open(tmp_path / "scene_state.yaml") as f:
        data = yaml.safe_load(f)
    assert data["scene_id"] == "test_scene"
    assert data["current_beat"] == "opening"
    assert data["npc_knowledge"] == {}
    assert data["flags"] == {}
    assert data["last_actions"] == {}


def test_initialize_scene_state_skips_if_same_scene(tmp_path):
    from showrunner.tools.state_writer import initialize_scene_state, advance_beat
    initialize_scene_state(_SCENE, state_dir=str(tmp_path))
    advance_beat("audience", state_dir=str(tmp_path))
    initialize_scene_state(_SCENE, state_dir=str(tmp_path))
    with open(tmp_path / "scene_state.yaml") as f:
        data = yaml.safe_load(f)
    assert data["current_beat"] == "audience", "existing state should be preserved for same scene"


def test_initialize_scene_state_reinitializes_on_scene_change(tmp_path):
    from showrunner.tools.state_writer import initialize_scene_state, advance_beat
    initialize_scene_state(_SCENE, state_dir=str(tmp_path))
    advance_beat("audience", state_dir=str(tmp_path))
    new_scene = {"scene_id": "other_scene", "beats": [{"id": "start"}]}
    initialize_scene_state(new_scene, state_dir=str(tmp_path))
    with open(tmp_path / "scene_state.yaml") as f:
        data = yaml.safe_load(f)
    assert data["scene_id"] == "other_scene"
    assert data["current_beat"] == "start"


def test_advance_beat_updates_current_beat(tmp_path):
    from showrunner.tools.state_writer import initialize_scene_state, advance_beat
    initialize_scene_state(_SCENE, state_dir=str(tmp_path))
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


_NPC_YAML = {
    "identity": {"name": "Bargos the Hutt", "player": None},
    "derived": {"wound_threshold": 18, "strain_threshold": 14},
    "status": {"wounds": 0, "strain": 0, "critical_injuries": []},
}

_HUMAN_YAML = {
    "identity": {"name": "Z-4P0", "player": "human"},
    "derived": {"wound_threshold": 12, "strain_threshold": 13},
    "status": {"wounds": 0, "strain": 0, "critical_injuries": []},
}


def _write_char_yaml(chars_dir, name, data):
    import yaml
    (chars_dir / f"{name}.yaml").write_text(yaml.dump(data))


def test_initialize_npc_stats_adds_npc_with_thresholds(tmp_path):
    import yaml
    from showrunner.tools.state_writer import initialize_npc_stats
    chars_dir = tmp_path / "chars"
    chars_dir.mkdir()
    _write_char_yaml(chars_dir, "bargos_the_hutt", _NPC_YAML)
    scene = {"npcs_present": ["bargos_the_hutt"]}
    stats_path = str(tmp_path / "party_stats.yaml")
    initialize_npc_stats(scene, path=stats_path, characters_dir=str(chars_dir))
    with open(stats_path) as f:
        data = yaml.safe_load(f)
    char = data["characters"]["bargos_the_hutt"]
    assert char["wounds_current"] == 0
    assert char["wounds_threshold"] == 18
    assert char["strain_current"] == 0
    assert char["strain_threshold"] == 14


def test_initialize_npc_stats_skips_human_pc(tmp_path):
    import yaml
    from pathlib import Path
    from showrunner.tools.state_writer import initialize_npc_stats
    chars_dir = tmp_path / "chars"
    chars_dir.mkdir()
    _write_char_yaml(chars_dir, "Z-4P0", _HUMAN_YAML)
    scene = {"npcs_present": ["Z-4P0"]}
    stats_path = str(tmp_path / "party_stats.yaml")
    initialize_npc_stats(scene, path=stats_path, characters_dir=str(chars_dir))
    if Path(stats_path).exists():
        with open(stats_path) as f:
            data = yaml.safe_load(f)
        assert "Z-4P0" not in data.get("characters", {})


def test_initialize_npc_stats_preserves_existing_wounds(tmp_path):
    import yaml
    from showrunner.tools.state_writer import initialize_npc_stats, update_party_stats
    chars_dir = tmp_path / "chars"
    chars_dir.mkdir()
    _write_char_yaml(chars_dir, "bargos_the_hutt", _NPC_YAML)
    stats_path = str(tmp_path / "party_stats.yaml")
    update_party_stats({"characters": {"bargos_the_hutt": {"wounds_current": 5, "wounds_threshold": 18}}}, path=stats_path)
    scene = {"npcs_present": ["bargos_the_hutt"]}
    initialize_npc_stats(scene, path=stats_path, characters_dir=str(chars_dir))
    with open(stats_path) as f:
        data = yaml.safe_load(f)
    assert data["characters"]["bargos_the_hutt"]["wounds_current"] == 5


def test_initialize_npc_stats_skips_missing_yaml(tmp_path):
    from showrunner.tools.state_writer import initialize_npc_stats
    chars_dir = tmp_path / "chars"
    chars_dir.mkdir()
    scene = {"npcs_present": ["inline_npc_no_file"]}
    stats_path = str(tmp_path / "party_stats.yaml")
    initialize_npc_stats(scene, path=stats_path, characters_dir=str(chars_dir))  # must not raise


def test_advance_beat_preserves_other_fields(tmp_path):
    from showrunner.tools.state_writer import initialize_scene_state, advance_beat, update_scene_state
    initialize_scene_state(_SCENE, state_dir=str(tmp_path))
    outfile = str(tmp_path / "scene_state.yaml")
    update_scene_state({"ticking_clocks": [{"id": "storm_barriers", "destroyed": 1}]}, path=outfile)
    advance_beat("audience", state_dir=str(tmp_path))
    with open(tmp_path / "scene_state.yaml") as f:
        data = yaml.safe_load(f)
    assert data["current_beat"] == "audience"
    assert data["ticking_clocks"][0]["destroyed"] == 1
