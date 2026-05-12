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


def test_consult_narrator_raises():
    from showrunner.tools.agent_tools import consult_narrator
    with pytest.raises(NotImplementedError):
        consult_narrator.run("Should the Gamorreans attack?")


def test_read_state_raises():
    from showrunner.tools.agent_tools import read_state
    with pytest.raises(NotImplementedError):
        read_state.run("scene_state.yaml")


def test_write_state_raises():
    from showrunner.tools.agent_tools import write_state
    with pytest.raises(NotImplementedError):
        write_state.run("party_stats.yaml", {})
