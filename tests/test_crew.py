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


def test_crew_has_five_agents():
    from showrunner.crew import build_crew
    crew = build_crew("A test scene.")
    assert len(crew.agents) == 5


def test_crew_agent_roles():
    from showrunner.crew import build_crew
    crew = build_crew("A test scene.")
    roles = {a.role for a in crew.agents}
    assert "Show Runner" in roles
    assert "Narrator" in roles
    assert "NPC Voice Actor" in roles
    assert "Rules Engine" in roles
    assert "State Keeper" in roles


def test_crew_has_five_tasks():
    from showrunner.crew import build_crew
    crew = build_crew("A test scene.")
    assert len(crew.tasks) == 5


def test_crew_task_agents_in_order():
    from showrunner.crew import build_crew
    crew = build_crew("A test scene.")
    roles = [t.agent.role for t in crew.tasks]
    assert roles == ["Show Runner", "Narrator", "NPC Voice Actor", "Rules Engine", "State Keeper"]


def test_crew_scribe_task_has_full_context():
    from showrunner.crew import build_crew
    crew = build_crew("A test scene.")
    scribe_task = crew.tasks[4]
    context_agents = {t.agent.role for t in scribe_task.context}
    assert "Show Runner" in context_agents
    assert "Narrator" in context_agents
    assert "NPC Voice Actor" in context_agents
    assert "Rules Engine" in context_agents


def test_crew_show_runner_context_in_task():
    from showrunner.crew import build_crew
    crew = build_crew("The Hutt awaits.", narrator_context="")
    assert "The Hutt awaits." in crew.tasks[0].description


def test_crew_actors_context_in_task():
    from showrunner.crew import build_crew
    crew = build_crew("A test scene.", actors_context="## Bargos the Hutt\nHutt crime lord.")
    actors_task = crew.tasks[2]
    assert "Bargos the Hutt" in actors_task.description
