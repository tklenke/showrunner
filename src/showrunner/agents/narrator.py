# ABOUTME: Narrator agent — GM voice for prose narration, atmosphere, scene descriptions.
# ABOUTME: Runs on Sardinia (Llama 3.1 8B); receives beat decisions from Show Runner.

from crewai import Agent

from showrunner.config import load_agent_configs
from showrunner.tools.agent_tools import consult_show_runner


def render_narrator_context(
    scene: dict,
    beat_id: str,
    last_action: str = "",
    party_stats: dict | None = None,
) -> str:
    """Build the Narrator's task context for the given beat.

    Always includes the opening read_aloud (Narrator delivers this verbatim at
    scene entry). Adds beat-specific narrator_notes, the last player action, and
    current party status so the Narrator has full runtime context.
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
        lines.append(beat["narrator_notes"].strip())

    lines.append("")
    lines.append("## Last Player Action")
    lines.append(last_action if last_action else "None yet.")

    lines.append("")
    lines.append("## Party Status")
    characters = (party_stats or {}).get("characters", {})
    for name, stats in characters.items():
        lines.append(f"{name}: wounds {stats.get('wounds', 0)}, strain {stats.get('strain', 0)}")

    return "\n".join(lines)


def create_narrator() -> Agent:
    """Return the Narrator agent (Sardinia)."""
    cfg = load_agent_configs()["narrator"]
    return Agent(
        role=cfg["role"],
        goal=cfg["goal"],
        backstory=cfg["backstory"],
        llm=cfg["llm"],
        tools=[consult_show_runner],
        allow_delegation=cfg["allow_delegation"],
        verbose=cfg["verbose"],
    )
