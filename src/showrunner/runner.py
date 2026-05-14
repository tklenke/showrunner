# ABOUTME: Phase runners — each function drives one phase of the turn loop via direct LLM calls.
# ABOUTME: Replaces CrewAI crew builders; returns plain dicts/strings, no crew objects.

from showrunner.llm import build_system_prompt, call_llm, load_task_prompt


def run_npc_wave(
    npcs: dict[str, str],
    beat_ctx: str,
    user_action: str,
    companion_summaries: dict[str, str],
    summaries_log_path,
) -> dict[str, str]:
    """Step 3: Each NPC acts, then Narrator summarizes (2N calls for N NPCs).

    Each NPC receives beat context, player action, companion summaries, and compact
    summaries of prior NPCs. Summaries are appended to summaries_log_path.
    Returns {npc_id: full_output}.
    """
    prior_summaries = ""
    npc_outputs: dict[str, str] = {}

    for npc_id, npc_context in npcs.items():
        sections = []
        if companion_summaries:
            for cid, summary in companion_summaries.items():
                sections.append(f"\n{cid}: {summary}")
        if prior_summaries:
            sections.append(prior_summaries)
        msg = load_task_prompt("run_npc_wave").format(
            npc_context=npc_context,
            beat_ctx=beat_ctx,
            player_action=user_action,
            other_character_actions="".join(sections),
        )

        full_output = call_llm("actors", build_system_prompt("actors"), msg, label=npc_id)
        print(f"\n=== {npc_id} ===\n{full_output}")
        npc_outputs[npc_id] = full_output

        summary_msg = load_task_prompt("run_npc_wave_summary").format(
            npc_id=npc_id, full_output=full_output
        )
        summary = call_llm("narrator", build_system_prompt("narrator"), summary_msg, label=npc_id)
        with open(summaries_log_path, "a") as f:
            f.write(f"{npc_id}: {summary}\n")
        prior_summaries += f"\n{npc_id}: {summary}"

    return npc_outputs


def run_companion_wave(
    companion_contexts: dict[str, str],
    beat_ctx: str,
    player_action: str,
) -> tuple[dict[str, str], dict[str, str]]:
    """Step 2: Each Companion responds; Narrator summarizes each.

    Returns (full_outputs, summaries). full_outputs go to the session log;
    summaries go to the NPC wave so NPCs see compact companion context.
    """
    if not companion_contexts:
        return {}, {}
    outputs: dict[str, str] = {}
    summaries: dict[str, str] = {}
    for pc_id, pc_context in companion_contexts.items():
        msg = load_task_prompt("run_companion_wave").format(
            pc_context=pc_context,
            beat_ctx=beat_ctx,
            player_action=player_action,
        )
        output = call_llm("actors", build_system_prompt("actors"), msg, label=pc_id)
        print(f"\n=== {pc_id} ===\n{output}")
        outputs[pc_id] = output
        summary_msg = load_task_prompt("run_npc_wave_summary").format(
            npc_id=pc_id, full_output=output
        )
        summaries[pc_id] = call_llm("narrator", build_system_prompt("narrator"), summary_msg, label=pc_id)
    return outputs, summaries


def run_summaries(party_actions: dict[str, str], summaries_log_path) -> None:
    """Step 4: Narrator summarises each party member's action, appending to summaries log."""
    for actor_id, action_text in party_actions.items():
        msg = load_task_prompt("run_summaries").format(actor_id=actor_id, action_text=action_text)
        summary = call_llm("narrator", build_system_prompt("narrator"), msg)
        with open(summaries_log_path, "a") as f:
            f.write(f"{actor_id}: {summary}\n")


def run_checks(char_summaries: dict[str, str], char_stats: dict[str, str]) -> str:
    """Step 5: Identify skill checks per character; return combined check lines or 'NO_CHECKS'."""
    check_lines: list[str] = []
    for char_id, summary in char_summaries.items():
        stats = char_stats.get(char_id, "")
        msg = load_task_prompt("run_checks").format(char_id=char_id, summary=summary, stats=stats)
        output = call_llm("show_runner", build_system_prompt("show_runner"), msg, label=char_id)
        if "NO_CHECKS" not in output:
            check_lines.append(output.strip())
    return "\n".join(check_lines) if check_lines else "NO_CHECKS"


def run_rulings(check_specs: list[dict], *, on_ruling=None) -> dict[str, str]:
    """Step 6: Issue a ruling for each check spec.

    on_ruling(actor, ruling_text) -> str | None is called after each ruling;
    its return value becomes the party-status context for the next ruling call.
    Returns {} for empty specs.
    """
    if not check_specs:
        return {}
    rulings: dict[str, str] = {}
    next_context = ""
    for spec in check_specs:
        msg = load_task_prompt("run_rulings").format(
            actor=spec["actor"],
            skill=spec["skill"],
            difficulty=spec["difficulty"],
            notes=spec.get("notes", ""),
            roll_result=spec.get("roll_result", ""),
        )
        if next_context:
            msg += f"\n\n## Current party status:\n{next_context}"
        ruling = call_llm("show_runner", build_system_prompt("show_runner"), msg)
        rulings[spec["actor"]] = ruling
        if on_ruling:
            next_context = on_ruling(spec["actor"], ruling) or ""
    return rulings


def run_narrative(summaries: str, checks: str, results: str) -> str:
    """Step 3d: Generate player-facing narrative prose from the full resolution record."""
    msg = load_task_prompt("run_narrative").format(summaries=summaries, checks=checks, results=results)
    return call_llm("show_runner", build_system_prompt("show_runner"), msg)


def run_last_actions(actor_summaries: dict[str, str]) -> dict[str, str]:
    """Step 3e: Extract each actor's last action sentence from their summary.

    Each Narrator call receives only that actor's own summary. Returns {} for empty input.
    """
    if not actor_summaries:
        return {}
    last_actions: dict[str, str] = {}
    for actor_id, summary in actor_summaries.items():
        msg = load_task_prompt("run_last_actions").format(actor_id=actor_id, summary=summary)
        last_actions[actor_id] = call_llm("narrator", build_system_prompt("narrator"), msg, label=actor_id)
    return last_actions


def run_plan_update(
    characters: dict[str, str],
    summaries: str,
    results: str,
    last_actions: dict[str, str],
    *,
    plan_log_path=None,
) -> dict[str, str]:
    """Step 9: SR sets overall plan then individual plans for each character.

    Returns {character_id: individual_plan}. No calls if characters is empty.
    """
    if not characters:
        return {}

    last_actions_text = "\n".join(f"{k}: {v}" for k, v in last_actions.items())
    overall_msg = load_task_prompt("run_plan_update").format(
        summaries=summaries, results=results, last_actions_text=last_actions_text
    )
    overall_plan = call_llm("show_runner", build_system_prompt("show_runner"), overall_msg)

    if plan_log_path is not None:
        with open(plan_log_path, "w") as f:
            f.write(overall_plan)

    individual_plans: dict[str, str] = {}
    for char_id, char_context in characters.items():
        msg = load_task_prompt("run_plan_update_individual").format(
            overall_plan=overall_plan, char_id=char_id, char_context=char_context
        )
        individual_plans[char_id] = call_llm("show_runner", build_system_prompt("show_runner"), msg, label=char_id)

    return individual_plans


def run_beat_opener(beat: dict, last_log_entry: str, verbose: bool = False) -> None:
    """Print a 2-3 sentence player-facing opener for the start of a new beat."""
    msg = load_task_prompt("run_beat_opener").format(
        show_runner_notes=beat.get("show_runner_notes", ""),
        narrator_notes=beat.get("narrator_notes", ""),
    )
    if last_log_entry:
        msg += f"\n\n## Previous session log entry:\n{last_log_entry}"
    opener = call_llm("narrator", build_system_prompt("narrator"), msg)
    if verbose:
        print(f"=== Beat Opener ===\n{opener}")
    else:
        print(opener)
