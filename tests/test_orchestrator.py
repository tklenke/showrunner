# ABOUTME: Tests for orchestrator — player turn detection and CLI prompt for human characters.
# ABOUTME: Verifies human vs AI character routing and CLI input handling.


SCENE = {
    "beats": [
        {"id": "summons"},
        {"id": "audience"},
        {"id": "mission_brief"},
    ]
}


def test_beat_prompt_enter_stays_on_current_beat(monkeypatch):
    from showrunner.orchestrator import _beat_prompt
    monkeypatch.setattr("builtins.input", lambda _: "")
    result = _beat_prompt(SCENE, "summons")
    assert result == "stay"


def test_beat_prompt_a_advances(monkeypatch):
    from showrunner.orchestrator import _beat_prompt
    monkeypatch.setattr("builtins.input", lambda _: "a")
    result = _beat_prompt(SCENE, "summons")
    assert result == "advance"


def test_beat_prompt_beat_id_returns_id(monkeypatch):
    from showrunner.orchestrator import _beat_prompt
    monkeypatch.setattr("builtins.input", lambda _: "mission_brief")
    result = _beat_prompt(SCENE, "summons")
    assert result == "mission_brief"


def test_beat_prompt_quit_returns_quit(monkeypatch):
    from showrunner.orchestrator import _beat_prompt
    monkeypatch.setattr("builtins.input", lambda _: "q")
    result = _beat_prompt(SCENE, "summons")
    assert result == "q"


def test_human_player_turn_prompts_cli(monkeypatch):
    from showrunner.orchestrator import prompt_player_action
    monkeypatch.setattr("builtins.input", lambda _: "Zee scans the exits.")
    result = prompt_player_action("Z-4P0")
    assert result == "Zee scans the exits."


def test_companion_character_detected_correctly():
    from showrunner.orchestrator import is_human_character
    assert not is_human_character({"identity": {"player": "companion"}})


def test_human_character_detected_correctly():
    from showrunner.orchestrator import is_human_character
    assert is_human_character({"identity": {"player": "human"}})


# ---------------------------------------------------------------------------
# _parse_ruling_specs
# ---------------------------------------------------------------------------

def test_parse_ruling_specs_no_checks():
    from showrunner.orchestrator import _parse_ruling_specs
    assert _parse_ruling_specs("NO_CHECKS") == []


def test_parse_ruling_specs_single_check():
    from showrunner.orchestrator import _parse_ruling_specs
    text = "1. Z-4P0 | Negotiation | Presence 2 | 1 | Opposed vs Bargos Cool | +1 Boost"
    specs = _parse_ruling_specs(text)
    assert len(specs) == 1
    s = specs[0]
    assert s["actor"] == "Z-4P0"
    assert s["skill"] == "Negotiation"
    assert s["characteristic"] == "Presence"
    assert s["char_value"] == 2
    assert s["skill_rank"] == 1
    assert s["difficulty"] == "Opposed vs Bargos Cool"
    assert s["notes"] == "+1 Boost"


def test_parse_ruling_specs_two_checks():
    from showrunner.orchestrator import _parse_ruling_specs
    text = (
        "1. Z-4P0 | Negotiation | Presence 2 | 1 | Opposed vs Bargos Cool | +1 Boost\n"
        "2. Kaelen | Athletics | Brawn 3 | 2 | Average | Seeking cover"
    )
    specs = _parse_ruling_specs(text)
    assert len(specs) == 2
    assert specs[1]["actor"] == "Kaelen"
    assert specs[1]["char_value"] == 3
    assert specs[1]["skill_rank"] == 2


def test_parse_ruling_specs_missing_notes_defaults_empty():
    from showrunner.orchestrator import _parse_ruling_specs
    text = "1. Z-4P0 | Brawl | Brawn 3 | 2 | Average"
    specs = _parse_ruling_specs(text)
    assert specs[0]["notes"] == ""


def test_parse_ruling_specs_tolerates_surrounding_text():
    from showrunner.orchestrator import _parse_ruling_specs
    text = "Here are the checks:\n1. Z-4P0 | Brawl | Brawn 2 | 1 | Easy | None\nEnd."
    specs = _parse_ruling_specs(text)
    assert len(specs) == 1


def test_parse_ruling_specs_noninteger_values_default_to_zero():
    from showrunner.orchestrator import _parse_ruling_specs
    text = "1. Z-4P0 | Brawl | Brawn X | Y | Average | None"
    specs = _parse_ruling_specs(text)
    assert specs[0]["char_value"] == 0
    assert specs[0]["skill_rank"] == 0


# ---------------------------------------------------------------------------
# _ruling_specs_parser
# ---------------------------------------------------------------------------

def test_ruling_specs_parser_no_checks_is_ok():
    from showrunner.orchestrator import _ruling_specs_parser
    specs, ok = _ruling_specs_parser("NO_CHECKS")
    assert specs == []
    assert ok is True


def test_ruling_specs_parser_valid_line_is_ok():
    from showrunner.orchestrator import _ruling_specs_parser
    raw = "1. Z-4P0 | Negotiation | Presence 2 | 1 | Average | notes"
    specs, ok = _ruling_specs_parser(raw)
    assert len(specs) == 1
    assert ok is True


def test_ruling_specs_parser_malformed_is_not_ok():
    from showrunner.orchestrator import _ruling_specs_parser
    specs, ok = _ruling_specs_parser("{Kaelin} | Negotiation | garbage")
    assert specs == []
    assert ok is False


# ---------------------------------------------------------------------------
# _build_char_stats
# ---------------------------------------------------------------------------

_BARGOS_YAML = {
    "identity": {"name": "Bargos the Hutt"},
    "characteristics": {"presence": 4, "cunning": 3},
    "skills": [{"name": "Negotiation", "characteristic": "Presence", "ranks": 2}],
}


def test_build_char_stats_keys_are_character_ids():
    from showrunner.orchestrator import _build_char_stats
    result = _build_char_stats({"bargos": _BARGOS_YAML})
    assert "bargos" in result


def test_build_char_stats_includes_character_name():
    from showrunner.orchestrator import _build_char_stats
    result = _build_char_stats({"bargos": _BARGOS_YAML})
    assert "Bargos the Hutt" in result["bargos"]


def test_build_char_stats_includes_characteristic_values():
    from showrunner.orchestrator import _build_char_stats
    result = _build_char_stats({"bargos": _BARGOS_YAML})
    assert "4" in result["bargos"]
    assert "3" in result["bargos"]


def test_build_char_stats_includes_skill_names():
    from showrunner.orchestrator import _build_char_stats
    result = _build_char_stats({"bargos": _BARGOS_YAML})
    assert "Negotiation" in result["bargos"]


def test_build_char_stats_includes_inline_npcs_with_stats():
    from showrunner.orchestrator import _build_char_stats
    inline_npc = {
        "id": "genko", "name": "Genko",
        "characteristics": {"brawn": 1, "agility": 2, "intellect": 3, "cunning": 3, "willpower": 2, "presence": 2},
        "skills": [{"name": "Deception", "ranks": 2}],
    }
    result = _build_char_stats({}, inline_npcs=[inline_npc])
    assert "genko" in result
    assert "Genko" in result["genko"]
    assert "Deception" in result["genko"]


def test_build_char_stats_skips_inline_npcs_without_characteristics():
    from showrunner.orchestrator import _build_char_stats
    inline_npc = {"id": "servant", "name": "Servant"}
    result = _build_char_stats({}, inline_npcs=[inline_npc])
    assert "servant" not in result


def test_build_char_stats_includes_minion_groups():
    from showrunner.orchestrator import _build_char_stats
    minion = {
        "id": "guards", "name": "Gamorrean Guards",
        "characteristics": {"brawn": 3, "agility": 2, "intellect": 1, "cunning": 1, "willpower": 2, "presence": 1},
        "skills": [{"name": "Melee", "ranks": 1}],
    }
    result = _build_char_stats({}, minion_groups=[minion])
    assert "guards" in result
    assert "Gamorrean Guards" in result["guards"]
    assert "Melee" in result["guards"]


def test_build_char_stats_merges_yaml_inline_and_minion():
    from showrunner.orchestrator import _build_char_stats
    inline_npc = {
        "id": "genko", "name": "Genko",
        "characteristics": {"cunning": 3},
        "skills": [],
    }
    minion = {
        "id": "guards", "name": "Guards",
        "characteristics": {"brawn": 3},
        "skills": [],
    }
    result = _build_char_stats({"bargos": _BARGOS_YAML}, inline_npcs=[inline_npc], minion_groups=[minion])
    assert "bargos" in result
    assert "genko" in result
    assert "guards" in result


# ---------------------------------------------------------------------------
# _parse_summaries_log
# ---------------------------------------------------------------------------

def test_parse_summaries_log_returns_dict_keyed_by_actor(tmp_path):
    from showrunner.orchestrator import _parse_summaries_log
    log = tmp_path / "s.txt"
    log.write_text("bargos: Bargos threatened.\nkaelen: Kaelen watched.\n")
    result = _parse_summaries_log(log)
    assert set(result.keys()) == {"bargos", "kaelen"}


def test_parse_summaries_log_returns_correct_summaries(tmp_path):
    from showrunner.orchestrator import _parse_summaries_log
    log = tmp_path / "s.txt"
    log.write_text("bargos: Bargos threatened.\n")
    result = _parse_summaries_log(log)
    assert result["bargos"] == "Bargos threatened."


def test_parse_summaries_log_missing_file_returns_empty(tmp_path):
    from showrunner.orchestrator import _parse_summaries_log
    result = _parse_summaries_log(tmp_path / "missing.txt")
    assert result == {}


# ---------------------------------------------------------------------------
# _write_turn_file
# ---------------------------------------------------------------------------

def test_write_turn_file_creates_file(tmp_path):
    from showrunner.orchestrator import _write_turn_file
    result = _write_turn_file(tmp_path, 0, 0, "summons", 1, "summaries", "Bargos spoke.")
    assert (tmp_path / "00_00_summons_0001_summaries.txt").exists()
    assert result == "Bargos spoke."


def test_write_turn_file_returns_content(tmp_path):
    from showrunner.orchestrator import _write_turn_file
    content = "Check: Z-4P0 | Negotiation"
    result = _write_turn_file(tmp_path, 0, 1, "beat", 5, "checks", content)
    assert result == content


def test_write_turn_file_scene_beat_turn_naming(tmp_path):
    from showrunner.orchestrator import _write_turn_file
    _write_turn_file(tmp_path, 0, 2, "gamorrean_rumble", 3, "summaries", "content")
    assert (tmp_path / "00_02_gamorrean_rumble_0003_summaries.txt").exists()


# ---------------------------------------------------------------------------
# _apply_beat_notes
# ---------------------------------------------------------------------------

_BEAT_WITH_NOTES = {
    "id": "summons",
    "title": "The Summons",
    "show_runner_notes": "SR directive here.",
    "narrator_notes": "Narrator hint here.",
}


def test_apply_beat_notes_injects_sr_notes():
    from showrunner.orchestrator import _apply_beat_notes
    sr_ctx, _ = _apply_beat_notes(_BEAT_WITH_NOTES, "base sr", "base narrator")
    assert "SR directive here." in sr_ctx
    assert "## Beat Director Notes:" in sr_ctx


def test_apply_beat_notes_injects_narrator_notes():
    from showrunner.orchestrator import _apply_beat_notes
    _, narrator_ctx = _apply_beat_notes(_BEAT_WITH_NOTES, "base sr", "base narrator")
    assert "Narrator hint here." in narrator_ctx
    assert "## Beat Director Notes:" in narrator_ctx


def test_apply_beat_notes_preserves_base_ctx():
    from showrunner.orchestrator import _apply_beat_notes
    sr_ctx, narrator_ctx = _apply_beat_notes(_BEAT_WITH_NOTES, "base sr", "base narrator")
    assert "base sr" in sr_ctx
    assert "base narrator" in narrator_ctx


def test_apply_beat_notes_empty_notes_leaves_contexts_unchanged():
    from showrunner.orchestrator import _apply_beat_notes
    beat = {"id": "x", "title": "X", "show_runner_notes": "", "narrator_notes": ""}
    sr_ctx, narrator_ctx = _apply_beat_notes(beat, "base sr", "base narrator")
    assert sr_ctx == "base sr"
    assert narrator_ctx == "base narrator"


# ---------------------------------------------------------------------------
# _read_last_session_log_entry
# ---------------------------------------------------------------------------

def test_read_last_session_log_entry_returns_empty_when_file_missing(tmp_path, monkeypatch):
    from showrunner.orchestrator import _read_last_session_log_entry
    monkeypatch.chdir(tmp_path)
    result = _read_last_session_log_entry()
    assert result == ""


def test_read_last_session_log_entry_returns_last_paragraph(tmp_path, monkeypatch):
    from showrunner.orchestrator import _read_last_session_log_entry
    log_file = tmp_path / "state" / "session_log.md"
    log_file.parent.mkdir()
    log_file.write_text("First entry.\n\nSecond entry.\n\n")
    monkeypatch.chdir(tmp_path)
    result = _read_last_session_log_entry()
    assert "Second entry." in result


# ---------------------------------------------------------------------------
# verbose beat title print (via _run_beat_initialization)
# ---------------------------------------------------------------------------

def test_run_beat_initialization_prints_title_when_verbose(capsys, tmp_path, monkeypatch):
    import logging
    from unittest.mock import patch
    from showrunner.orchestrator import _run_beat_initialization
    monkeypatch.chdir(tmp_path)
    (tmp_path / "state").mkdir()
    log = logging.getLogger("test")
    with patch("showrunner.orchestrator.update_scene_state"), \
         patch("showrunner.orchestrator.run_beat_opener"):
        _run_beat_initialization(_BEAT_WITH_NOTES, "sr", "nar", "", verbose=True, log=log)
    captured = capsys.readouterr()
    assert "The Summons" in captured.out


def test_run_beat_initialization_no_print_when_not_verbose(capsys, tmp_path, monkeypatch):
    import logging
    from unittest.mock import patch
    from showrunner.orchestrator import _run_beat_initialization
    monkeypatch.chdir(tmp_path)
    (tmp_path / "state").mkdir()
    log = logging.getLogger("test")
    with patch("showrunner.orchestrator.update_scene_state"), \
         patch("showrunner.orchestrator.run_beat_opener"):
        _run_beat_initialization(_BEAT_WITH_NOTES, "sr", "nar", "", verbose=False, log=log)
    captured = capsys.readouterr()
    assert "The Summons" not in captured.out


def test_run_beat_initialization_calls_run_beat_opener(tmp_path, monkeypatch):
    import logging
    from unittest.mock import patch, MagicMock
    from showrunner.orchestrator import _run_beat_initialization
    monkeypatch.chdir(tmp_path)
    (tmp_path / "state").mkdir()
    log = logging.getLogger("test")
    with patch("showrunner.orchestrator.update_scene_state"), \
         patch("showrunner.orchestrator.run_beat_opener") as mock_opener:
        _run_beat_initialization(_BEAT_WITH_NOTES, "sr", "nar", "last entry", verbose=False, log=log)
    mock_opener.assert_called_once_with(_BEAT_WITH_NOTES, "last entry", verbose=False)


# ---------------------------------------------------------------------------
# parse_structured
# ---------------------------------------------------------------------------

def _ok_parser(raw: str):
    return (raw.strip(), True) if raw.strip() else (None, False)


def _fail_parser(raw: str):
    return (None, False)


def test_parse_structured_clean_input_no_llm_calls():
    from unittest.mock import patch
    from showrunner.orchestrator import parse_structured
    with patch("showrunner.orchestrator.call_llm") as mock:
        result, recovered = parse_structured("good input", _ok_parser, context="ctx")
    mock.assert_not_called()
    assert result == "good input"
    assert recovered is False


def test_parse_structured_malformed_calls_scribe():
    from unittest.mock import patch
    from showrunner.orchestrator import parse_structured
    with patch("showrunner.orchestrator.call_llm", return_value="fixed") as mock:
        result, recovered = parse_structured("bad", _fail_parser, context="ctx")
    scribe_calls = [c for c in mock.call_args_list if c.args[0] == "scribe"]
    assert len(scribe_calls) >= 1


def test_parse_structured_scribe_fixes_returns_recovered_true():
    from unittest.mock import patch
    from showrunner.orchestrator import parse_structured

    def parser(raw):
        return (raw, True) if "fixed" in raw else (None, False)

    with patch("showrunner.orchestrator.call_llm", return_value="fixed output"):
        result, recovered = parse_structured("broken", parser, context="ctx")
    assert recovered is True
    assert result == "fixed output"


def test_parse_structured_repair_prompt_includes_python_sample():
    from unittest.mock import patch
    from showrunner.orchestrator import parse_structured
    with patch("showrunner.orchestrator.call_llm", return_value="still bad") as mock:
        parse_structured("bad", _fail_parser, context="ctx", python_sample="{'actor': 'Bargos'}")
    scribe_call = next(c for c in mock.call_args_list if c.args[0] == "scribe")
    assert "{'actor': 'Bargos'}" in scribe_call.args[2]


def test_parse_structured_all_llm_fail_returns_zero_fallback(tmp_path, monkeypatch):
    from unittest.mock import patch
    from showrunner.orchestrator import parse_structured
    monkeypatch.chdir(tmp_path)
    (tmp_path / "state").mkdir()
    monkeypatch.setattr("builtins.input", lambda _: "")
    with patch("showrunner.orchestrator.call_llm", return_value="still bad"):
        result, recovered = parse_structured("bad", _fail_parser, context="ctx")
    assert recovered is False


def test_parse_structured_all_fail_does_not_write_to_session_log(tmp_path, monkeypatch):
    from unittest.mock import patch
    from showrunner.orchestrator import parse_structured
    monkeypatch.chdir(tmp_path)
    (tmp_path / "state").mkdir()
    monkeypatch.setattr("builtins.input", lambda _: "")
    with patch("showrunner.orchestrator.call_llm", return_value="still bad"):
        parse_structured("bad", _fail_parser, context="ctx")
    log_path = tmp_path / "state" / "session_log.md"
    assert not log_path.exists() or "WARNING" not in log_path.read_text()


def test_parse_structured_all_fail_logs_warning(tmp_path, monkeypatch):
    import logging
    from unittest.mock import patch
    from showrunner.orchestrator import parse_structured
    monkeypatch.chdir(tmp_path)
    (tmp_path / "state").mkdir()
    monkeypatch.setattr("builtins.input", lambda _: "")
    with patch("showrunner.orchestrator.call_llm", return_value="still bad"):
        with patch("showrunner.orchestrator._log") as mock_log:
            parse_structured("bad", _fail_parser, context="ctx")
    mock_log.warning.assert_called_once()
    assert "ctx" in mock_log.warning.call_args.args[0]


# ---------------------------------------------------------------------------
# _find_human_pc_name
# ---------------------------------------------------------------------------

_HUMAN_YAML = {"identity": {"name": "Z-4P0 ('Zee')", "player": "human"}}
_NPC_YAML = {"identity": {"name": "Bargos the Hutt"}}


def test_find_human_pc_name_returns_identity_name(tmp_path):
    import yaml as pyyaml
    from showrunner.orchestrator import _find_human_pc_name
    chars_dir = tmp_path / "chars"
    chars_dir.mkdir()
    (chars_dir / "Z-4P0.yaml").write_text(pyyaml.dump(_HUMAN_YAML))
    scene = {"characters_present": ["Z-4P0"]}
    result = _find_human_pc_name(scene, characters_dir=str(chars_dir))
    assert result == "Z-4P0 ('Zee')"


def test_find_human_pc_name_skips_npcs(tmp_path):
    import yaml as pyyaml
    from showrunner.orchestrator import _find_human_pc_name
    chars_dir = tmp_path / "chars"
    chars_dir.mkdir()
    (chars_dir / "bargos.yaml").write_text(pyyaml.dump(_NPC_YAML))
    (chars_dir / "Z-4P0.yaml").write_text(pyyaml.dump(_HUMAN_YAML))
    scene = {"characters_present": ["bargos", "Z-4P0"]}
    result = _find_human_pc_name(scene, characters_dir=str(chars_dir))
    assert result == "Z-4P0 ('Zee')"


def test_find_human_pc_name_returns_fallback_when_no_human(tmp_path):
    import yaml as pyyaml
    from showrunner.orchestrator import _find_human_pc_name
    chars_dir = tmp_path / "chars"
    chars_dir.mkdir()
    (chars_dir / "bargos.yaml").write_text(pyyaml.dump(_NPC_YAML))
    scene = {"characters_present": ["bargos"]}
    result = _find_human_pc_name(scene, characters_dir=str(chars_dir))
    assert result == "Player"


# ---------------------------------------------------------------------------
# _extract_stat_changes
# ---------------------------------------------------------------------------

def test_extract_stat_changes_parses_wounds():
    from showrunner.orchestrator import _extract_stat_changes
    result = _extract_stat_changes("Z-4P0 takes 3 wounds.")
    assert result.get("wounds") == 3


def test_extract_stat_changes_parses_strain():
    from showrunner.orchestrator import _extract_stat_changes
    result = _extract_stat_changes("Kaelen suffers 2 strain from the exertion.")
    assert result.get("strain") == 2


def test_extract_stat_changes_returns_zero_for_no_damage():
    from showrunner.orchestrator import _extract_stat_changes
    result = _extract_stat_changes("Z-4P0 succeeds with Triumph. No damage taken.")
    assert result.get("wounds", 0) == 0
    assert result.get("strain", 0) == 0


# ---------------------------------------------------------------------------
# _make_ruling_callback (orchestrator's on_ruling factory)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# _build_actor_name_map
# ---------------------------------------------------------------------------

def test_build_actor_name_map_maps_yaml_characters():
    from showrunner.orchestrator import _build_actor_name_map
    scene = {"characters_present": ["bargos_the_hutt"], "inline_npcs": [], "minion_groups": []}
    scene_yamls = {"bargos_the_hutt": {"identity": {"name": "Bargos"}}}
    result = _build_actor_name_map(scene, scene_yamls)
    assert result["bargos"] == "bargos_the_hutt"


def test_build_actor_name_map_maps_inline_npcs():
    from showrunner.orchestrator import _build_actor_name_map
    scene = {
        "characters_present": [],
        "inline_npcs": [{"id": "genko", "name": "Genko"}],
        "minion_groups": [],
    }
    result = _build_actor_name_map(scene, {})
    assert result["genko"] == "genko"


def test_build_actor_name_map_maps_minion_groups():
    from showrunner.orchestrator import _build_actor_name_map
    scene = {
        "characters_present": [],
        "inline_npcs": [],
        "minion_groups": [{"id": "gamorrean_guards", "name": "Renegade Gamorrean Guards"}],
    }
    result = _build_actor_name_map(scene, {})
    assert result["renegade gamorrean guards"] == "gamorrean_guards"


def test_build_actor_name_map_keys_are_lowercase():
    from showrunner.orchestrator import _build_actor_name_map
    scene = {"characters_present": [], "inline_npcs": [], "minion_groups": []}
    scene_yamls = {"bargos_the_hutt": {"identity": {"name": "Bargos The Hutt"}}}
    result = _build_actor_name_map(scene, scene_yamls)
    assert "bargos the hutt" in result
    assert "Bargos The Hutt" not in result


# ---------------------------------------------------------------------------
# _make_ruling_callback (updated signature)
# ---------------------------------------------------------------------------

def test_make_ruling_callback_updates_party_stats_on_ruling(tmp_path, monkeypatch):
    from showrunner.orchestrator import _make_ruling_callback
    monkeypatch.chdir(tmp_path)
    (tmp_path / "state").mkdir()
    import yaml
    (tmp_path / "state" / "party_stats.yaml").write_text(
        yaml.dump({"characters": {"z_4p0": {"wounds_current": 0, "wounds_threshold": 12}}})
    )
    callback = _make_ruling_callback(tmp_path / "state" / "party_stats.yaml", {})
    callback("z_4p0", "Z-4P0 takes 2 wounds.")
    updated = yaml.safe_load((tmp_path / "state" / "party_stats.yaml").read_text())
    assert updated["characters"]["z_4p0"]["wounds_current"] == 2


def test_make_ruling_callback_returns_stats_text_for_next_ruling(tmp_path, monkeypatch):
    from showrunner.orchestrator import _make_ruling_callback
    monkeypatch.chdir(tmp_path)
    (tmp_path / "state").mkdir()
    import yaml
    (tmp_path / "state" / "party_stats.yaml").write_text(
        yaml.dump({"characters": {"z_4p0": {"wounds_current": 0, "wounds_threshold": 12}}})
    )
    callback = _make_ruling_callback(tmp_path / "state" / "party_stats.yaml", {})
    context = callback("z_4p0", "Z-4P0 takes 2 wounds.")
    assert context is not None
    assert isinstance(context, str)


def test_make_ruling_callback_resolves_display_name_to_id(tmp_path, monkeypatch):
    from showrunner.orchestrator import _make_ruling_callback
    monkeypatch.chdir(tmp_path)
    (tmp_path / "state").mkdir()
    import yaml
    (tmp_path / "state" / "party_stats.yaml").write_text(
        yaml.dump({"characters": {"bargos_the_hutt": {"wounds_current": 0, "wounds_threshold": 20}}})
    )
    name_to_id = {"bargos": "bargos_the_hutt"}
    callback = _make_ruling_callback(tmp_path / "state" / "party_stats.yaml", name_to_id)
    callback("Bargos", "Bargos takes 3 wounds.")
    updated = yaml.safe_load((tmp_path / "state" / "party_stats.yaml").read_text())
    assert updated["characters"]["bargos_the_hutt"]["wounds_current"] == 3


def test_make_ruling_callback_falls_back_to_raw_actor_when_not_in_map(tmp_path, monkeypatch):
    from showrunner.orchestrator import _make_ruling_callback
    monkeypatch.chdir(tmp_path)
    (tmp_path / "state").mkdir()
    import yaml
    (tmp_path / "state" / "party_stats.yaml").write_text(
        yaml.dump({"characters": {"z_4p0": {"wounds_current": 0, "wounds_threshold": 12}}})
    )
    callback = _make_ruling_callback(tmp_path / "state" / "party_stats.yaml", {})
    callback("z_4p0", "Z-4P0 takes 1 wound.")
    updated = yaml.safe_load((tmp_path / "state" / "party_stats.yaml").read_text())
    assert updated["characters"]["z_4p0"]["wounds_current"] == 1


# ---------------------------------------------------------------------------
# _roll_specs — manual dice input wiring
# ---------------------------------------------------------------------------

_SPEC = {
    "actor": "Kaelen",
    "skill": "Negotiation",
    "characteristic": "Presence",
    "char_value": 3,
    "skill_rank": 2,
    "difficulty": "Average",
    "opposed_skill": "",
}


def test_roll_specs_auto_roll_when_no_input(monkeypatch):
    from showrunner.orchestrator import _roll_specs
    monkeypatch.setattr("builtins.input", lambda _: "")
    spec = dict(_SPEC)
    _roll_specs([spec])
    assert "roll_result" in spec
    assert "passed" in spec["roll_result"] or "failed" in spec["roll_result"]


def test_roll_specs_manual_input_sets_roll_result(monkeypatch):
    from showrunner.orchestrator import _roll_specs
    monkeypatch.setattr("builtins.input", lambda _: "S3A1")
    spec = dict(_SPEC)
    _roll_specs([spec])
    assert "roll_result" in spec
    assert "passed" in spec["roll_result"]
    assert "+3" in spec["roll_result"]  # net_successes 3


def test_roll_specs_manual_failure_marked_failed(monkeypatch):
    from showrunner.orchestrator import _roll_specs
    monkeypatch.setattr("builtins.input", lambda _: "F3")
    spec = dict(_SPEC)
    _roll_specs([spec])
    assert "failed" in spec["roll_result"]
    assert "-3" in spec["roll_result"]
