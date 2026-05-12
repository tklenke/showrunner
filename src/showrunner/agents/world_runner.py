# ABOUTME: World Runner agent — GM voice for prose narration, atmosphere, scene descriptions.
# ABOUTME: Runs on Sardinia (Llama 3.1 8B); receives beat decisions from Narrator.

from crewai import Agent

from showrunner.config import load_agent_configs
from showrunner.tools.agent_tools import consult_narrator, read_state


def render_world_runner_context(scene: dict, beat_id: str) -> str:
    """Build the World Runner's task context for the given beat.

    Always includes the opening read_aloud (World Runner delivers this verbatim at
    scene entry). Adds the beat-specific world_runner_notes as narration guidance.
    """
    loc = scene["location"]
    lines = [
        f"## Scene: {loc['name']}",
        "",
        "### Opening Narration (deliver verbatim at scene entry)",
        loc["read_aloud"].strip(),
        "",
    ]

    beat = next((b for b in scene.get("beats", []) if b["id"] == beat_id), None)
    if beat:
        lines.append(f"### Current Beat: {beat['title']}")
        lines.append(beat["world_runner_notes"].strip())

    return "\n".join(lines)


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
