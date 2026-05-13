# ABOUTME: Referee agent — rules engine for dice pool construction, skill check difficulty, combat.
# ABOUTME: Runs on Alien (Llama 3.2 3B); uses dice_roller tool and rules_lookup tool.

from crewai import Agent

from showrunner.config import load_agent_configs
from showrunner.tools.agent_tools import consult_show_runner, read_state, roll_dice


def build_referee_backstory() -> str:
    """Return the Referee's system prompt with Phase 4 inline rules for the Bargos mansion scene."""
    return """You are the Referee — the rules engine for this RPG session.
You determine whether skill checks are needed, construct dice pools, and resolve combat.

POOL CONSTRUCTION:
- ability_dice = max(characteristic, skill_ranks)
- proficiency_dice = min(characteristic, skill_ranks)  [upgrade that many Ability to Proficiency]
- Add difficulty dice per check difficulty. Add boost/setback from situational modifiers.

SKILL CHECKS (Phase 4 scene):
- Vigilance check (spot incoming threat): Average difficulty — 2 purple dice.
  On PC success: PC acts before threat. On failure: threat gets one free advance.
- Negotiation vs Bargos: Opposed check. PC rolls Presence + Negotiation vs Bargos's Cool.

COMBAT ATTACKS:
- Melee/Brawl attack difficulty = target's melee defense rating (minimum 1 purple).
- Add 1 difficulty die per range band beyond Engaged.

DAMAGE AND SOAK:
- Wounds taken = (weapon damage + net successes) - target soak. Minimum 0.

MINION GROUPS (Gamorrean Guards):
- Group wound threshold = 5 per minion. One minion dies per 5 wounds dealt to the group.
- Group skill ranks stay constant regardless of how many minions remain.
- Pool construction uses the group's listed skill rank and characteristic.

TRIUMPH / DESPAIR:
- Triumph: counts as 1 success AND triggers a critical injury or exceptional outcome.
- Despair: counts as 1 failure AND triggers a complication or critical injury.
- Critical injuries: also triggered by spending 2 Advantage. Resolve narratively in Phase 4.

Do NOT call rules_lookup() — it is not implemented in Phase 4."""


def render_referee_context(scene: dict, beat_id: str) -> str:
    """Build scene-specific context for the Referee for the given beat.

    Includes the current beat's checks and all scene minion group stats.
    Appended to build_referee_backstory() — does not replace the rules.
    """
    lines = ["## Checks This Beat"]
    beat = next((b for b in scene.get("beats", []) if b["id"] == beat_id), None)
    checks = beat.get("checks", []) if beat else []
    for check in checks:
        header = (
            f"- Skill: {check['skill']} | Characteristic: {check['characteristic']}"
            f" | Difficulty: {check['difficulty']}"
        )
        if check.get("opposed_skill"):
            header += f" | Opposed: {check['opposed_skill']}"
        lines.append(header)
        if check.get("notes"):
            lines.append(f"  Notes: {check['notes'].strip()}")

    lines.append("")
    lines.append("## Minion Groups")
    for group in scene.get("minion_groups", []):
        characteristics = group.get("characteristics", {})
        char_str = ", ".join(f"{k.capitalize()} {v}" for k, v in characteristics.items())
        skills = group.get("skills", {})
        skill_str = ", ".join(f"{k.capitalize()} {v}" for k, v in skills.items())
        stats_str = ", ".join(filter(None, [char_str, skill_str]))
        lines.append(
            f"{group['name']} (count: {group['count']}, soak: {group['soak']},"
            f" wound threshold: {group['wound_threshold']} per minion)"
        )
        if stats_str:
            lines.append(f"  {stats_str}")
        for weapon in group.get("weapons", []):
            lines.append(
                f"  {weapon['name']}: damage {weapon['damage']}, crit {weapon['critical']},"
                f" {weapon['range']}, {weapon['special']}"
            )

    return "\n".join(lines)


def create_referee(context: str = "") -> Agent:
    """Return the Referee agent (Alien).

    context is rendered beat/scene data from render_referee_context(); appended
    to backstory so the Referee has it regardless of the Show Runner's delegation.
    """
    cfg = load_agent_configs()["referee"]
    backstory = build_referee_backstory()
    if context:
        backstory = f"{backstory}\n\n{context}"
    return Agent(
        role=cfg["role"],
        goal=cfg["goal"],
        backstory=backstory,
        llm=cfg["llm"],
        tools=[roll_dice, read_state, consult_show_runner],
        allow_delegation=cfg["allow_delegation"],
        verbose=cfg["verbose"],
    )
