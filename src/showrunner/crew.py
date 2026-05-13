# ABOUTME: CrewAI crew assembly — wires agents, tasks, and LiteLLM routing together.
# ABOUTME: Show Runner is the hierarchical manager; Narrator, Actors, Referee, Scribe are workers.

from crewai import Crew, Process, Task

from showrunner.agents.actors import create_actors
from showrunner.agents.narrator import create_narrator
from showrunner.agents.referee import create_referee
from showrunner.agents.scribe import create_scribe
from showrunner.agents.show_runner import create_show_runner


def build_crew(
    show_runner_context: str,
    narrator_context: str = "",
    referee_context: str = "",
    scribe_context: str = "",
) -> Crew:
    """Assemble the full agent crew for a scene beat.

    show_runner_context is passed to the Show Runner's task. The *_context params
    are injected into each worker's backstory so they have scene-specific data
    regardless of what the Show Runner delegates to them.
    """
    show_runner = create_show_runner()
    narrator = create_narrator(context=narrator_context)
    actors = create_actors()
    referee = create_referee(context=referee_context)
    scribe = create_scribe(context=scribe_context)

    tasks = [
        Task(
            description=(
                f"{show_runner_context}\n\n"
                "Run a single scene beat: assess the current beat, direct the Narrator to "
                "narrate, handle any player or NPC action, call the Referee if a check is "
                "triggered, and have the Scribe record the outcome."
            ),
            expected_output=(
                "A complete scene beat: narration delivered to the player, any check resolved, "
                "and state updated."
            ),
            agent=narrator,
        ),
    ]

    return Crew(
        agents=[narrator, actors, referee, scribe],
        tasks=tasks,
        manager_agent=show_runner,
        process=Process.hierarchical,
        verbose=True,
    )
