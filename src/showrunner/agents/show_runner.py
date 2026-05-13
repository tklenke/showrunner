# ABOUTME: Show Runner agent — adventure state, scene beat decisions, ticking clocks, NPC knowledge.
# ABOUTME: Runs on Gemini; acts as CrewAI manager agent; consulted at scene transitions and major decisions.

from crewai import Agent

from showrunner.config import load_agent_configs


def render_show_runner_context(
    scene: dict,
    scene_state: dict,
    party_stats: dict,
    last_actions: dict | None = None,
) -> str:
    """Build the Show Runner's task context string.

    Assembles static scene content first (caches across turns) then dynamic
    runtime state (re-evaluated each turn). Mirrors the static-to-volatile
    ordering of render_actor_prompt().
    """
    lines = []

    # --- Static block (caches across all turns in this scene) ---

    loc = scene["location"]
    lines.append(f"# Scene: {scene['title']}")
    lines.append("")
    lines.append("## Location")
    lines.append(loc["name"])
    lines.append(loc["atmosphere"])
    lines.append("")

    npcs = scene.get("npcs_present", [])
    inline = scene.get("inline_npcs", [])
    if npcs or inline:
        lines.append("## NPCs Present")
        for name in npcs:
            lines.append(f"- {name}")
        for npc in inline:
            lines.append(f"- {npc['name']} ({npc['role']}): {npc['key_traits']}")
        lines.append("")

    minion_groups = scene.get("minion_groups", [])
    if minion_groups:
        lines.append("## Minion Groups")
        for group in minion_groups:
            lines.append(
                f"{group['name']} (count: {group['count']}, "
                f"soak: {group['soak']}, wound threshold: {group['wound_threshold']} per minion)"
            )
            for w in group.get("weapons", []):
                lines.append(
                    f"  Weapon: {w['name']} — damage {w['damage']}, "
                    f"crit {w['critical']}, {w['range']}"
                    + (f", {w['special']}" if w.get("special") else "")
                )
        lines.append("")

    beat_ids = [b["id"] for b in scene.get("beats", [])]
    lines.append(f"## Beat Sequence: {' → '.join(beat_ids)}")
    lines.append("")

    # --- Dynamic block (re-evaluated each turn) ---

    current_beat_id = scene_state["current_beat"]
    lines.append(f"## Current Beat: {current_beat_id}")
    current_beat = next((b for b in scene.get("beats", []) if b["id"] == current_beat_id), None)
    if current_beat:
        lines.append(f"Title: {current_beat['title']}")
        lines.append(f"Trigger: {current_beat['trigger']}")
        lines.append(f"Direction: {current_beat['show_runner_notes']}")
        for check in current_beat.get("checks", []):
            lines.append(
                f"Check: {check['skill']} difficulty {check['difficulty']}"
                + (f" — {check['notes']}" if check.get("notes") else "")
            )
    lines.append("")

    lines.append("## Current State")
    lines.append(f"Current Beat: {current_beat_id}")
    plans = scene_state.get("character_plans", {})
    if plans:
        lines.append("Character Plans:")
        for name, plan in plans.items():
            lines.append(f"  {name}: {plan}")
    lines.append("")

    characters = party_stats.get("characters", {})
    if characters:
        lines.append("## Party Status")
        for name, stats in characters.items():
            lines.append(
                f"{name}: wounds {stats.get('wounds', 0)}, strain {stats.get('strain', 0)}"
            )
        lines.append("")

    clocks = scene_state.get("ticking_clocks", [])
    if clocks:
        lines.append("## Ticking Clocks")
        for clock in clocks:
            lines.append(
                f"{clock.get('label', clock['id'])}: "
                f"{clock.get('destroyed', 0)}/{clock.get('max', '?')} destroyed"
            )
        lines.append("")

    lines.append("## Last Actions")
    if last_actions:
        for actor, action in last_actions.items():
            lines.append(f"{actor}: {action}")
    else:
        lines.append("None yet.")

    return "\n".join(lines)


def create_show_runner() -> Agent:
    """Return the Show Runner agent (Gemini, manager)."""
    cfg = load_agent_configs()["show_runner"]
    return Agent(
        role=cfg["role"],
        goal=cfg["goal"],
        backstory=cfg["backstory"],
        llm=cfg["llm"],
        tools=[],
        allow_delegation=cfg["allow_delegation"],
        verbose=cfg["verbose"],
    )
