# ABOUTME: Tests for CrewAI crew assembly — verifies agents, tasks, process, and context wiring.
# ABOUTME: Does not make LLM calls; tests structural configuration only.

import os
import pytest
from crewai import Crew, Process


@pytest.fixture(autouse=True)
def gemini_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")


def test_build_crew_returns_crew():
    from showrunner.crew import build_crew
    crew = build_crew("A test scene.")
    assert isinstance(crew, Crew)


def test_crew_process_is_sequential():
    from showrunner.crew import build_crew
    crew = build_crew("A test scene.")
    assert crew.process == Process.sequential


def test_crew_has_no_manager_agent():
    from showrunner.crew import build_crew
    crew = build_crew("A test scene.")
    assert crew.manager_agent is None


def test_crew_with_no_npcs_has_four_tasks():
    from showrunner.crew import build_crew
    crew = build_crew("A test scene.")
    assert len(crew.tasks) == 4


def test_crew_with_one_npc_has_five_tasks():
    from showrunner.crew import build_crew
    crew = build_crew("A test scene.", actors_contexts={"bargos": "## Bargos the Hutt"})
    assert len(crew.tasks) == 5


def test_crew_with_two_npcs_has_six_tasks():
    from showrunner.crew import build_crew
    crew = build_crew("A test scene.", actors_contexts={"npc1": "# NPC One", "npc2": "# NPC Two"})
    assert len(crew.tasks) == 6


def test_crew_with_no_npcs_has_four_agents():
    from showrunner.crew import build_crew
    crew = build_crew("A test scene.")
    assert len(crew.agents) == 4


def test_crew_with_two_npcs_has_six_agents():
    from showrunner.crew import build_crew
    crew = build_crew("A test scene.", actors_contexts={"npc1": "# NPC One", "npc2": "# NPC Two"})
    assert len(crew.agents) == 6


def test_crew_agent_roles_with_npc():
    from showrunner.crew import build_crew
    crew = build_crew("A test scene.", actors_contexts={"bargos": "## Bargos"})
    roles = {a.role for a in crew.agents}
    assert "Show Runner" in roles
    assert "Narrator" in roles
    assert "NPC Voice Actor" in roles
    assert "Rules Engine" in roles
    assert "State Keeper" in roles


def test_crew_task_order_with_one_npc():
    from showrunner.crew import build_crew
    crew = build_crew("A test scene.", actors_contexts={"bargos": "## Bargos"})
    roles = [t.agent.role for t in crew.tasks]
    assert roles == ["Show Runner", "Narrator", "NPC Voice Actor", "Rules Engine", "State Keeper"]


def test_crew_task_order_with_two_npcs():
    from showrunner.crew import build_crew
    crew = build_crew("A test scene.", actors_contexts={"npc1": "NPC1", "npc2": "NPC2"})
    roles = [t.agent.role for t in crew.tasks]
    assert roles == [
        "Show Runner", "Narrator",
        "NPC Voice Actor", "NPC Voice Actor",
        "Rules Engine", "State Keeper",
    ]


def test_crew_task_order_with_no_npcs():
    from showrunner.crew import build_crew
    crew = build_crew("A test scene.")
    roles = [t.agent.role for t in crew.tasks]
    assert roles == ["Show Runner", "Narrator", "Rules Engine", "State Keeper"]


def test_crew_each_npc_gets_own_task():
    from showrunner.crew import build_crew
    crew = build_crew(
        "A test scene.",
        actors_contexts={"npc1": "# NPC One data", "npc2": "# NPC Two data"},
    )
    npc_tasks = crew.tasks[2:4]
    descs = [t.description for t in npc_tasks]
    assert any("NPC One data" in d for d in descs)
    assert any("NPC Two data" in d for d in descs)


def test_crew_scribe_task_has_full_context():
    from showrunner.crew import build_crew
    crew = build_crew("A test scene.", actors_contexts={"bargos": "## Bargos"})
    scribe_task = crew.tasks[-1]
    context_agents = {t.agent.role for t in scribe_task.context}
    assert "Show Runner" in context_agents
    assert "Narrator" in context_agents
    assert "NPC Voice Actor" in context_agents
    assert "Rules Engine" in context_agents


def test_crew_referee_context_includes_npc_tasks():
    from showrunner.crew import build_crew
    crew = build_crew("A test scene.", actors_contexts={"bargos": "## Bargos"})
    referee_task = crew.tasks[-2]
    context_agents = {t.agent.role for t in referee_task.context}
    assert "NPC Voice Actor" in context_agents


def test_crew_show_runner_context_in_task():
    from showrunner.crew import build_crew
    crew = build_crew("The Hutt awaits.")
    assert "The Hutt awaits." in crew.tasks[0].description


def test_crew_actors_context_in_task():
    from showrunner.crew import build_crew
    crew = build_crew(
        "A test scene.",
        actors_contexts={"bargos": "## Bargos the Hutt\nHutt crime lord."},
    )
    npc_task = crew.tasks[2]
    assert "Bargos the Hutt" in npc_task.description
