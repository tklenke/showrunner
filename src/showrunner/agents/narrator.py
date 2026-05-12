# ABOUTME: Narrator agent — adventure state, scene beat decisions, ticking clocks, NPC knowledge tracking.
# ABOUTME: Runs on Gemini; acts as CrewAI manager agent; consulted at scene transitions and major decisions.

from crewai import Agent

from showrunner.config import load_agent_configs
from showrunner.tools.agent_tools import ask_player


def create_narrator() -> Agent:
    """Return the Narrator agent (Gemini, manager)."""
    cfg = load_agent_configs()["narrator"]
    return Agent(
        role=cfg["role"],
        goal=cfg["goal"],
        backstory=cfg["backstory"],
        llm=cfg["llm"],
        tools=[ask_player],
        allow_delegation=cfg["allow_delegation"],
        verbose=cfg["verbose"],
    )
