# ABOUTME: Phase runners — each function drives one phase of the turn loop via direct LLM calls.
# ABOUTME: Replaces CrewAI crew builders; returns plain dicts/strings, no crew objects.

from showrunner.llm import build_system_prompt, call_llm


def run_npc_wave(
    npcs: dict[str, str],
    beat_ctx: str,
    user_action: str,
    companion_outputs: dict[str, str],
    summaries_log_path,
) -> dict[str, str]:
    """Step 3: Each NPC acts, then Narrator summarizes (2N calls for N NPCs).

    Each NPC receives beat context, user action, companion outputs, and compact
    summaries of prior NPCs. Summaries are appended to summaries_log_path.
    Returns {npc_id: full_output}.
    """
    prior_summaries = ""
    npc_outputs: dict[str, str] = {}

    for npc_id, npc_context in npcs.items():
        msg = f"{npc_context}\n\n{beat_ctx}"
        if user_action:
            msg += f"\n\n## Player action:\n{user_action}"
        if companion_outputs:
            companions_text = "\n\n".join(
                f"[{cid}]: {out}" for cid, out in companion_outputs.items()
            )
            msg += f"\n\n## Companion actions:\n{companions_text}"
        if prior_summaries:
            msg += f"\n\n## Earlier NPC actions this turn:\n{prior_summaries}"

        full_output = call_llm("actors", build_system_prompt("actors"), msg)
        print(f"[{npc_id}] {full_output}")
        npc_outputs[npc_id] = full_output

        summary_msg = f"Summarize in 1-2 sentences what {npc_id} just did:\n{full_output}"
        summary = call_llm("narrator", build_system_prompt("narrator"), summary_msg)
        with open(summaries_log_path, "a") as f:
            f.write(f"{npc_id}: {summary}\n")
        prior_summaries += f"\n{npc_id}: {summary}"

    return npc_outputs


def run_companion_wave(
    companion_contexts: dict[str, str],
    beat_ctx: str,
    player_action: str,
) -> dict[str, str]:
    """Step 2: Each Companion responds to the beat context and player action.

    Companions act before the NPC wave and do not see NPC outputs.
    Returns {} for empty companion_contexts.
    """
    if not companion_contexts:
        return {}
    outputs: dict[str, str] = {}
    for pc_id, pc_context in companion_contexts.items():
        msg = (
            f"{pc_context}\n\n"
            f"{beat_ctx}\n\n"
            f"## Player action:\n{player_action}"
        )
        output = call_llm("actors", build_system_prompt("actors"), msg)
        print(f"[{pc_id}] {output}")
        outputs[pc_id] = output
    return outputs


def run_summaries(action_map: dict[str, str]) -> dict[str, str]:
    """Step 3a: Summarise each actor's action in 1–2 sentences.

    Returns {actor_id: summary_text}.
    """
    summaries: dict[str, str] = {}
    for actor_id, action_text in action_map.items():
        msg = f"Summarise in 1-2 sentences what {actor_id} did: {action_text}"
        summaries[actor_id] = call_llm("actors", build_system_prompt("actors"), msg)
    return summaries


def run_checks(summaries_text: str, stats_text: str) -> str:
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


def run_rulings(check_specs: list[dict]) -> dict[str, str]:
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


def run_narrative(summaries: str, checks: str, results: str) -> str:
    """Step 3d: Generate player-facing narrative prose from the full resolution record."""
    msg = (
        f"## Action Summaries\n{summaries}\n\n"
        f"## Checks\n{checks}\n\n"
        f"## Results\n{results}"
    )
    return call_llm("show_runner", build_system_prompt("show_runner"), msg)


def run_last_actions(actor_summaries: dict[str, str]) -> dict[str, str]:
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


def run_beat_opener(beat: dict, last_log_entry: str) -> None:
    """Print a 2-3 sentence player-facing opener for the start of a new beat."""
    msg = (
        f"## Beat Director Notes\n"
        f"Show Runner: {beat.get('show_runner_notes', '')}\n"
        f"Narrator: {beat.get('narrator_notes', '')}"
    )
    if last_log_entry:
        msg += f"\n\n## Previous session log entry:\n{last_log_entry}"
    opener = call_llm("narrator", build_system_prompt("narrator"), msg)
    print(opener)
