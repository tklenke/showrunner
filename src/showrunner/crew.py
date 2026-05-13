# ABOUTME: CrewAI crew assembly — wires agents and tasks into a sequential pipeline.
# ABOUTME: Show Runner plans; Narrator, one task per NPC, Referee, Scribe execute in order each turn.

from crewai import Crew, Process, Task

from showrunner.agents.actors import create_actors
from showrunner.agents.narrator import create_narrator
from showrunner.agents.referee import create_referee
from showrunner.agents.scribe import create_scribe
from showrunner.agents.show_runner import create_show_runner


def build_crew(
    show_runner_context: str,
    narrator_context: str = "",
    actors_contexts: dict[str, str] | None = None,
    referee_context: str = "",
    scribe_context: str = "",
) -> Crew:
    """Assemble the sequential agent crew for a scene beat.

    Each *_context string is injected into the corresponding agent's task description
    so agents have per-turn scene data without it being baked into their backstories.
    actors_contexts maps npc_id to that NPC's rendered character prompt; one task is
    created per NPC so each receives only their own character data.
    """
    show_runner = create_show_runner()
    narrator = create_narrator()
    referee = create_referee()
    scribe = create_scribe()

    task_plan = Task(
        description=(
            f"{show_runner_context}\n\n"
            "Plan this beat: decide what the Narrator should describe, which NPCs are "
            "active and what they do, whether any skill or combat check is required, "
            "and what state changes the Scribe should record."
        ),
        expected_output=(
            "A beat plan: narration brief, active NPCs and their intended actions, "
            "any check to resolve, and state changes to record."
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
    for npc_id, npc_prompt in (actors_contexts or {}).items():
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
            context=[task_plan],
        )
        npc_tasks.append(npc_task)

    task_referee = Task(
        description=(
            f"{referee_context}\n\n"
            "Resolve any skill or combat checks triggered this beat per the beat plan. "
            'If no check is required, output "No check required."'
        ),
        expected_output="Check result with dice outcome, or 'No check required.'",
        agent=referee,
        context=[task_plan, task_narrate] + npc_tasks,
    )

    task_scribe = Task(
        description=(
            f"{scribe_context}\n\n"
            "Write a single sentence summarising what happened this beat for the session log. "
            "Format: '<what happened this beat in plain past tense>'. "
            "Do not call any tools. Output only the summary sentence, nothing else."
        ),
        expected_output="One sentence: a plain past-tense summary of this beat's events.",
        agent=scribe,
        context=[task_plan, task_narrate] + npc_tasks + [task_referee],
    )

    all_agents = [show_runner, narrator] + [t.agent for t in npc_tasks] + [referee, scribe]
    all_tasks = [task_plan, task_narrate] + npc_tasks + [task_referee, task_scribe]

    return Crew(
        agents=all_agents,
        tasks=all_tasks,
        process=Process.sequential,
        verbose=True,
    )
