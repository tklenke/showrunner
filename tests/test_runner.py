# ABOUTME: Tests for runner.py — NPC/PC wave functions and five-step resolution pipeline.
# ABOUTME: All tests mock call_llm to verify message assembly and return values.

import pytest
from unittest.mock import patch, call


@pytest.fixture(autouse=True)
def gemini_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")


def _mock_call_llm(responses: list[str]):
    """Return a side_effect list that yields strings in order."""
    return responses


# ---------------------------------------------------------------------------
# run_npc_wave
# ---------------------------------------------------------------------------

def test_run_npc_wave_calls_show_runner_once():
    from showrunner.runner import run_npc_wave
    with patch("showrunner.runner.call_llm", side_effect=["beat plan", "narration", "npc out"]) as mock:
        run_npc_wave("sr ctx", "narrator ctx", {"bargos": "Bargos is here."})
    sr_calls = [c for c in mock.call_args_list if c.args[0] == "show_runner"]
    assert len(sr_calls) == 1


def test_run_npc_wave_calls_narrator_once():
    from showrunner.runner import run_npc_wave
    with patch("showrunner.runner.call_llm", side_effect=["beat plan", "narration", "npc out"]) as mock:
        run_npc_wave("sr ctx", "narrator ctx", {"bargos": "Bargos is here."})
    narrator_calls = [c for c in mock.call_args_list if c.args[0] == "narrator"]
    assert len(narrator_calls) == 1


def test_run_npc_wave_calls_actors_once_per_npc():
    from showrunner.runner import run_npc_wave
    with patch("showrunner.runner.call_llm", side_effect=["beat", "narr", "out1", "out2"]) as mock:
        run_npc_wave("sr", "nar", {"a": "A context", "b": "B context"})
    actors_calls = [c for c in mock.call_args_list if c.args[0] == "actors"]
    assert len(actors_calls) == 2


def test_run_npc_wave_second_npc_sees_first_npc_output():
    from showrunner.runner import run_npc_wave
    with patch("showrunner.runner.call_llm", side_effect=["beat plan", "narration", "first npc out", "second npc out"]) as mock:
        run_npc_wave("sr", "nar", {"first": "first ctx", "second": "second ctx"})
    second_npc_call = [c for c in mock.call_args_list if c.args[0] == "actors"][1]
    user_message = second_npc_call.args[2]
    assert "first npc out" in user_message


def test_run_npc_wave_returns_narrator_and_npc_outputs():
    from showrunner.runner import run_npc_wave
    with patch("showrunner.runner.call_llm", side_effect=["beat plan", "my narration", "bargos says hi"]):
        result = run_npc_wave("sr", "nar", {"bargos": "ctx"})
    assert result["_narrator"] == "my narration"
    assert result["bargos"] == "bargos says hi"


def test_run_npc_wave_prints_narrator_output(capsys):
    from showrunner.runner import run_npc_wave
    with patch("showrunner.runner.call_llm", side_effect=["beat", "narrator prose", "npc line"]):
        run_npc_wave("sr", "nar", {"bargos": "ctx"})
    captured = capsys.readouterr()
    assert "narrator prose" in captured.out


def test_run_npc_wave_prints_npc_output_with_id(capsys):
    from showrunner.runner import run_npc_wave
    with patch("showrunner.runner.call_llm", side_effect=["beat", "narr", "bargos speaks"]):
        run_npc_wave("sr", "nar", {"bargos": "ctx"})
    captured = capsys.readouterr()
    assert "bargos" in captured.out
    assert "bargos speaks" in captured.out


# ---------------------------------------------------------------------------
# run_companion_wave
# ---------------------------------------------------------------------------

def test_run_companion_wave_empty_returns_empty_dict():
    from showrunner.runner import run_companion_wave
    result = run_companion_wave("npc wave text", {}, "player did something")
    assert result == {}


def test_run_companion_wave_calls_actors_once_per_ai_pc():
    from showrunner.runner import run_companion_wave
    with patch("showrunner.runner.call_llm", side_effect=["kaelen out"]) as mock:
        run_companion_wave("npc wave", {"kaelen": "kaelen ctx"}, "player action")
    actors_calls = [c for c in mock.call_args_list if c.args[0] == "actors"]
    assert len(actors_calls) == 1


def test_run_companion_wave_user_message_contains_npc_wave_text():
    from showrunner.runner import run_companion_wave
    with patch("showrunner.runner.call_llm", side_effect=["kaelen out"]) as mock:
        run_companion_wave("NPC wave text here", {"kaelen": "kaelen ctx"}, "player action")
    user_msg = mock.call_args_list[0].args[2]
    assert "NPC wave text here" in user_msg


def test_run_companion_wave_user_message_contains_player_action():
    from showrunner.runner import run_companion_wave
    with patch("showrunner.runner.call_llm", side_effect=["kaelen out"]) as mock:
        run_companion_wave("npc wave", {"kaelen": "kaelen ctx"}, "player does X")
    user_msg = mock.call_args_list[0].args[2]
    assert "player does X" in user_msg


def test_run_companion_wave_returns_pc_outputs():
    from showrunner.runner import run_companion_wave
    with patch("showrunner.runner.call_llm", side_effect=["kaelen out"]):
        result = run_companion_wave("npc wave", {"kaelen": "ctx"}, "action")
    assert result == {"kaelen": "kaelen out"}


# ---------------------------------------------------------------------------
# run_summary_phase
# ---------------------------------------------------------------------------

def test_run_summary_phase_calls_actors_once_per_actor():
    from showrunner.runner import run_summary_phase
    with patch("showrunner.runner.call_llm", side_effect=["sum1", "sum2"]) as mock:
        run_summary_phase({"bargos": "did X", "kaelen": "did Y"})
    actors_calls = [c for c in mock.call_args_list if c.args[0] == "actors"]
    assert len(actors_calls) == 2


def test_run_summary_phase_user_message_contains_action_text():
    from showrunner.runner import run_summary_phase
    with patch("showrunner.runner.call_llm", side_effect=["summary"]) as mock:
        run_summary_phase({"bargos": "threatened Z-4P0"})
    user_msg = mock.call_args_list[0].args[2]
    assert "threatened Z-4P0" in user_msg


def test_run_summary_phase_returns_dict_keyed_by_actor():
    from showrunner.runner import run_summary_phase
    with patch("showrunner.runner.call_llm", side_effect=["sum1", "sum2"]):
        result = run_summary_phase({"bargos": "did X", "kaelen": "did Y"})
    assert set(result.keys()) == {"bargos", "kaelen"}
    assert result["bargos"] == "sum1"


# ---------------------------------------------------------------------------
# run_check_phase
# ---------------------------------------------------------------------------

def test_run_check_phase_calls_show_runner_once():
    from showrunner.runner import run_check_phase
    with patch("showrunner.runner.call_llm", return_value="NO_CHECKS") as mock:
        run_check_phase("summaries", "stats")
    sr_calls = [c for c in mock.call_args_list if c.args[0] == "show_runner"]
    assert len(sr_calls) == 1


def test_run_check_phase_user_message_contains_summaries_and_stats():
    from showrunner.runner import run_check_phase
    with patch("showrunner.runner.call_llm", return_value="NO_CHECKS") as mock:
        run_check_phase("action summaries here", "stats here")
    user_msg = mock.call_args_list[0].args[2]
    assert "action summaries here" in user_msg
    assert "stats here" in user_msg


def test_run_check_phase_returns_llm_output():
    from showrunner.runner import run_check_phase
    with patch("showrunner.runner.call_llm", return_value="1. Z-4P0 | Negotiation | ..."):
        result = run_check_phase("summaries", "stats")
    assert "Negotiation" in result


# ---------------------------------------------------------------------------
# run_ruling_phase
# ---------------------------------------------------------------------------

def test_run_ruling_phase_empty_returns_empty_dict():
    from showrunner.runner import run_ruling_phase
    result = run_ruling_phase([])
    assert result == {}


def test_run_ruling_phase_calls_show_runner_once_per_spec():
    from showrunner.runner import run_ruling_phase
    specs = [
        {"actor": "Z-4P0", "skill": "Negotiation", "difficulty": "Average", "notes": "", "roll_result": "passed"},
        {"actor": "Kaelen", "skill": "Athletics", "difficulty": "Easy", "notes": "", "roll_result": "failed"},
    ]
    with patch("showrunner.runner.call_llm", side_effect=["ruling1", "ruling2"]) as mock:
        run_ruling_phase(specs)
    sr_calls = [c for c in mock.call_args_list if c.args[0] == "show_runner"]
    assert len(sr_calls) == 2


def test_run_ruling_phase_second_call_contains_first_ruling():
    from showrunner.runner import run_ruling_phase
    specs = [
        {"actor": "A", "skill": "S", "difficulty": "Easy", "notes": "", "roll_result": "passed"},
        {"actor": "B", "skill": "S", "difficulty": "Easy", "notes": "", "roll_result": "failed"},
    ]
    with patch("showrunner.runner.call_llm", side_effect=["first ruling text", "second ruling"]) as mock:
        run_ruling_phase(specs)
    second_call_msg = mock.call_args_list[1].args[2]
    assert "first ruling text" in second_call_msg


def test_run_ruling_phase_returns_dict_keyed_by_actor():
    from showrunner.runner import run_ruling_phase
    specs = [{"actor": "Z-4P0", "skill": "N", "difficulty": "Easy", "notes": "", "roll_result": "passed"}]
    with patch("showrunner.runner.call_llm", return_value="Z-4P0 succeeds."):
        result = run_ruling_phase(specs)
    assert result == {"Z-4P0": "Z-4P0 succeeds."}


# ---------------------------------------------------------------------------
# run_narrative_phase
# ---------------------------------------------------------------------------

def test_run_narrative_phase_calls_show_runner_once():
    from showrunner.runner import run_narrative_phase
    with patch("showrunner.runner.call_llm", return_value="prose") as mock:
        run_narrative_phase("summaries", "checks", "results")
    sr_calls = [c for c in mock.call_args_list if c.args[0] == "show_runner"]
    assert len(sr_calls) == 1


def test_run_narrative_phase_user_message_contains_all_three_inputs():
    from showrunner.runner import run_narrative_phase
    with patch("showrunner.runner.call_llm", return_value="prose") as mock:
        run_narrative_phase("summary text", "check text", "result text")
    user_msg = mock.call_args_list[0].args[2]
    assert "summary text" in user_msg
    assert "check text" in user_msg
    assert "result text" in user_msg


def test_run_narrative_phase_returns_llm_output():
    from showrunner.runner import run_narrative_phase
    with patch("showrunner.runner.call_llm", return_value="The battle concludes."):
        result = run_narrative_phase("s", "c", "r")
    assert result == "The battle concludes."


# ---------------------------------------------------------------------------
# run_last_action_phase
# ---------------------------------------------------------------------------

def test_run_last_action_phase_empty_returns_empty_dict():
    from showrunner.runner import run_last_action_phase
    result = run_last_action_phase({})
    assert result == {}


def test_run_last_action_phase_calls_narrator_once_per_actor():
    from showrunner.runner import run_last_action_phase
    with patch("showrunner.runner.call_llm", side_effect=["act1", "act2"]) as mock:
        run_last_action_phase({"bargos": "summary1", "kaelen": "summary2"})
    narrator_calls = [c for c in mock.call_args_list if c.args[0] == "narrator"]
    assert len(narrator_calls) == 2


def test_run_last_action_phase_bargos_call_does_not_contain_kaelen_summary():
    from showrunner.runner import run_last_action_phase
    with patch("showrunner.runner.call_llm", side_effect=["bargos last", "kaelen last"]) as mock:
        run_last_action_phase({"bargos": "Bargos threatened Z-4P0.", "kaelen": "Kaelen took cover."})
    bargos_call = mock.call_args_list[0]
    user_msg = bargos_call.args[2]
    assert "Bargos threatened Z-4P0." in user_msg
    assert "Kaelen took cover." not in user_msg


def test_run_last_action_phase_returns_dict_keyed_by_actor():
    from showrunner.runner import run_last_action_phase
    with patch("showrunner.runner.call_llm", side_effect=["Bargos spoke.", "Kaelen fled."]):
        result = run_last_action_phase({"bargos": "s1", "kaelen": "s2"})
    assert result == {"bargos": "Bargos spoke.", "kaelen": "Kaelen fled."}


# ---------------------------------------------------------------------------
# run_scribe_phase
# ---------------------------------------------------------------------------

def test_run_scribe_phase_calls_scribe_once():
    from showrunner.runner import run_scribe_phase
    with patch("showrunner.runner.call_llm", return_value="log entry") as mock:
        run_scribe_phase("scribe ctx", "full turn summary")
    scribe_calls = [c for c in mock.call_args_list if c.args[0] == "scribe"]
    assert len(scribe_calls) == 1


def test_run_scribe_phase_returns_llm_output():
    from showrunner.runner import run_scribe_phase
    with patch("showrunner.runner.call_llm", return_value="2026-05-13 — Bargos makes demands."):
        result = run_scribe_phase("ctx", "summary")
    assert result == "2026-05-13 — Bargos makes demands."
