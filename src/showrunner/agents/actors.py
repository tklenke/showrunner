# ABOUTME: Actors agent — voices NPCs with decisions, dialogue, and physical responses.
# ABOUTME: Runs on Sardinia (Llama 3.1 8B); receives rendered character prompt from render_actor_prompt().

from crewai import Agent

from showrunner.config import load_agent_configs
from showrunner.tools.agent_tools import consult_narrator, read_state


def render_actor_prompt(character_yaml: dict, persona_md: str, scene_state: dict) -> str:
    """Build the full system prompt for an NPC actor.

    Sorts content from most static (identity, persona) to most volatile (wounds, strain)
    to maximize prompt cache reuse across turns.
    """
    raise NotImplementedError


def create_actors() -> Agent:
    """Return the Actors agent (Sardinia)."""
    cfg = load_agent_configs()["actors"]
    return Agent(
        role=cfg["role"],
        goal=cfg["goal"],
        backstory=cfg["backstory"],
        llm=cfg["llm"],
        tools=[read_state, consult_narrator],
        allow_delegation=cfg["allow_delegation"],
        verbose=cfg["verbose"],
    )
