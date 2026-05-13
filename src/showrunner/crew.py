# ABOUTME: CrewAI crew assembly — wires agents and tasks into a sequential pipeline.
# ABOUTME: Show Runner plans; Narrator, Actors, Referee, Scribe execute in order each turn.

from crewai import Crew, Process, Task

from showrunner.agents.actors import create_actors
from showrunner.agents.narrator import create_narrator
from showrunner.agents.referee import create_referee
from showrunner.agents.scribe import create_scribe
from showrunner.agents.show_runner import create_show_runner


def build_crew(
    show_runner_context: str,
    narrator_context: str = "",
    actors_context: str = "",
    referee_context: str = "",
    scribe_context: str = "",
) -> Crew:
    """Assemble the sequential agent crew for a scene beat.

    Each *_context string is injected into the corresponding agent's task description
    so agents have per-turn scene data without it being baked into their backstories.
    """
    show_runner = create_show_runner()
    narrator = create_narrator()
    actors = create_actors()
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

    task_act = Task(
        description=(
            f"{actors_context}\n\n"
            "Voice the NPCs active this beat per the beat plan. "
            "Write each NPC's dialogue and actions in character."
        ),
        expected_output="NPC dialogue and actions for each active NPC this beat.",
        agent=actors,
        context=[task_plan],
    )

    task_referee = Task(
        description=(
            f"{referee_context}\n\n"
            "Resolve any skill or combat checks triggered this beat per the beat plan. "
            'If no check is required, output "No check required."'
        ),
        expected_output="Check result with dice outcome, or 'No check required.'",
        agent=referee,
        context=[task_plan, task_narrate, task_act],
    )

    task_scribe = Task(
        description=(
            f"{scribe_context}\n\n"
            "Record the outcomes of this beat. Update scene_state.yaml with the current "
            "beat progression, any NPC knowledge changes, and last_actions for each actor "
            "who acted this beat. Update party_stats.yaml for any wounds, strain, or "
            "resource changes."
        ),
        expected_output="State files updated; last_actions recorded for each active actor.",
        agent=scribe,
        context=[task_plan, task_narrate, task_act, task_referee],
    )

    return Crew(
        agents=[show_runner, narrator, actors, referee, scribe],
        tasks=[task_plan, task_narrate, task_act, task_referee, task_scribe],
        process=Process.sequential,
        verbose=True,
    )
