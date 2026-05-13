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
# run_npc_wave  (2N call pattern: actors + narrator per NPC)
# ---------------------------------------------------------------------------

def test_run_npc_wave_makes_2n_calls_for_n_npcs(tmp_path):
    from showrunner.runner import run_npc_wave
    log_path = tmp_path / "summaries.txt"
    # 2 NPCs → 4 calls: actors, narrator, actors, narrator
    with patch("showrunner.runner.call_llm", side_effect=["npc1 out", "sum1", "npc2 out", "sum2"]) as mock:
        run_npc_wave({"a": "ctx a", "b": "ctx b"}, "beat ctx", "player action", {}, log_path)
    assert mock.call_count == 4


def test_run_npc_wave_second_npc_receives_summary_not_full_output(tmp_path):
    from showrunner.runner import run_npc_wave
    log_path = tmp_path / "summaries.txt"
    with patch("showrunner.runner.call_llm", side_effect=["FULL_OUTPUT_LONG", "short summary", "npc2 out", "sum2"]) as mock:
        run_npc_wave({"first": "ctx", "second": "ctx"}, "beat ctx", "action", {}, log_path)
    second_npc_call = [c for c in mock.call_args_list if c.args[0] == "actors"][1]
    user_msg = second_npc_call.args[2]
    assert "short summary" in user_msg
    assert "FULL_OUTPUT_LONG" not in user_msg


def test_run_npc_wave_appends_summaries_to_log_file(tmp_path):
    from showrunner.runner import run_npc_wave
    log_path = tmp_path / "summaries.txt"
    with patch("showrunner.runner.call_llm", side_effect=["out1", "summary1", "out2", "summary2"]):
        run_npc_wave({"npc_a": "ctx", "npc_b": "ctx"}, "beat ctx", "action", {}, log_path)
    content = log_path.read_text()
    assert "summary1" in content
    assert "summary2" in content


def test_run_npc_wave_returns_full_outputs_not_summaries(tmp_path):
    from showrunner.runner import run_npc_wave
    log_path = tmp_path / "summaries.txt"
    with patch("showrunner.runner.call_llm", side_effect=["FULL1", "sum1"]):
        result = run_npc_wave({"bargos": "ctx"}, "beat ctx", "action", {}, log_path)
    assert result == {"bargos": "FULL1"}


def test_run_npc_wave_empty_npcs_returns_empty_dict(tmp_path):
    from showrunner.runner import run_npc_wave
    log_path = tmp_path / "summaries.txt"
    with patch("showrunner.runner.call_llm") as mock:
        result = run_npc_wave({}, "beat ctx", "action", {}, log_path)
    assert result == {}
    mock.assert_not_called()


def test_run_npc_wave_prints_npc_output_with_id(tmp_path, capsys):
    from showrunner.runner import run_npc_wave
    log_path = tmp_path / "summaries.txt"
    with patch("showrunner.runner.call_llm", side_effect=["bargos speaks", "summary"]):
        run_npc_wave({"bargos": "ctx"}, "beat ctx", "action", {}, log_path)
    captured = capsys.readouterr()
    assert "bargos" in captured.out
    assert "bargos speaks" in captured.out


# ---------------------------------------------------------------------------
# run_companion_wave
# ---------------------------------------------------------------------------

def test_run_companion_wave_empty_returns_empty_dict():
    from showrunner.runner import run_companion_wave
    result = run_companion_wave({}, "beat ctx", "player did something")
    assert result == {}


def test_run_companion_wave_calls_actors_once_per_companion():
    from showrunner.runner import run_companion_wave
    with patch("showrunner.runner.call_llm", side_effect=["kaelen out"]) as mock:
        run_companion_wave({"kaelen": "kaelen ctx"}, "beat ctx", "player action")
    actors_calls = [c for c in mock.call_args_list if c.args[0] == "actors"]
    assert len(actors_calls) == 1


def test_run_companion_wave_user_message_contains_beat_ctx():
    from showrunner.runner import run_companion_wave
    with patch("showrunner.runner.call_llm", side_effect=["kaelen out"]) as mock:
        run_companion_wave({"kaelen": "kaelen ctx"}, "BEAT_CONTEXT_HERE", "player action")
    user_msg = mock.call_args_list[0].args[2]
    assert "BEAT_CONTEXT_HERE" in user_msg


def test_run_companion_wave_user_message_contains_player_action():
    from showrunner.runner import run_companion_wave
    with patch("showrunner.runner.call_llm", side_effect=["kaelen out"]) as mock:
        run_companion_wave({"kaelen": "kaelen ctx"}, "beat ctx", "player does X")
    user_msg = mock.call_args_list[0].args[2]
    assert "player does X" in user_msg


def test_run_companion_wave_returns_companion_outputs():
    from showrunner.runner import run_companion_wave
    with patch("showrunner.runner.call_llm", side_effect=["kaelen out"]):
        result = run_companion_wave({"kaelen": "ctx"}, "beat ctx", "action")
    assert result == {"kaelen": "kaelen out"}


# ---------------------------------------------------------------------------
# run_summaries
# ---------------------------------------------------------------------------

def test_run_summaries_calls_narrator_once_per_actor(tmp_path):
    from showrunner.runner import run_summaries
    log_path = tmp_path / "summaries.txt"
    with patch("showrunner.runner.call_llm", side_effect=["sum1", "sum2"]) as mock:
        run_summaries({"bargos": "did X", "kaelen": "did Y"}, log_path)
    narrator_calls = [c for c in mock.call_args_list if c.args[0] == "narrator"]
    assert len(narrator_calls) == 2


def test_run_summaries_user_message_contains_action_text(tmp_path):
    from showrunner.runner import run_summaries
    log_path = tmp_path / "summaries.txt"
    with patch("showrunner.runner.call_llm", side_effect=["summary"]) as mock:
        run_summaries({"bargos": "threatened Z-4P0"}, log_path)
    user_msg = mock.call_args_list[0].args[2]
    assert "threatened Z-4P0" in user_msg


def test_run_summaries_appends_to_existing_log(tmp_path):
    from showrunner.runner import run_summaries
    log_path = tmp_path / "summaries.txt"
    log_path.write_text("npc_a: existing summary\n")
    with patch("showrunner.runner.call_llm", side_effect=["pc_summary"]):
        run_summaries({"bargos": "did X"}, log_path)
    content = log_path.read_text()
    assert "existing summary" in content
    assert "pc_summary" in content


def test_run_summaries_empty_makes_no_calls_and_leaves_file_unchanged(tmp_path):
    from showrunner.runner import run_summaries
    log_path = tmp_path / "summaries.txt"
    log_path.write_text("existing\n")
    with patch("showrunner.runner.call_llm") as mock:
        run_summaries({}, log_path)
    mock.assert_not_called()
    assert log_path.read_text() == "existing\n"


# ---------------------------------------------------------------------------
# run_checks
# ---------------------------------------------------------------------------

def test_run_checks_calls_show_runner_once_per_character():
    from showrunner.runner import run_checks
    char_summaries = {"bargos": "Bargos spoke.", "kaelen": "Kaelen watched."}
    char_stats = {"bargos": "Presence 4", "kaelen": "Agility 3"}
    with patch("showrunner.runner.call_llm", side_effect=["NO_CHECKS", "NO_CHECKS"]) as mock:
        run_checks(char_summaries, char_stats)
    sr_calls = [c for c in mock.call_args_list if c.args[0] == "show_runner"]
    assert len(sr_calls) == 2


def test_run_checks_each_call_contains_only_that_chars_summary():
    from showrunner.runner import run_checks
    with patch("showrunner.runner.call_llm", side_effect=["NO_CHECKS", "NO_CHECKS"]) as mock:
        run_checks({"bargos": "Bargos spoke.", "kaelen": "Kaelen watched."}, {"bargos": "", "kaelen": ""})
    bargos_msg = mock.call_args_list[0].args[2]
    assert "Bargos spoke." in bargos_msg
    assert "Kaelen watched." not in bargos_msg


def test_run_checks_no_checks_returns_no_checks_sentinel():
    from showrunner.runner import run_checks
    with patch("showrunner.runner.call_llm", side_effect=["NO_CHECKS", "NO_CHECKS"]):
        result = run_checks({"bargos": "spoke", "kaelen": "watched"}, {"bargos": "", "kaelen": ""})
    assert result == "NO_CHECKS"


def test_run_checks_check_lines_combined_into_single_output():
    from showrunner.runner import run_checks
    line1 = "bargos | Negotiation | Presence 4 | 2 | Average | notes"
    line2 = "kaelen | Athletics | Agility 3 | 1 | Easy | notes"
    with patch("showrunner.runner.call_llm", side_effect=[line1, line2]):
        result = run_checks({"bargos": "spoke", "kaelen": "ran"}, {"bargos": "", "kaelen": ""})
    assert line1 in result
    assert line2 in result


# ---------------------------------------------------------------------------
# run_rulings
# ---------------------------------------------------------------------------

def test_run_rulings_empty_returns_empty_dict():
    from showrunner.runner import run_rulings
    result = run_rulings([])
    assert result == {}


def test_run_rulings_calls_show_runner_once_per_spec():
    from showrunner.runner import run_rulings
    specs = [
        {"actor": "Z-4P0", "skill": "Negotiation", "difficulty": "Average", "notes": "", "roll_result": "passed"},
        {"actor": "Kaelen", "skill": "Athletics", "difficulty": "Easy", "notes": "", "roll_result": "failed"},
    ]
    with patch("showrunner.runner.call_llm", side_effect=["ruling1", "ruling2"]) as mock:
        run_rulings(specs)
    sr_calls = [c for c in mock.call_args_list if c.args[0] == "show_runner"]
    assert len(sr_calls) == 2


def test_run_rulings_on_ruling_callback_called_after_each_ruling():
    from showrunner.runner import run_rulings
    specs = [
        {"actor": "A", "skill": "S", "difficulty": "Easy", "notes": "", "roll_result": "passed"},
        {"actor": "B", "skill": "S", "difficulty": "Easy", "notes": "", "roll_result": "failed"},
    ]
    called_with = []
    def on_ruling(actor, text):
        called_with.append((actor, text))
        return f"updated stats after {actor}"
    with patch("showrunner.runner.call_llm", side_effect=["ruling1", "ruling2"]):
        run_rulings(specs, on_ruling=on_ruling)
    assert called_with[0] == ("A", "ruling1")
    assert called_with[1] == ("B", "ruling2")


def test_run_rulings_second_call_contains_context_from_on_ruling():
    from showrunner.runner import run_rulings
    specs = [
        {"actor": "A", "skill": "S", "difficulty": "Easy", "notes": "", "roll_result": "passed"},
        {"actor": "B", "skill": "S", "difficulty": "Easy", "notes": "", "roll_result": "failed"},
    ]
    def on_ruling(actor, text):
        return f"UPDATED_STATS_FROM_{actor}"
    with patch("showrunner.runner.call_llm", side_effect=["ruling1", "ruling2"]) as mock:
        run_rulings(specs, on_ruling=on_ruling)
    second_call_msg = mock.call_args_list[1].args[2]
    assert "UPDATED_STATS_FROM_A" in second_call_msg


def test_run_rulings_returns_dict_keyed_by_actor():
    from showrunner.runner import run_rulings
    specs = [{"actor": "Z-4P0", "skill": "N", "difficulty": "Easy", "notes": "", "roll_result": "passed"}]
    with patch("showrunner.runner.call_llm", return_value="Z-4P0 succeeds."):
        result = run_rulings(specs)
    assert result == {"Z-4P0": "Z-4P0 succeeds."}


# ---------------------------------------------------------------------------
# run_narrative
# ---------------------------------------------------------------------------

def test_run_narrative_calls_show_runner_once():
    from showrunner.runner import run_narrative
    with patch("showrunner.runner.call_llm", return_value="prose") as mock:
        run_narrative("summaries", "checks", "results")
    sr_calls = [c for c in mock.call_args_list if c.args[0] == "show_runner"]
    assert len(sr_calls) == 1


def test_run_narrative_user_message_contains_all_three_inputs():
    from showrunner.runner import run_narrative
    with patch("showrunner.runner.call_llm", return_value="prose") as mock:
        run_narrative("summary text", "check text", "result text")
    user_msg = mock.call_args_list[0].args[2]
    assert "summary text" in user_msg
    assert "check text" in user_msg
    assert "result text" in user_msg


def test_run_narrative_returns_llm_output():
    from showrunner.runner import run_narrative
    with patch("showrunner.runner.call_llm", return_value="The battle concludes."):
        result = run_narrative("s", "c", "r")
    assert result == "The battle concludes."


# ---------------------------------------------------------------------------
# run_last_actions
# ---------------------------------------------------------------------------

def test_run_last_actions_empty_returns_empty_dict():
    from showrunner.runner import run_last_actions
    result = run_last_actions({})
    assert result == {}


def test_run_last_actions_calls_narrator_once_per_actor():
    from showrunner.runner import run_last_actions
    with patch("showrunner.runner.call_llm", side_effect=["act1", "act2"]) as mock:
        run_last_actions({"bargos": "summary1", "kaelen": "summary2"})
    narrator_calls = [c for c in mock.call_args_list if c.args[0] == "narrator"]
    assert len(narrator_calls) == 2


def test_run_last_actions_bargos_call_does_not_contain_kaelen_summary():
    from showrunner.runner import run_last_actions
    with patch("showrunner.runner.call_llm", side_effect=["bargos last", "kaelen last"]) as mock:
        run_last_actions({"bargos": "Bargos threatened Z-4P0.", "kaelen": "Kaelen took cover."})
    bargos_call = mock.call_args_list[0]
    user_msg = bargos_call.args[2]
    assert "Bargos threatened Z-4P0." in user_msg
    assert "Kaelen took cover." not in user_msg


def test_run_last_actions_returns_dict_keyed_by_actor():
    from showrunner.runner import run_last_actions
    with patch("showrunner.runner.call_llm", side_effect=["Bargos spoke.", "Kaelen fled."]):
        result = run_last_actions({"bargos": "s1", "kaelen": "s2"})
    assert result == {"bargos": "Bargos spoke.", "kaelen": "Kaelen fled."}


# ---------------------------------------------------------------------------
# run_beat_opener
# ---------------------------------------------------------------------------

BEAT = {
    "id": "summons",
    "title": "The Summons",
    "show_runner_notes": "SR hint.",
    "narrator_notes": "Narrator hint.",
}


def test_run_beat_opener_calls_narrator_once():
    from showrunner.runner import run_beat_opener
    with patch("showrunner.runner.call_llm", return_value="The door opens.") as mock:
        run_beat_opener(BEAT, "")
    narrator_calls = [c for c in mock.call_args_list if c.args[0] == "narrator"]
    assert len(narrator_calls) == 1


def test_run_beat_opener_prints_output(capsys):
    from showrunner.runner import run_beat_opener
    with patch("showrunner.runner.call_llm", return_value="You enter the chamber."):
        run_beat_opener(BEAT, "")
    captured = capsys.readouterr()
    assert "You enter the chamber." in captured.out


def test_run_beat_opener_includes_last_log_entry_in_message():
    from showrunner.runner import run_beat_opener
    with patch("showrunner.runner.call_llm", return_value="ok") as mock:
        run_beat_opener(BEAT, "Z-4P0 arrived safely.")
    user_msg = mock.call_args_list[0].args[2]
    assert "Z-4P0 arrived safely." in user_msg


def test_run_beat_opener_empty_last_log_does_not_crash():
    from showrunner.runner import run_beat_opener
    with patch("showrunner.runner.call_llm", return_value="ok"):
        run_beat_opener(BEAT, "")  # must not raise


# ---------------------------------------------------------------------------
# run_plan_update
# ---------------------------------------------------------------------------

_CHARS = {"bargos": "Bargos context", "kaelen": "Kaelen context"}


def test_run_plan_update_fires_overall_plan_call_once():
    from showrunner.runner import run_plan_update
    with patch("showrunner.runner.call_llm", side_effect=["overall plan", "plan_b", "plan_k"]) as mock:
        run_plan_update(_CHARS, "summaries", "results", {"bargos": "last act"})
    sr_calls = [c for c in mock.call_args_list if c.args[0] == "show_runner"]
    assert len(sr_calls) == 3  # 1 overall + 2 individual


def test_run_plan_update_fires_one_individual_call_per_character():
    from showrunner.runner import run_plan_update
    with patch("showrunner.runner.call_llm", side_effect=["overall", "plan1", "plan2"]) as mock:
        run_plan_update(_CHARS, "summaries", "results", {})
    assert mock.call_count == 3


def test_run_plan_update_returns_dict_keyed_by_character():
    from showrunner.runner import run_plan_update
    with patch("showrunner.runner.call_llm", side_effect=["overall", "bargos_plan", "kaelen_plan"]):
        result = run_plan_update(_CHARS, "summaries", "results", {})
    assert set(result.keys()) == {"bargos", "kaelen"}
    assert result["bargos"] == "bargos_plan"


def test_run_plan_update_individual_call_contains_overall_plan():
    from showrunner.runner import run_plan_update
    with patch("showrunner.runner.call_llm", side_effect=["OVERALL_PLAN_TEXT", "p1", "p2"]) as mock:
        run_plan_update(_CHARS, "summaries", "results", {})
    individual_call = mock.call_args_list[1]
    user_msg = individual_call.args[2]
    assert "OVERALL_PLAN_TEXT" in user_msg


def test_run_plan_update_empty_characters_returns_empty_no_calls():
    from showrunner.runner import run_plan_update
    with patch("showrunner.runner.call_llm") as mock:
        result = run_plan_update({}, "summaries", "results", {})
    assert result == {}
    mock.assert_not_called()


def test_run_plan_update_writes_overall_plan_to_log_path(tmp_path):
    from showrunner.runner import run_plan_update
    log_path = tmp_path / "sr_plan.txt"
    with patch("showrunner.runner.call_llm", side_effect=["THE_OVERALL_PLAN", "p1", "p2"]):
        run_plan_update(_CHARS, "summaries", "results", {}, plan_log_path=log_path)
    assert log_path.exists()
    assert "THE_OVERALL_PLAN" in log_path.read_text()


def test_run_plan_update_empty_characters_no_file_written(tmp_path):
    from showrunner.runner import run_plan_update
    log_path = tmp_path / "sr_plan.txt"
    with patch("showrunner.runner.call_llm"):
        run_plan_update({}, "summaries", "results", {}, plan_log_path=log_path)
    assert not log_path.exists()
