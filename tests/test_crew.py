# ABOUTME: Tests for CrewAI crew assembly — verifies three phase crew builders.
# ABOUTME: build_npc_crew, build_pc_crew, build_resolution_crew structural tests only.

import os
import pytest
pytest.importorskip("crewai", reason="crewai removed in 4.15")
from crewai import Crew, Process


@pytest.fixture(autouse=True)
def gemini_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")


# ---------------------------------------------------------------------------
# build_npc_crew
# ---------------------------------------------------------------------------

def test_build_npc_crew_returns_crew():
    from showrunner.crew import build_npc_crew
    crew = build_npc_crew("A test scene.", "Narrator context.", {})
    assert isinstance(crew, Crew)


def test_npc_crew_process_is_sequential():
    from showrunner.crew import build_npc_crew
    crew = build_npc_crew("A test scene.", "", {})
    assert crew.process == Process.sequential


def test_npc_crew_has_no_manager_agent():
    from showrunner.crew import build_npc_crew
    crew = build_npc_crew("A test scene.", "", {})
    assert crew.manager_agent is None


def test_npc_crew_with_no_npcs_has_two_tasks():
    from showrunner.crew import build_npc_crew
    crew = build_npc_crew("A test scene.", "", {})
    assert len(crew.tasks) == 2


def test_npc_crew_with_two_npcs_has_four_tasks():
    from showrunner.crew import build_npc_crew
    crew = build_npc_crew("scene", "", {"npc1": "NPC One", "npc2": "NPC Two"})
    assert len(crew.tasks) == 4


def test_npc_crew_task_order():
    from showrunner.crew import build_npc_crew
    crew = build_npc_crew("scene", "", {"bargos": "Bargos data"})
    roles = [t.agent.role for t in crew.tasks]
    assert roles == ["Show Runner", "Narrator", "NPC Voice Actor"]


def test_npc_crew_sr_context_in_task():
    from showrunner.crew import build_npc_crew
    crew = build_npc_crew("The Hutt awaits.", "", {})
    assert "The Hutt awaits." in crew.tasks[0].description


def test_npc_crew_narrator_context_in_task():
    from showrunner.crew import build_npc_crew
    crew = build_npc_crew("scene", "It was a dark night.", {})
    assert "It was a dark night." in crew.tasks[1].description


def test_npc_crew_npc_context_in_task():
    from showrunner.crew import build_npc_crew
    crew = build_npc_crew("scene", "", {"bargos": "## Bargos the Hutt\nHutt crime lord."})
    assert "Bargos the Hutt" in crew.tasks[2].description


def test_npc_crew_npc_task_name_is_npc_id():
    from showrunner.crew import build_npc_crew
    crew = build_npc_crew("scene", "", {"bargos": "Bargos data"})
    assert crew.tasks[2].name == "bargos"


def test_npc_crew_chains_npc_contexts():
    from showrunner.crew import build_npc_crew
    crew = build_npc_crew("scene", "", {"npc1": "NPC1 data", "npc2": "NPC2 data"})
    npc1_task = crew.tasks[2]
    npc2_task = crew.tasks[3]
    assert npc1_task not in npc1_task.context  # npc1 doesn't see itself
    assert npc1_task in npc2_task.context       # npc2 sees npc1


def test_npc_crew_narrator_sees_sr_plan():
    from showrunner.crew import build_npc_crew
    crew = build_npc_crew("scene", "", {})
    sr_task = crew.tasks[0]
    narrator_task = crew.tasks[1]
    assert sr_task in narrator_task.context


def test_npc_crew_narrator_has_callback():
    from showrunner.crew import build_npc_crew
    crew = build_npc_crew("scene", "", {})
    narrator_task = crew.tasks[1]
    assert narrator_task.callback is not None



def test_npc_crew_npc_tasks_have_callbacks():
    from showrunner.crew import build_npc_crew
    crew = build_npc_crew("scene", "", {"bargos": "data", "genko": "data"})
    npc_tasks = crew.tasks[2:]
    assert all(t.callback is not None for t in npc_tasks)


def test_npc_crew_show_runner_task_has_no_callback():
    from showrunner.crew import build_npc_crew
    crew = build_npc_crew("scene", "", {})
    sr_task = crew.tasks[0]
    assert sr_task.callback is None


# ---------------------------------------------------------------------------
# build_pc_crew
# ---------------------------------------------------------------------------

def test_build_pc_crew_returns_crew():
    from showrunner.crew import build_pc_crew
    crew = build_pc_crew("NPC wave text.", {"kaelen": "Kaelen data"}, "Player ran.")
    assert isinstance(crew, Crew)


def test_pc_crew_with_no_ai_pcs_returns_none():
    from showrunner.crew import build_pc_crew
    assert build_pc_crew("NPC wave.", {}, "Player ran.") is None


def test_pc_crew_with_one_ai_pc_has_one_task():
    from showrunner.crew import build_pc_crew
    crew = build_pc_crew("NPC wave.", {"kaelen": "Kaelen data"}, "Player ran.")
    assert len(crew.tasks) == 1


def test_pc_crew_kaelen_sees_npc_wave():
    from showrunner.crew import build_pc_crew
    crew = build_pc_crew("Bargos said hello.", {"kaelen": "Kaelen data"}, "I sprint left.")
    kaelen_task = crew.tasks[0]
    assert "Bargos said hello." in kaelen_task.description


def test_pc_crew_kaelen_sees_player_action():
    from showrunner.crew import build_pc_crew
    crew = build_pc_crew("NPC wave.", {"kaelen": "Kaelen data"}, "I sprint left.")
    kaelen_task = crew.tasks[0]
    assert "I sprint left." in kaelen_task.description


def test_pc_crew_has_no_show_runner_task():
    from showrunner.crew import build_pc_crew
    crew = build_pc_crew("NPC wave.", {"kaelen": "Kaelen data"}, "Player ran.")
    roles = [t.agent.role for t in crew.tasks]
    assert "Show Runner" not in roles


def test_pc_crew_ai_pc_tasks_have_callbacks():
    from showrunner.crew import build_pc_crew
    crew = build_pc_crew("NPC wave.", {"kaelen": "Kaelen data", "rex": "Rex data"}, "Player ran.")
    assert all(t.callback is not None for t in crew.tasks)


# ---------------------------------------------------------------------------
# build_resolution_crew
# ---------------------------------------------------------------------------

CHECK_SPEC = {
    "actor": "Z-4P0",
    "skill": "Negotiation",
    "characteristic": "Presence",
    "difficulty": "Opposed vs Bargos Cool",
    "notes": "+1 Boost",
}

CHECK_SPEC_2 = {
    "actor": "Kaelen",
    "skill": "Athletics",
    "characteristic": "Brawn",
    "difficulty": "Average",
    "notes": "Seeking cover",
}


def test_build_resolution_crew_returns_crew():
    from showrunner.crew import build_resolution_crew
    crew = build_resolution_crew([CHECK_SPEC], "Scribe ctx.", "Turn summary.")
    assert isinstance(crew, Crew)


def test_resolution_crew_empty_specs_has_only_scribe():
    from showrunner.crew import build_resolution_crew
    crew = build_resolution_crew([], "Scribe ctx.", "Turn summary.")
    assert len(crew.tasks) == 1
    assert crew.tasks[0].agent.role == "State Keeper"


def test_resolution_crew_one_spec_has_referee_plus_scribe():
    from showrunner.crew import build_resolution_crew
    crew = build_resolution_crew([CHECK_SPEC], "Scribe ctx.", "Turn summary.")
    assert len(crew.tasks) == 2
    roles = [t.agent.role for t in crew.tasks]
    assert roles == ["Rules Engine", "State Keeper"]


def test_resolution_crew_two_specs_has_two_referees_plus_scribe():
    from showrunner.crew import build_resolution_crew
    crew = build_resolution_crew([CHECK_SPEC, CHECK_SPEC_2], "Scribe ctx.", "Turn summary.")
    assert len(crew.tasks) == 3
    roles = [t.agent.role for t in crew.tasks]
    assert roles == ["Rules Engine", "Rules Engine", "State Keeper"]


def test_resolution_crew_referee_task_contains_check_spec():
    from showrunner.crew import build_resolution_crew
    crew = build_resolution_crew([CHECK_SPEC], "Scribe ctx.", "Turn summary.")
    ref_task = crew.tasks[0]
    assert "Negotiation" in ref_task.description
    assert "Z-4P0" in ref_task.description


def test_resolution_crew_referee_tasks_chained():
    from showrunner.crew import build_resolution_crew
    crew = build_resolution_crew([CHECK_SPEC, CHECK_SPEC_2], "Scribe ctx.", "Turn summary.")
    ref1_task = crew.tasks[0]
    ref2_task = crew.tasks[1]
    assert ref1_task in ref2_task.context


def test_resolution_crew_scribe_sees_all_referee_tasks():
    from showrunner.crew import build_resolution_crew
    crew = build_resolution_crew([CHECK_SPEC, CHECK_SPEC_2], "Scribe ctx.", "Turn summary.")
    scribe_task = crew.tasks[-1]
    context_roles = {t.agent.role for t in scribe_task.context}
    assert "Rules Engine" in context_roles


def test_resolution_crew_scribe_sees_turn_summary():
    from showrunner.crew import build_resolution_crew
    crew = build_resolution_crew([], "Scribe ctx.", "Bargos spoke ominously.")
    scribe_task = crew.tasks[0]
    assert "Bargos spoke ominously." in scribe_task.description


# ---------------------------------------------------------------------------
# _parse_check_specs
# ---------------------------------------------------------------------------

def test_parse_check_specs_no_checks():
    from showrunner.orchestrator import _parse_check_specs
    assert _parse_check_specs("NO_CHECKS") == []


def test_parse_check_specs_single_check():
    from showrunner.orchestrator import _parse_check_specs
    text = "CHECKS:\n1. Z-4P0 | Negotiation | Presence | Opposed vs Bargos Cool | +1 Boost\nCHECKS_END"
    specs = _parse_check_specs(text)
    assert len(specs) == 1
    assert specs[0]["actor"] == "Z-4P0"
    assert specs[0]["skill"] == "Negotiation"
    assert specs[0]["characteristic"] == "Presence"
    assert specs[0]["difficulty"] == "Opposed vs Bargos Cool"
    assert specs[0]["notes"] == "+1 Boost"


def test_parse_check_specs_two_checks():
    from showrunner.orchestrator import _parse_check_specs
    text = (
        "CHECKS:\n"
        "1. Z-4P0 | Negotiation | Presence | Opposed vs Bargos Cool | +1 Boost\n"
        "2. Kaelen | Athletics | Brawn | Average | Seeking cover\n"
        "CHECKS_END"
    )
    specs = _parse_check_specs(text)
    assert len(specs) == 2
    assert specs[1]["actor"] == "Kaelen"


def test_parse_check_specs_tolerates_surrounding_text():
    from showrunner.orchestrator import _parse_check_specs
    text = "Looking at all the actions:\n\nCHECKS:\n1. Z-4P0 | Brawl | Brawn | Easy | None\nCHECKS_END\n\nThat's all."
    specs = _parse_check_specs(text)
    assert len(specs) == 1
    assert specs[0]["skill"] == "Brawl"


def test_parse_check_specs_missing_notes_defaults_empty():
    from showrunner.orchestrator import _parse_check_specs
    text = "CHECKS:\n1. Z-4P0 | Brawl | Brawn | Easy\nCHECKS_END"
    specs = _parse_check_specs(text)
    assert specs[0]["notes"] == ""


# ---------------------------------------------------------------------------
# build_summary_crew (3a)
# ---------------------------------------------------------------------------

def test_build_summary_crew_returns_crew():
    from showrunner.crew import build_summary_crew
    crew = build_summary_crew({"bargos": "Said something threatening."})
    assert isinstance(crew, Crew)


def test_summary_crew_one_task_per_actor():
    from showrunner.crew import build_summary_crew
    crew = build_summary_crew({"bargos": "Spoke.", "kae": "Moved."})
    assert len(crew.tasks) == 2


def test_summary_crew_task_names_match_actor_ids():
    from showrunner.crew import build_summary_crew
    crew = build_summary_crew({"bargos": "Spoke.", "kae": "Moved."})
    assert {t.name for t in crew.tasks} == {"bargos", "kae"}


def test_summary_crew_task_contains_action_text():
    from showrunner.crew import build_summary_crew
    crew = build_summary_crew({"bargos": "Said something threatening."})
    assert "Said something threatening." in crew.tasks[0].description


def test_summary_crew_uses_actor_agent():
    from showrunner.crew import build_summary_crew
    crew = build_summary_crew({"bargos": "Spoke."})
    assert crew.tasks[0].agent.role == "NPC Voice Actor"


# ---------------------------------------------------------------------------
# build_check_crew (3b)
# ---------------------------------------------------------------------------

def test_build_check_crew_returns_crew():
    from showrunner.crew import build_check_crew
    crew = build_check_crew("Bargos threatened Z-4P0.", "Z-4P0: Presence 2, Negotiation rank 1")
    assert isinstance(crew, Crew)


def test_check_crew_has_single_show_runner_task():
    from showrunner.crew import build_check_crew
    crew = build_check_crew("summaries", "stats")
    assert len(crew.tasks) == 1
    assert crew.tasks[0].agent.role == "Show Runner"


def test_check_crew_task_contains_summaries():
    from showrunner.crew import build_check_crew
    crew = build_check_crew("Bargos threatened Z-4P0.", "stats")
    assert "Bargos threatened Z-4P0." in crew.tasks[0].description


def test_check_crew_task_contains_stats():
    from showrunner.crew import build_check_crew
    crew = build_check_crew("summaries", "Z-4P0: Presence 2, Negotiation rank 1")
    assert "Z-4P0: Presence 2, Negotiation rank 1" in crew.tasks[0].description


# ---------------------------------------------------------------------------
# build_ruling_crew (3c)
# ---------------------------------------------------------------------------

RULING_SPEC = {
    "actor": "Z-4P0",
    "skill": "Negotiation",
    "characteristic": "Presence",
    "char_value": 2,
    "skill_rank": 1,
    "difficulty": "Opposed vs Bargos Cool",
    "notes": "+1 Boost",
    "roll_result": "Roll passed: net +2 successes, +1 advantage",
}

RULING_SPEC_2 = {
    "actor": "Kaelen",
    "skill": "Athletics",
    "characteristic": "Brawn",
    "char_value": 3,
    "skill_rank": 2,
    "difficulty": "Average",
    "notes": "",
    "roll_result": "Roll failed: net -1 successes, +2 advantage",
}


def test_build_ruling_crew_returns_none_for_empty_specs():
    from showrunner.crew import build_ruling_crew
    assert build_ruling_crew([]) is None


def test_build_ruling_crew_returns_crew():
    from showrunner.crew import build_ruling_crew
    crew = build_ruling_crew([RULING_SPEC])
    assert isinstance(crew, Crew)


def test_ruling_crew_one_task_per_spec():
    from showrunner.crew import build_ruling_crew
    crew = build_ruling_crew([RULING_SPEC, RULING_SPEC_2])
    assert len(crew.tasks) == 2


def test_ruling_crew_uses_show_runner_agent():
    from showrunner.crew import build_ruling_crew
    crew = build_ruling_crew([RULING_SPEC])
    assert crew.tasks[0].agent.role == "Show Runner"


def test_ruling_crew_task_contains_roll_result():
    from showrunner.crew import build_ruling_crew
    crew = build_ruling_crew([RULING_SPEC])
    assert "Roll passed: net +2 successes" in crew.tasks[0].description


def test_ruling_crew_task_contains_check_details():
    from showrunner.crew import build_ruling_crew
    crew = build_ruling_crew([RULING_SPEC])
    assert "Z-4P0" in crew.tasks[0].description
    assert "Negotiation" in crew.tasks[0].description


def test_ruling_crew_tasks_chained():
    from showrunner.crew import build_ruling_crew
    crew = build_ruling_crew([RULING_SPEC, RULING_SPEC_2])
    assert crew.tasks[0] in crew.tasks[1].context


# ---------------------------------------------------------------------------
# build_narrative_crew (3d)
# ---------------------------------------------------------------------------

def test_build_narrative_crew_returns_crew():
    from showrunner.crew import build_narrative_crew
    crew = build_narrative_crew("summaries", "checks", "results")
    assert isinstance(crew, Crew)


def test_narrative_crew_has_single_show_runner_task():
    from showrunner.crew import build_narrative_crew
    crew = build_narrative_crew("summaries", "checks", "results")
    assert len(crew.tasks) == 1
    assert crew.tasks[0].agent.role == "Show Runner"


def test_narrative_crew_task_contains_all_three_inputs():
    from showrunner.crew import build_narrative_crew
    crew = build_narrative_crew("ACTION SUMMARIES", "CHECK LIST", "RULING RESULTS")
    desc = crew.tasks[0].description
    assert "ACTION SUMMARIES" in desc
    assert "CHECK LIST" in desc
    assert "RULING RESULTS" in desc


# ---------------------------------------------------------------------------
# build_last_action_crew (3e)
# ---------------------------------------------------------------------------

def test_build_last_action_crew_returns_none_for_empty_actors():
    from showrunner.crew import build_last_action_crew
    assert build_last_action_crew([], "s", "c", "r") is None


def test_build_last_action_crew_returns_crew():
    from showrunner.crew import build_last_action_crew
    crew = build_last_action_crew(["bargos"], "summaries", "checks", "results")
    assert isinstance(crew, Crew)


def test_last_action_crew_one_task_per_actor():
    from showrunner.crew import build_last_action_crew
    crew = build_last_action_crew(["bargos", "kae"], "s", "c", "r")
    assert len(crew.tasks) == 2


def test_last_action_crew_task_names_match_actor_ids():
    from showrunner.crew import build_last_action_crew
    crew = build_last_action_crew(["bargos", "kae"], "s", "c", "r")
    assert {t.name for t in crew.tasks} == {"bargos", "kae"}


def test_last_action_crew_uses_narrator_agent():
    from showrunner.crew import build_last_action_crew
    crew = build_last_action_crew(["bargos"], "s", "c", "r")
    assert crew.tasks[0].agent.role == "Narrator"


def test_last_action_crew_task_contains_actor_name():
    from showrunner.crew import build_last_action_crew
    crew = build_last_action_crew(["bargos"], "summaries", "checks", "results")
    assert "bargos" in crew.tasks[0].description
