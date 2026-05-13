# ABOUTME: Scribe agent — state keeper; writes session log and party stats after each resolved action.
# ABOUTME: Runs on Alien (Llama 3.2 3B); has exclusive write access to state/ files.

from crewai import Agent

from showrunner.config import load_agent_configs


def render_scribe_context(scene_state: dict, party_stats: dict) -> str:
    """Build current-state snapshot for the Scribe so it knows what to update and what to leave alone."""
    characters = party_stats.get("characters", {})
    char_lines = [
        f"{name}: wounds {stats.get('wounds', 0)}, strain {stats.get('strain', 0)}"
        for name, stats in characters.items()
    ]

    clocks = scene_state.get("ticking_clocks", [])
    clocks_str = str(clocks) if clocks else "none"

    plans = scene_state.get("character_plans", {})
    plans_str = str(plans) if plans else "none"

    lines = [
        "## Current State (read before writing)",
        "",
        "### party_stats.yaml — update wounds and strain after each resolved action",
        *char_lines,
        "",
        "### scene_state.yaml — update character_plans and ticking_clocks only",
        f"Current beat: {scene_state.get('current_beat', '')}  ← DO NOT CHANGE THIS."
        " Beat progression is Show Runner only.",
        f"Ticking clocks: {clocks_str}",
        f"Character plans: {plans_str}",
        "",
        "### session_log.md — append a one-sentence narrative summary of what happened",
        'Format: "YYYY-MM-DD HH:MM — <what happened>"',
    ]
    return "\n".join(lines)


def create_scribe() -> Agent:
    """Return the Scribe agent (Alien)."""
    cfg = load_agent_configs()["scribe"]
    return Agent(
        role=cfg["role"],
        goal=cfg["goal"],
        backstory=cfg["backstory"],
        llm=cfg["llm"],
        tools=[],
        allow_delegation=cfg["allow_delegation"],
        verbose=cfg["verbose"],
    )
