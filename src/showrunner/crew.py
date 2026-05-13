# ABOUTME: CrewAI crew assembly — three phase builders for the turn loop.
# ABOUTME: build_npc_crew, build_pc_crew, build_resolution_crew replace the old build_crew.

from crewai import Crew, Process, Task

from showrunner.agents.actors import create_actors
from showrunner.agents.narrator import create_narrator
from showrunner.agents.referee import create_referee
from showrunner.agents.scribe import create_scribe
from showrunner.agents.show_runner import create_show_runner


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
    sr_review_context: str,
) -> Crew:
    """Phase 2: AI party members act, then Show Runner identifies checks needed.

    AI PC tasks receive the NPC wave text and player action so each AI PC
    sees the full context before acting. The Show Runner review task at the
    end reads all outputs and emits a structured check list for Phase 3.
    """
    show_runner = create_show_runner()

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
        )
        ai_pc_tasks.append(pc_task)

    task_sr_review = Task(
        description=(
            f"{sr_review_context}\n\n"
            "## NPC Actions This Beat:\n"
            f"{npc_wave_text}\n\n"
            f"## Player Action: {player_action}\n\n"
            "Review every action taken this beat. List every skill check, opposed roll, "
            "or combat attack that was triggered. Use this exact format:\n\n"
            "CHECKS:\n"
            "1. {actor} | {skill} | {characteristic} | {difficulty} | {notes}\n"
            "CHECKS_END\n\n"
            "If no mechanical checks are needed, output exactly: NO_CHECKS"
        ),
        expected_output=(
            "Either NO_CHECKS, or a CHECKS:/CHECKS_END block listing every check "
            "triggered this beat."
        ),
        agent=show_runner,
        context=ai_pc_tasks,
    )

    all_agents = [t.agent for t in ai_pc_tasks] + [show_runner]
    all_tasks = ai_pc_tasks + [task_sr_review]

    return Crew(
        agents=all_agents,
        tasks=all_tasks,
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
