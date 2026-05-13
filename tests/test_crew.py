# ABOUTME: Tests for CrewAI crew assembly — verifies three phase crew builders.
# ABOUTME: build_npc_crew, build_pc_crew, build_resolution_crew structural tests only.

import os
import pytest
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
