# ABOUTME: Main turn loop — sequences agent calls for each scene beat.
# ABOUTME: Narrator decides beat → World Runner narrates → player/actor acts → Referee checks → Scribe records.

import logging
from datetime import datetime
from pathlib import Path

from showrunner.agents.narrator import render_narrator_context
from showrunner.agents.world_runner import render_world_runner_context
from showrunner.crew import build_crew
from showrunner.tools.state_reader import load_party_stats, load_scene_state
from showrunner.tools.state_writer import advance_beat


def _setup_session_log() -> logging.Logger:
    """Set up a session log that writes to logs/session_TIMESTAMP.log and stdout."""
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = logs_dir / f"session_{timestamp}.log"

    logger = logging.getLogger("showrunner.session")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s  %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(file_handler)

    logger.info(f"Session log: {log_path}")
    return logger


def is_human_character(character_yaml: dict) -> bool:
    """Return True if this character is driven by the human player."""
    return character_yaml.get("identity", {}).get("player") == "human"


def prompt_player_action(character_name: str) -> str:
    """Prompt the CLI for the human player's action and return their input."""
    return input(f"What does {character_name} do? > ")


def _next_beat_id(scene: dict, current_beat_id: str) -> str | None:
    """Return the id of the beat after current_beat_id, or None if last."""
    beats = scene.get("beats", [])
    ids = [b["id"] for b in beats]
    try:
        idx = ids.index(current_beat_id)
        return ids[idx + 1] if idx + 1 < len(ids) else None
    except ValueError:
        return None


def _beat_prompt(scene: dict, current_beat_id: str) -> str:
    """Prompt for beat advancement, showing available options."""
    beats = scene.get("beats", [])
    beat_ids = [b["id"] for b in beats]
    next_id = _next_beat_id(scene, current_beat_id)

    print(f"\n  Current beat : {current_beat_id}")
    print(f"  All beats    : {' → '.join(beat_ids)}")
    if next_id:
        prompt = f"  Next beat? [Enter = '{next_id}', or type a beat ID, 'quit' to stop] > "
    else:
        prompt = f"  Last beat reached. [Enter to end session, or type a beat ID to revisit] > "
    return input(prompt).strip().lower()


def run_turn_loop(scene: dict) -> None:
    """Run the agent turn loop for a loaded adventure scene.

    Each iteration builds context from current state, kicks off a CrewAI
    hierarchical run, then continues until the player quits or the scene exits.
    """
    log = _setup_session_log()

    print(f"\n=== {scene['title']} ===")
    print(scene["location"]["read_aloud"])
    log.info(f"Scene started: {scene['scene_id']}")

    last_action = ""
    while True:
        scene_state = load_scene_state()
        party_stats = load_party_stats()
        current_beat = scene_state.get("current_beat", "")

        narrator_ctx = render_narrator_context(scene, scene_state, party_stats, last_action)
        log.debug(f"Beat: {current_beat}  last_action: {last_action!r}")

        print(f"\n--- Beat: {current_beat} ---")
        crew = build_crew(narrator_ctx)
        result = crew.kickoff()
        result_str = str(result)
        print(f"\n{result_str}")
        log.info(f"Beat result: {result_str[:200]}")

        last_action = prompt_player_action("Z-4P0")
        log.info(f"Z-4P0: {last_action!r}")

        if last_action.strip().lower() in ("quit", "exit", "q"):
            print("Session ended.")
            log.info("Session ended by player.")
            break

        choice = _beat_prompt(scene, current_beat)
        if choice in ("quit", "exit", "q"):
            print("Session ended.")
            log.info("Session ended by player.")
            break
        elif choice == "":
            next_id = _next_beat_id(scene, current_beat)
            if next_id:
                advance_beat(next_id)
                log.info(f"Advanced to beat: {next_id}")
            else:
                print("Scene complete.")
                log.info("Scene complete — no more beats.")
                break
        else:
            advance_beat(choice)
            log.info(f"Jumped to beat: {choice}")
