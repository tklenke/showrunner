# ABOUTME: Scribe agent — state keeper; writes session log and party stats after each resolved action.
# ABOUTME: Runs on Alien (Llama 3.2 3B); has exclusive write access to state/ files.

from crewai import Agent

from showrunner.config import load_agent_configs
from showrunner.tools.agent_tools import consult_narrator, read_state, write_state


def create_scribe() -> Agent:
    """Return the Scribe agent (Alien)."""
    cfg = load_agent_configs()["scribe"]
    return Agent(
        role=cfg["role"],
        goal=cfg["goal"],
        backstory=cfg["backstory"],
        llm=cfg["llm"],
        tools=[read_state, write_state, consult_narrator],
        allow_delegation=cfg["allow_delegation"],
        verbose=cfg["verbose"],
    )
