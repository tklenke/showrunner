# ABOUTME: Actors agent — voices NPCs with decisions, dialogue, and physical responses.
# ABOUTME: Receives rendered character prompt from render_actor_prompt().


def render_actor_prompt(character_yaml: dict, persona_md: str, scene_state: dict) -> str:
    """Build the full system prompt for an NPC actor.

    Sorts content from most static (identity, persona) to most volatile (wounds, strain)
    to maximize prompt cache reuse across turns.
    """
    identity = character_yaml["identity"]
    char = character_yaml["characteristics"]
    derived = character_yaml["derived"]
    status = character_yaml["status"]

    lines = []

    # 1. Identity
    lines.append(f"# {identity['name']}")
    lines.append(
        f"Species: {identity['species']} | Career: {identity['career']}"
        + (f" | Specialization: {identity['specialization']}"
           if identity.get("specialization") else "")
    )
    lines.append("")

    # 2. Persona
    lines.append("## Persona")
    lines.append(persona_md.strip())
    lines.append("")

    # 3. Characteristics
    lines.append("## Characteristics")
    lines.append(
        f"Brawn {char['brawn']} | Agility {char['agility']} | Intellect {char['intellect']} | "
        f"Cunning {char['cunning']} | Willpower {char['willpower']} | Presence {char['presence']}"
    )
    lines.append("")

    # 4. Skills with descriptors
    lines.append("## Skills")
    for skill in character_yaml.get("skills", []):
        lines.append(f"- {skill['name']} ({skill['characteristic']}): {skill['descriptor']}")
    lines.append("")

    # 5. Talents
    talents = character_yaml.get("talents", [])
    if talents:
        lines.append("## Talents")
        for talent in talents:
            suffix = f" (rank {talent['ranks']})" if talent.get("ranks", 1) > 1 else ""
            lines.append(f"- {talent['name']}{suffix}: {talent['description']}")
        lines.append("")

    # 6. Derived stats
    defense = derived.get("defense", {})
    lines.append("## Derived Stats")
    lines.append(
        f"Wound Threshold: {derived['wound_threshold']} | "
        f"Strain Threshold: {derived['strain_threshold']} | "
        f"Soak: {derived['soak']} | "
        f"Defense: Melee {defense.get('melee', 0)}, Ranged {defense.get('ranged', 0)}"
    )
    lines.append("")

    # 7. Equipment
    equipment = character_yaml.get("equipment", {})
    lines.append("## Equipment")
    weapons = equipment.get("weapons", [])
    if weapons:
        lines.append("Weapons:")
        for w in weapons:
            lines.append(
                f"  - {w['name']}: damage {w.get('damage', '?')}, "
                f"crit {w.get('critical', '?')}, range {w.get('range', '?')}"
            )
    armor = equipment.get("armor", [])
    if armor:
        lines.append("Armor:")
        for a in armor:
            lines.append(f"  - {a['name']}")
    gear = equipment.get("gear", [])
    if gear:
        lines.append("Gear: " + ", ".join(g["name"] for g in gear))
    lines.append("")

    # 8. Credits
    credits = character_yaml.get("resources", {}).get("credits")
    if credits is not None:
        lines.append(f"Credits: {credits}")
        lines.append("")

    # 9. Scene plan (from scene_state if present)
    plans = scene_state.get("character_plans", {})
    plan = plans.get(identity["name"])
    if plan:
        lines.append("## Scene Plan")
        lines.append(plan)
        lines.append("")

    # 10. Active critical injuries
    injuries = status.get("critical_injuries", [])
    if injuries:
        lines.append("## Active Critical Injuries")
        for injury in injuries:
            lines.append(f"- {injury}")
        lines.append("")

    # 11. Current wounds / strain (most volatile)
    lines.append(f"Wounds: {status['wounds']}/{derived['wound_threshold']} | "
                 f"Strain: {status['strain']}/{derived['strain_threshold']}")

    return "\n".join(lines)


def load_scene_characters(
    scene: dict,
    scene_state: dict,
    characters_dir: str = "characters",
    player_filter: str | None = None,
) -> dict:
    """Return {id: rendered_prompt} for characters in the scene.

    player_filter controls which characters are returned:
      None         → all characters (default)
      "npc"        → only characters with no player field (pure NPCs); inline NPCs always included
      "companion"  → only characters with player: "companion" (Companions); inline NPCs excluded
    Characters with player: "human" are never returned by any filter.
    """
    import yaml as pyyaml
    from pathlib import Path

    result = {}

    for name in scene.get("npcs_present", []):
        yaml_path = Path(characters_dir) / f"{name}.yaml"
        md_path = Path(characters_dir) / f"{name}.md"
        with open(yaml_path) as f:
            char_yaml = pyyaml.safe_load(f)
        char_player = char_yaml.get("identity", {}).get("player")
        if char_player == "human":
            continue
        if player_filter == "npc" and char_player is not None:
            continue
        if player_filter == "companion" and char_player != "companion":
            continue
        persona_md = md_path.read_text() if md_path.exists() else ""
        result[name] = render_actor_prompt(char_yaml, persona_md, scene_state)

    if player_filter != "companion":
        for npc in scene.get("inline_npcs", []):
            result[npc["id"]] = npc["key_traits"]

    return result


def load_scene_yamls(
    scene: dict,
    characters_dir: str = "characters",
) -> dict[str, dict]:
    """Return {id: raw_yaml_dict} for non-human characters in scene["npcs_present"].

    Inline NPCs are skipped — they have no YAML file. Human players are excluded.
    Used to supply character stats (characteristic values, skill ranks) for check
    identification in Phase 3b.
    """
    import yaml as pyyaml
    from pathlib import Path

    result = {}
    for name in scene.get("npcs_present", []):
        yaml_path = Path(characters_dir) / f"{name}.yaml"
        with open(yaml_path) as f:
            char_yaml = pyyaml.safe_load(f)
        if char_yaml.get("identity", {}).get("player") == "human":
            continue
        result[name] = char_yaml
    return result


