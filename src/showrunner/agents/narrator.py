# ABOUTME: Narrator agent — GM voice for prose narration, atmosphere, scene descriptions.
# ABOUTME: Receives beat decisions from Show Runner; renders context strings for the narrator.


def render_narrator_context(
    scene: dict,
    beat_id: str,
    last_actions: dict | None = None,
    party_stats: dict | None = None,
) -> str:
    """Build the Narrator's task context for the given beat."""
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
    lines.append("## Last Actions")
    if last_actions:
        for actor, action in last_actions.items():
            lines.append(f"{actor}: {action}")
    else:
        lines.append("None yet.")

    lines.append("")
    lines.append("## Party Status")
    characters = (party_stats or {}).get("characters", {})
    for name, stats in characters.items():
        lines.append(f"{name}: wounds {stats.get('wounds', 0)}, strain {stats.get('strain', 0)}")

    return "\n".join(lines)


