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
# _build_stats_text
# ---------------------------------------------------------------------------

def test_build_stats_text_includes_character_name():
    from showrunner.orchestrator import _build_stats_text
    yamls = {
        "bargos": {
            "identity": {"name": "Bargos the Hutt"},
            "characteristics": {"presence": 4, "cunning": 3},
            "skills": [{"name": "Negotiation", "characteristic": "Presence"}],
        }
    }
    text = _build_stats_text(yamls)
    assert "Bargos the Hutt" in text


def test_build_stats_text_includes_characteristic_values():
    from showrunner.orchestrator import _build_stats_text
    yamls = {
        "bargos": {
            "identity": {"name": "Bargos"},
            "characteristics": {"presence": 4, "cunning": 3},
            "skills": [],
        }
    }
    text = _build_stats_text(yamls)
    assert "4" in text
    assert "3" in text


def test_build_stats_text_includes_skill_names():
    from showrunner.orchestrator import _build_stats_text
    yamls = {
        "bargos": {
            "identity": {"name": "Bargos"},
            "characteristics": {},
            "skills": [{"name": "Cool", "characteristic": "Presence", "ranks": 2}],
        }
    }
    text = _build_stats_text(yamls)
    assert "Cool" in text


# ---------------------------------------------------------------------------
# _write_turn_file
# ---------------------------------------------------------------------------

def test_write_turn_file_creates_file(tmp_path):
    from showrunner.orchestrator import _write_turn_file
    result = _write_turn_file(tmp_path, "20260513_120000", "summons", "summaries", "Bargos spoke.")
    assert (tmp_path / "turn_20260513_120000_summons_summaries.txt").exists()
    assert result == "Bargos spoke."


def test_write_turn_file_returns_content(tmp_path):
    from showrunner.orchestrator import _write_turn_file
    content = "Check: Z-4P0 | Negotiation"
    result = _write_turn_file(tmp_path, "ts", "beat", "checks", content)
    assert result == content
