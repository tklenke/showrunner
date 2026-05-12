# ABOUTME: CrewAI crew assembly — wires agents, tasks, and LiteLLM routing together.
# ABOUTME: Narrator is the hierarchical manager; World Runner, Actors, Referee, Scribe are workers.

from crewai import Crew, Process, Task

from showrunner.agents.actors import create_actors
from showrunner.agents.narrator import create_narrator
from showrunner.agents.referee import create_referee
from showrunner.agents.scribe import create_scribe
from showrunner.agents.world_runner import create_world_runner


def build_crew(narrator_context: str) -> Crew:
    """Assemble the full agent crew for a scene beat.

    narrator_context is the rendered scene + runtime state string from
    render_narrator_context(). Injected into the task description so the
    Narrator has full scene and state context before delegating.
    """
    narrator = create_narrator()
    world_runner = create_world_runner()
    actors = create_actors()
    referee = create_referee()
    scribe = create_scribe()

    tasks = [
        Task(
            description=(
                f"{narrator_context}\n\n"
                "Run a single scene beat: assess the current beat, direct the World Runner to "
                "narrate, handle any player or NPC action, call the Referee if a check is "
                "triggered, and have the Scribe record the outcome."
            ),
            expected_output=(
                "A complete scene beat: narration delivered to the player, any check resolved, "
                "and state updated."
            ),
            agent=world_runner,
        ),
    ]

    return Crew(
        agents=[world_runner, actors, referee, scribe],
        tasks=tasks,
        manager_agent=narrator,
        process=Process.hierarchical,
        verbose=True,
    )
