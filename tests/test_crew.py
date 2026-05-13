# ABOUTME: Tests for CrewAI crew assembly — verifies agents, process, and manager wiring.
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


def test_crew_process_is_hierarchical():
    from showrunner.crew import build_crew
    crew = build_crew("A test scene.")
    assert crew.process == Process.hierarchical


def test_crew_has_four_worker_agents():
    from showrunner.crew import build_crew
    crew = build_crew("A test scene.")
    assert len(crew.agents) == 4


def test_crew_worker_roles():
    from showrunner.crew import build_crew
    crew = build_crew("A test scene.")
    roles = {a.role for a in crew.agents}
    assert "Narrator" in roles
    assert "NPC Voice Actor" in roles
    assert "Rules Engine" in roles
    assert "State Keeper" in roles


def test_crew_manager_is_show_runner():
    from showrunner.crew import build_crew
    crew = build_crew("A test scene.")
    assert crew.manager_agent is not None
    assert crew.manager_agent.role == "Show Runner"


def test_crew_has_tasks():
    from showrunner.crew import build_crew
    crew = build_crew("A test scene.")
    assert len(crew.tasks) > 0


def test_crew_actors_context_in_backstory():
    from showrunner.crew import build_crew
    crew = build_crew("A test scene.", actors_context="## Bargos the Hutt\nHutt crime lord.")
    actors_agent = next(a for a in crew.agents if a.role == "NPC Voice Actor")
    assert "Bargos the Hutt" in actors_agent.backstory
