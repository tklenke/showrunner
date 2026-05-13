# ABOUTME: Main turn loop — sequences agent calls for each scene beat.
# ABOUTME: Narrator decides beat → World Runner narrates → player/actor acts → Referee checks → Scribe records.

import logging
from datetime import datetime
from pathlib import Path


from showrunner.agents.actors import load_scene_characters
from showrunner.agents.narrator import render_narrator_context
from showrunner.agents.referee import render_referee_context
from showrunner.agents.scribe import render_scribe_context
from showrunner.agents.show_runner import render_show_runner_context
from showrunner.crew import build_crew
from showrunner.instrumentation import setup_instrumentation, verbose_to_file
from showrunner.tools.state_reader import load_party_stats, load_scene_state
from showrunner.tools.state_writer import advance_beat


def _setup_session_log(timestamp: str) -> logging.Logger:
    """Set up a session log that writes to logs/session_TIMESTAMP.log."""
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    log_path = logs_dir / f"session_{timestamp}.log"

    logger = logging.getLogger("showrunner.session")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
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


_DIVIDER = "─" * 60


def prompt_player_action(character_name: str) -> str:
    """Prompt the CLI for the human player's action and return their input."""
    print(f"\n{_DIVIDER}")
    return input(f"  What does {character_name} do? > ")


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
    """Prompt for beat advancement; returns 'stay', 'advance', a beat ID, or 'quit'."""
    beats = scene.get("beats", [])
    beat_ids = [b["id"] for b in beats]
    next_id = _next_beat_id(scene, current_beat_id)

    print(f"\n{_DIVIDER}")
    print(f"  Beat: {current_beat_id}  ({' → '.join(beat_ids)})")
    if next_id:
        prompt = f"  [Enter] stay  |  [a] advance to '{next_id}'  |  [beat ID] jump  |  [q] quit > "
    else:
        prompt = f"  Last beat.  [Enter] stay  |  [beat ID] jump  |  [q] quit > "
    choice = input(prompt).strip().lower()
    if choice == "":
        return "stay"
    if choice == "a" and next_id:
        return "advance"
    return choice


def run_turn_loop(scene: dict) -> None:
    """Run the agent turn loop for a loaded adventure scene.

    Each iteration builds context from current state, kicks off a CrewAI
    hierarchical run, then continues until the player quits or the scene exits.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log = _setup_session_log(timestamp)
    verbose_path, prompts_path, prompt_logger = setup_instrumentation(timestamp)
    print(f"Verbose log: logs/verbose_{timestamp}.log  (tail -f to watch)")
    print(f"Prompt log:  logs/prompts_{timestamp}.log")

    print(f"\n=== {scene['title']} ===")
    print(scene["location"]["read_aloud"])
    log.info(f"Scene started: {scene['scene_id']}")

    last_action = ""
    while True:
        scene_state = load_scene_state()
        party_stats = load_party_stats()
        current_beat = scene_state.get("current_beat", "")

        show_runner_ctx = render_show_runner_context(scene, scene_state, party_stats, last_action)
        narrator_ctx = render_narrator_context(scene, current_beat, last_action, party_stats)
        referee_ctx = render_referee_context(scene, current_beat)
        scribe_ctx = render_scribe_context(scene_state, party_stats)
        scene_chars = load_scene_characters(scene, scene_state)
        actors_ctx = "\n\n---\n\n".join(scene_chars.values()) if scene_chars else ""
        log.debug(f"Beat: {current_beat}  last_action: {last_action!r}")

        print(f"\n--- Beat: {current_beat} ---")
        crew = build_crew(
            show_runner_ctx,
            narrator_context=narrator_ctx,
            actors_context=actors_ctx,
            referee_context=referee_ctx,
            scribe_context=scribe_ctx,
        )
        with verbose_to_file(verbose_path):
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
        elif choice == "stay":
            log.info(f"Staying on beat: {current_beat}")
        elif choice == "advance":
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
