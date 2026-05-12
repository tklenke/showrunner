# ABOUTME: World Runner agent — GM voice for prose narration, atmosphere, scene descriptions.
# ABOUTME: Runs on Sardinia (Llama 3.1 8B); receives beat decisions from Narrator.

from crewai import Agent

from showrunner.config import load_agent_configs
from showrunner.tools.agent_tools import consult_narrator, read_state


def create_world_runner() -> Agent:
    """Return the World Runner agent (Sardinia)."""
    cfg = load_agent_configs()["world_runner"]
    return Agent(
        role=cfg["role"],
        goal=cfg["goal"],
        backstory=cfg["backstory"],
        llm=cfg["llm"],
        tools=[read_state, consult_narrator],
        allow_delegation=cfg["allow_delegation"],
        verbose=cfg["verbose"],
    )
