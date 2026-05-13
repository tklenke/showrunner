# ABOUTME: CrewAI crew assembly — phase builders for the turn loop.
# ABOUTME: NPC/PC wave builders plus five-step resolution pipeline (3a–3e).

import sys

from crewai import Crew, Process, Task

from showrunner.agents.actors import create_actors
from showrunner.agents.narrator import create_narrator
from showrunner.agents.referee import create_referee
from showrunner.agents.scribe import create_scribe
from showrunner.agents.show_runner import create_show_runner


class _PrintCallback:
    """Task callback that prints output to the real terminal immediately.

    Uses sys.__stdout__ so it bypasses the verbose_to_file redirect and reaches
    the player console as soon as each task completes. A class instance (not a
    closure) so Pydantic can serialize it without warnings.
    """

    def __init__(self, label: str | None = None):
        self.label = label

    def __call__(self, output) -> None:
        text = output.raw.strip() if hasattr(output, "raw") else str(output)
        if not text:
            return
        if self.label:
            sys.__stdout__.write(f"\n[{self.label}]\n{text}\n")
        else:
            sys.__stdout__.write(f"\n{text}\n")
        sys.__stdout__.flush()


def build_npc_crew(
    sr_context: str,
    narrator_context: str,
    npc_contexts: dict[str, str],
) -> Crew:
    """Phase 1: Show Runner plans, Narrator sets the scene, NPCs act in order.

    Each NPC task chains context from all prior NPC tasks so each character
    sees what the earlier NPCs said and did.
    """
    show_runner = create_show_runner()
    narrator = create_narrator()

    task_plan = Task(
        description=(
            f"{sr_context}\n\n"
            "Plan this beat: decide what the Narrator should describe, which NPCs are "
            "active and what they do, and what state changes the Scribe should record."
        ),
        expected_output=(
            "A beat plan: narration brief, active NPCs and their intended actions, "
            "any checks anticipated, and state changes to record."
        ),
        agent=show_runner,
    )

    task_narrate = Task(
        description=(
            f"{narrator_context}\n\n"
            "Deliver the narration for this beat based on the beat plan. "
            "Write in second person. Describe what the player sees, hears, and feels."
        ),
        expected_output="Narration text delivered to the player.",
        agent=narrator,
        context=[task_plan],
        callback=_PrintCallback(),
    )

    npc_tasks = []
    for npc_id, npc_prompt in npc_contexts.items():
        actor = create_actors()
        npc_task = Task(
            name=npc_id,
            description=(
                f"{npc_prompt}\n\n"
                f"Voice {npc_id} this beat per the beat plan. "
                "Write their dialogue and physical actions in character. "
                "Respond only as this character — do not speak for other NPCs."
            ),
            expected_output=f"Dialogue and actions for {npc_id} this beat.",
            agent=actor,
            context=[task_plan] + npc_tasks,
            callback=_PrintCallback(npc_id),
        )
        npc_tasks.append(npc_task)

    all_agents = [show_runner, narrator] + [t.agent for t in npc_tasks]
    all_tasks = [task_plan, task_narrate] + npc_tasks

    return Crew(
        agents=all_agents,
        tasks=all_tasks,
        process=Process.sequential,
        verbose=True,
    )


def build_pc_crew(
    npc_wave_text: str,
    ai_pc_contexts: dict[str, str],
    player_action: str,
) -> Crew | None:
    """Phase 2: AI party members act.

    Each AI PC task receives the full NPC wave text and player action so
    each character sees the complete context before responding.
    Returns None when ai_pc_contexts is empty (orchestrator skips kickoff).
    Check identification has moved to Phase 3b (build_check_crew).
    """
    if not ai_pc_contexts:
        return None

    ai_pc_tasks = []
    for pc_id, pc_prompt in ai_pc_contexts.items():
        actor = create_actors()
        pc_task = Task(
            name=pc_id,
            description=(
                f"{pc_prompt}\n\n"
                "## What happened before your turn:\n"
                f"{npc_wave_text}\n\n"
                f"## Player action: {player_action}\n\n"
                f"Voice {pc_id} in response to the above. "
                "React to the NPCs and to any direction the player gave you. "
                "Write your dialogue and physical actions in character."
            ),
            expected_output=f"Dialogue and actions for {pc_id} this beat.",
            agent=actor,
            callback=_PrintCallback(pc_id),
        )
        ai_pc_tasks.append(pc_task)

    return Crew(
        agents=[t.agent for t in ai_pc_tasks],
        tasks=ai_pc_tasks,
        process=Process.sequential,
        verbose=True,
    )


def build_resolution_crew(
    check_specs: list[dict],
    scribe_context: str,
    full_turn_summary: str,
) -> Crew:
    """Phase 3: one Referee task per check (chained), then Scribe logs the turn.

    If check_specs is empty, only the Scribe task is created.
    Each Referee task receives only its own check spec so the small model
    has one focused job per invocation.
    """
    referee_tasks = []
    for spec in check_specs:
        referee = create_referee()
        ref_task = Task(
            description=(
                "Resolve this check:\n"
                f"Actor: {spec['actor']}\n"
                f"Skill: {spec['skill']}\n"
                f"Characteristic: {spec['characteristic']}\n"
                f"Difficulty: {spec['difficulty']}\n"
                f"Notes: {spec.get('notes', '')}\n\n"
                "Construct the dice pool, roll the dice, and deliver your ruling."
            ),
            expected_output="Dice pool, roll result, and outcome ruling for this check.",
            agent=referee,
            context=referee_tasks[:],
        )
        referee_tasks.append(ref_task)

    scribe = create_scribe()
    task_scribe = Task(
        description=(
            f"{scribe_context}\n\n"
            "## Full Turn Summary:\n"
            f"{full_turn_summary}\n\n"
            "Write a single sentence summarising what happened this beat for the session log. "
            "Output only the summary sentence, nothing else."
        ),
        expected_output="One sentence: a plain past-tense summary of this beat's events.",
        agent=scribe,
        context=referee_tasks[:],
    )

    all_agents = [t.agent for t in referee_tasks] + [scribe]
    all_tasks = referee_tasks + [task_scribe]

    return Crew(
        agents=all_agents,
        tasks=all_tasks,
        process=Process.sequential,
        verbose=True,
    )


# ── Resolution pipeline (4.14) ───────────────────────────────────────────────


def build_summary_crew(action_map: dict[str, str]) -> Crew:
    """Phase 3a: one alien 3B summarisation task per actor.

    action_map is {actor_id: action_text} covering all characters that acted
    this turn. Each task produces a 1–2 sentence plain-language summary.
    """
    tasks = []
    for actor_id, action_text in action_map.items():
        actor = create_actors()
        task = Task(
            name=actor_id,
            description=(
                f"Summarise in 1–2 sentences what {actor_id} did:\n\n{action_text}"
            ),
            expected_output=f"1–2 sentence summary of {actor_id}'s action.",
            agent=actor,
        )
        tasks.append(task)
    return Crew(
        agents=[t.agent for t in tasks],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )


def build_check_crew(summaries_text: str, stats_text: str) -> Crew:
    """Phase 3b: sardinia 8B identifies required checks from summaries + stats.

    Produces a numbered check list or NO_CHECKS. Format per line:
    {n}. {actor} | {skill} | {characteristic} {value} | {skill_rank} | {difficulty} | {notes}
    """
    show_runner = create_show_runner()
    task = Task(
        description=(
            "## Action Summaries\n"
            f"{summaries_text}\n\n"
            "## Character Stats\n"
            f"{stats_text}\n\n"
            "Review every action. List every skill check, opposed roll, or combat attack "
            "triggered. Output format — one line per check:\n"
            "{n}. {actor} | {skill} | {characteristic} {value} | {skill_rank} | {difficulty} | {notes}\n\n"
            "If no checks are needed, output exactly: NO_CHECKS"
        ),
        expected_output=(
            "Either NO_CHECKS, or a numbered check list with characteristic values "
            "and skill ranks embedded."
        ),
        agent=show_runner,
    )
    return Crew(
        agents=[show_runner],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )


def build_ruling_crew(check_specs: list[dict]) -> Crew | None:
    """Phase 3c: one sardinia 8B ruling task per check spec.

    Each spec must include a pre-computed 'roll_result' string (dice rolled by
    the orchestrator). Returns None when check_specs is empty.
    Tasks chain so each ruling sees prior rulings.
    """
    if not check_specs:
        return None

    ruling_tasks = []
    for spec in check_specs:
        show_runner = create_show_runner()
        task = Task(
            name=spec["actor"],
            description=(
                f"Actor: {spec['actor']} | Skill: {spec['skill']} | "
                f"Characteristic: {spec['characteristic']} {spec.get('char_value', '')} | "
                f"Skill rank: {spec.get('skill_rank', '')} | "
                f"Difficulty: {spec['difficulty']}\n"
                f"Notes: {spec.get('notes', '')}\n\n"
                f"Dice roll result: {spec['roll_result']}\n\n"
                "State the outcome: passed or failed, wounds dealt (if attack), "
                "and any triumph/despair effects. One short paragraph."
            ),
            expected_output="Outcome ruling: passed/failed, mechanical consequences, narrative flavour.",
            agent=show_runner,
            context=ruling_tasks[:],
        )
        ruling_tasks.append(task)

    return Crew(
        agents=[t.agent for t in ruling_tasks],
        tasks=ruling_tasks,
        process=Process.sequential,
        verbose=True,
    )


def build_narrative_crew(summaries: str, checks: str, results: str) -> Crew:
    """Phase 3d: sardinia 8B (Show Runner) produces player-facing resolution prose.

    Receives all three turn files; outputs 2–4 sentences printed directly to terminal.
    """
    show_runner = create_show_runner()
    task = Task(
        description=(
            "## What each character did\n"
            f"{summaries}\n\n"
            "## Checks triggered\n"
            f"{checks}\n\n"
            "## Ruling results\n"
            f"{results}\n\n"
            "Describe what just happened in 2–4 vivid sentences for the player. "
            "Write in second person. Cover the most dramatic outcomes."
        ),
        expected_output="2–4 sentences of player-facing narrative prose.",
        agent=show_runner,
    )
    return Crew(
        agents=[show_runner],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )


def build_last_action_crew(
    actor_ids: list[str],
    summaries: str,
    checks: str,
    results: str,
) -> Crew | None:
    """Phase 3e: Narrator extracts one last-action sentence per actor.

    Used to populate scene_state last_actions for next turn context.
    Returns None when actor_ids is empty.
    """
    if not actor_ids:
        return None

    tasks = []
    for actor_id in actor_ids:
        narrator = create_narrator()
        task = Task(
            name=actor_id,
            description=(
                "Given these events:\n\n"
                f"## Summaries\n{summaries}\n\n"
                f"## Checks\n{checks}\n\n"
                f"## Results\n{results}\n\n"
                f"What was {actor_id}'s last action this turn? One sentence only."
            ),
            expected_output=f"One sentence describing {actor_id}'s last action.",
            agent=narrator,
        )
        tasks.append(task)

    return Crew(
        agents=[t.agent for t in tasks],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )
