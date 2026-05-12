# ABOUTME: Tests for agent tool stubs — roll_dice, ask_player, consult_narrator, read/write state.
# ABOUTME: Verifies tool wiring is correct before agents are fully integrated.

import json
import pytest


def test_roll_dice_returns_string():
    from showrunner.tools.agent_tools import roll_dice
    pool = json.dumps({"proficiency": 1, "ability": 1, "difficulty": 2,
                       "challenge": 0, "boost": 0, "setback": 0})
    result = roll_dice.run(pool)
    assert isinstance(result, str)


def test_roll_dice_result_mentions_pass_or_fail():
    from showrunner.tools.agent_tools import roll_dice
    pool = json.dumps({"proficiency": 2, "ability": 0, "difficulty": 1,
                       "challenge": 0, "boost": 0, "setback": 0})
    result = roll_dice.run(pool)
    assert "passed" in result.lower() or "failed" in result.lower()


def test_roll_dice_invalid_json_raises():
    from showrunner.tools.agent_tools import roll_dice
    with pytest.raises(ValueError):
        roll_dice.run("not json")


def test_ask_player_returns_input(monkeypatch):
    from showrunner.tools.agent_tools import ask_player
    monkeypatch.setattr("builtins.input", lambda _: "I attack the guard")
    result = ask_player.run("What does Kaelen do?")
    assert result == "I attack the guard"


def test_consult_narrator_returns_fallback():
    from showrunner.tools.agent_tools import consult_narrator
    result = consult_narrator.run("Should the Gamorreans attack?")
    assert isinstance(result, str) and len(result) > 0


def test_read_state_missing_file_returns_message():
    from showrunner.tools.agent_tools import read_state
    result = read_state.run("nonexistent_file.yaml")
    assert "not found" in result.lower()


def test_read_state_schema_wrapped_filename_extracted():
    from showrunner.tools.agent_tools import _ReadStateInput
    # 3B model passes JSON Schema structure instead of the actual value
    m = _ReadStateInput(filename={"properties": {"filename": "scene_state.yaml"}})
    assert m.filename == "scene_state.yaml"


def test_consult_narrator_schema_wrapped_question_extracted():
    from showrunner.tools.agent_tools import _ConsultNarratorInput
    # 3B model passes JSON Schema structure instead of the actual value
    m = _ConsultNarratorInput(question={"properties": {"question": "Attack?"}})
    assert m.question == "Attack?"


def test_write_state_unknown_file_raises():
    from showrunner.tools.agent_tools import write_state
    with pytest.raises(ValueError):
        write_state.run("unknown_file.yaml", {})
