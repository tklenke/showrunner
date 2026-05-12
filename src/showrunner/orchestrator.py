# ABOUTME: Main turn loop — sequences agent calls for each scene beat.
# ABOUTME: Narrator decides beat → World Runner narrates → player/actor acts → Referee checks → Scribe records.

from showrunner.crew import build_crew


def run_turn_loop(scene_description: str) -> None:
    """Run the agent turn loop starting from the given scene description.

    Each iteration kicks off a full CrewAI hierarchical run: Narrator manages,
    workers execute. Continues until the player types 'quit' or 'exit'.
    """
    print(f"\n=== Starting scene: {scene_description} ===\n")
    crew = build_crew(scene_description)

    while True:
        print("\n--- Running scene beat ---")
        result = crew.kickoff()
        print(f"\n{result}")

        cont = input("\nContinue to next beat? (enter to continue, 'quit' to stop): ").strip().lower()
        if cont in ("quit", "exit", "q"):
            print("Session ended.")
            break
