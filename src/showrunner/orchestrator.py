# ABOUTME: Main turn loop — sequences agent calls for each scene beat.
# ABOUTME: Narrator decides beat → World Runner narrates → player/actor acts → Referee checks → Scribe records.

from showrunner.agents.narrator import render_narrator_context
from showrunner.agents.world_runner import render_world_runner_context
from showrunner.crew import build_crew
from showrunner.tools.state_reader import load_party_stats, load_scene_state


def is_human_character(character_yaml: dict) -> bool:
    """Return True if this character is driven by the human player."""
    return character_yaml.get("identity", {}).get("player") == "human"


def prompt_player_action(character_name: str) -> str:
    """Prompt the CLI for the human player's action and return their input."""
    return input(f"What does {character_name} do? > ")


def run_turn_loop(scene: dict) -> None:
    """Run the agent turn loop for a loaded adventure scene.

    Each iteration builds context from current state, kicks off a CrewAI
    hierarchical run, then continues until the player quits or the scene exits.
    """
    print(f"\n=== {scene['title']} ===")
    print(scene["location"]["read_aloud"])

    while True:
        scene_state = load_scene_state()
        party_stats = load_party_stats()
        current_beat = scene_state.get("current_beat", "")

        narrator_ctx = render_narrator_context(scene, scene_state, party_stats, "")

        print(f"\n--- Beat: {current_beat} ---")
        crew = build_crew(narrator_ctx)
        result = crew.kickoff()
        print(f"\n{result}")

        cont = input("\nContinue to next beat? (beat ID, enter to stay, 'quit' to stop): ").strip().lower()
        if cont in ("quit", "exit", "q"):
            print("Session ended.")
            break
        elif cont:
            from showrunner.tools.state_writer import advance_beat
            advance_beat(cont)
