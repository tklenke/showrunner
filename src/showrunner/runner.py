# ABOUTME: Phase runners — each function drives one phase of the turn loop via direct LLM calls.
# ABOUTME: Replaces CrewAI crew builders; returns plain dicts/strings, no crew objects.

from showrunner.llm import build_system_prompt, call_llm


def run_npc_wave(
    sr_context: str,
    narrator_context: str,
    npc_contexts: dict[str, str],
) -> dict[str, str]:
    """Phase 1: Show Runner plans the beat, Narrator narrates, each NPC acts in order.

    Returns {"_narrator": narration_text, npc_id: output, ...}.
    """
    beat_plan = call_llm("show_runner", build_system_prompt("show_runner"), sr_context)

    narrator_msg = f"{narrator_context}\n\n## Beat Plan:\n{beat_plan}"
    narration = call_llm("narrator", build_system_prompt("narrator"), narrator_msg)
    print(narration)

    npc_outputs: dict[str, str] = {}
    for npc_id, npc_context in npc_contexts.items():
        prior = "\n\n".join(f"[{nid}]: {out}" for nid, out in npc_outputs.items())
        npc_msg = f"{npc_context}\n\n## Beat Plan:\n{beat_plan}"
        if prior:
            npc_msg += f"\n\n## Earlier NPC actions this beat:\n{prior}"
        output = call_llm("actors", build_system_prompt("actors"), npc_msg)
        print(f"[{npc_id}] {output}")
        npc_outputs[npc_id] = output

    return {"_narrator": narration, **npc_outputs}


def run_companion_wave(
    npc_wave_text: str,
    companion_contexts: dict[str, str],
    player_action: str,
) -> dict[str, str]:
    """Phase 2: Each Companion responds to the NPC wave and player action.

    Returns {} for empty companion_contexts.
    """
    if not companion_contexts:
        return {}
    outputs: dict[str, str] = {}
    for pc_id, pc_context in companion_contexts.items():
        msg = (
            f"{pc_context}\n\n"
            f"## What just happened:\n{npc_wave_text}\n\n"
            f"## Player action:\n{player_action}"
        )
        output = call_llm("actors", build_system_prompt("actors"), msg)
        print(f"[{pc_id}] {output}")
        outputs[pc_id] = output
    return outputs


def run_summary_phase(action_map: dict[str, str]) -> dict[str, str]:
    """Step 3a: Summarise each actor's action in 1–2 sentences.

    Returns {actor_id: summary_text}.
    """
    summaries: dict[str, str] = {}
    for actor_id, action_text in action_map.items():
        msg = f"Summarise in 1-2 sentences what {actor_id} did: {action_text}"
        summaries[actor_id] = call_llm("actors", build_system_prompt("actors"), msg)
    return summaries


def run_check_phase(summaries_text: str, stats_text: str) -> str:
    """Step 3b: Identify skill checks from summaries and stats.

    Returns raw Show Runner output (list of checks or "NO_CHECKS").
    """
    msg = (
        f"## Action Summaries\n{summaries_text}\n\n"
        f"## Character Stats\n{stats_text}\n\n"
        "Review every action. List every skill check, opposed roll, or combat attack triggered.\n"
        "Output format — one line per check:\n"
        "{n}. {actor} | {skill} | {characteristic} {value} | {skill_rank} | {difficulty} | {notes}\n\n"
        "If no checks are needed, output exactly: NO_CHECKS"
    )
    return call_llm("show_runner", build_system_prompt("show_runner"), msg)


def run_ruling_phase(check_specs: list[dict]) -> dict[str, str]:
    """Step 3c: Issue a ruling for each check spec.

    Each call sees all prior rulings for context. Returns {} for empty specs.
    """
    if not check_specs:
        return {}
    rulings: dict[str, str] = {}
    prior_rulings = ""
    for spec in check_specs:
        msg = (
            f"Resolve this check:\n"
            f"Actor: {spec['actor']} | Skill: {spec['skill']} | Difficulty: {spec['difficulty']}\n"
            f"Notes: {spec.get('notes', '')}\n\n"
            f"Dice roll result: {spec.get('roll_result', '')}"
        )
        if prior_rulings:
            msg += f"\n\n## Prior rulings this turn:\n{prior_rulings}"
        ruling = call_llm("show_runner", build_system_prompt("show_runner"), msg)
        rulings[spec["actor"]] = ruling
        prior_rulings += f"\n{spec['actor']}: {ruling}"
    return rulings


def run_narrative_phase(summaries: str, checks: str, results: str) -> str:
    """Step 3d: Generate player-facing narrative prose from the full resolution record."""
    msg = (
        f"## Action Summaries\n{summaries}\n\n"
        f"## Checks\n{checks}\n\n"
        f"## Results\n{results}"
    )
    return call_llm("show_runner", build_system_prompt("show_runner"), msg)


def run_last_action_phase(actor_summaries: dict[str, str]) -> dict[str, str]:
    """Step 3e: Extract each actor's last action sentence from their summary.

    Each Narrator call receives only that actor's own summary. Returns {} for empty input.
    """
    if not actor_summaries:
        return {}
    last_actions: dict[str, str] = {}
    for actor_id, summary in actor_summaries.items():
        msg = f"What was {actor_id}'s last action this turn? One sentence.\n\n{summary}"
        last_actions[actor_id] = call_llm("narrator", build_system_prompt("narrator"), msg)
    return last_actions


def run_scribe_phase(scribe_context: str, full_turn_summary: str) -> str:
    """Step 3f: Scribe writes one-sentence session log entry for the turn."""
    msg = f"{scribe_context}\n\n## This turn:\n{full_turn_summary}"
    return call_llm("scribe", build_system_prompt("scribe"), msg)
