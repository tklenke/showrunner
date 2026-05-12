# ABOUTME: CrewAI crew assembly — wires agents, tasks, and LiteLLM routing together.
# ABOUTME: Narrator is the hierarchical manager; World Runner, Actors, Referee, Scribe are workers.

from crewai import Crew, Process, Task

from showrunner.agents.actors import create_actors
from showrunner.agents.narrator import create_narrator
from showrunner.agents.referee import create_referee
from showrunner.agents.scribe import create_scribe
from showrunner.agents.world_runner import create_world_runner


def build_crew(scene_description: str) -> Crew:
    """Assemble the full agent crew for a scene run.

    Narrator manages the hierarchical process and delegates to the four worker agents.
    scene_description is injected into the opening task so the Narrator has context.
    """
    narrator = create_narrator()
    world_runner = create_world_runner()
    actors = create_actors()
    referee = create_referee()
    scribe = create_scribe()

    tasks = [
        Task(
            description=(
                f"Scene context: {scene_description}\n\n"
                "Run a single scene beat: assess the situation, direct the World Runner to "
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
