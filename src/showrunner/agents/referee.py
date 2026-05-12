# ABOUTME: Referee agent — rules engine for dice pool construction, skill check difficulty, combat.
# ABOUTME: Runs on Alien (Llama 3.2 3B); uses dice_roller tool and rules_lookup tool.

from crewai import Agent

from showrunner.config import load_agent_configs
from showrunner.tools.agent_tools import consult_narrator, read_state, roll_dice


def create_referee() -> Agent:
    """Return the Referee agent (Alien)."""
    cfg = load_agent_configs()["referee"]
    return Agent(
        role=cfg["role"],
        goal=cfg["goal"],
        backstory=cfg["backstory"],
        llm=cfg["llm"],
        tools=[roll_dice, read_state, consult_narrator],
        allow_delegation=cfg["allow_delegation"],
        verbose=cfg["verbose"],
    )
