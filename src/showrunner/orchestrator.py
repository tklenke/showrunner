# ABOUTME: Main turn loop — three-phase sequential agent pipeline per turn.
# ABOUTME: Phase 1: NPC wave. Phase 2: PC wave + check ID. Phase 3: resolution + scribe.

import logging
from datetime import datetime
from pathlib import Path

from showrunner.agents.actors import load_scene_characters
from showrunner.agents.narrator import render_narrator_context
from showrunner.agents.referee import render_referee_context
from showrunner.agents.scribe import render_scribe_context
from showrunner.agents.show_runner import render_show_runner_context
from showrunner.config import load_agent_configs
from showrunner.crew import build_npc_crew, build_pc_crew, build_resolution_crew
from showrunner.instrumentation import setup_instrumentation, verbose_to_file
from showrunner.tools.state_reader import load_party_stats, load_scene_state
from showrunner.tools.state_writer import advance_beat, initialize_scene_state, update_scene_state


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
    return input(f"  What do you and your companions do? > ")


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


def _parse_check_specs(review_output: str) -> list[dict]:
    """Parse the Show Runner review output into a list of check spec dicts.

    Expects either "NO_CHECKS" or a CHECKS:/CHECKS_END block:
        CHECKS:
        1. actor | skill | characteristic | difficulty | notes
        CHECKS_END
    """
    if "NO_CHECKS" in review_output:
        return []
    specs = []
    in_checks = False
    for line in review_output.splitlines():
        stripped = line.strip()
        if "CHECKS:" in stripped:
            in_checks = True
            continue
        if "CHECKS_END" in stripped:
            break
        if in_checks and stripped and stripped[0].isdigit():
            content = stripped.split(".", 1)[1].strip() if "." in stripped else stripped
            parts = [p.strip() for p in content.split("|")]
            if len(parts) >= 4:
                specs.append({
                    "actor": parts[0],
                    "skill": parts[1],
                    "characteristic": parts[2],
                    "difficulty": parts[3],
                    "notes": parts[4] if len(parts) > 4 else "",
                })
    return specs


def _collect_wave_outputs(crew, role: str) -> dict[str, str]:
    """Return {task.name: output.raw} for all tasks matching the given agent role."""
    return {
        task.name: (task.output.raw.strip() if task.output else "")
        for task in crew.tasks
        if task.agent.role == role and task.name
    }


def _get_task_output(crew, role: str) -> str:
    """Return output.raw for the first task matching the given agent role."""
    for task in crew.tasks:
        if task.agent.role == role and task.output:
            return task.output.raw.strip()
    return ""


def run_turn_loop(scene: dict) -> None:
    """Run the three-phase agent turn loop for a loaded adventure scene."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log = _setup_session_log(timestamp)
    verbose_path, prompts_path, prompt_logger = setup_instrumentation(
        timestamp, config_path=Path("config/litellm.yaml")
    )
    agent_configs = load_agent_configs()
    print("Agents:")
    for name, cfg in agent_configs.items():
        print(f"  {name:<14} {cfg['model_alias']}")
    print(f"Verbose log: logs/verbose_{timestamp}.log  (tail -f to watch)")
    print(f"Prompt log:  logs/prompts_{timestamp}.log")

    initialize_scene_state(scene)

    print(f"\n=== {scene['title']} ===")
    print(scene["location"]["read_aloud"])
    log.info(f"Scene started: {scene['scene_id']}")

    while True:
        scene_state = load_scene_state()
        party_stats = load_party_stats()
        current_beat = scene_state.get("current_beat", "")
        last_actions = scene_state.get("last_actions", {})

        # Contexts built once per turn (state hasn't changed mid-turn)
        sr_ctx = render_show_runner_context(scene, scene_state, party_stats, last_actions)
        narrator_ctx = render_narrator_context(scene, current_beat, last_actions, party_stats)
        referee_ctx = render_referee_context(scene, current_beat)
        scribe_ctx = render_scribe_context(scene_state, party_stats)

        npc_chars = load_scene_characters(scene, scene_state, player_filter="npc")
        ai_pc_chars = load_scene_characters(scene, scene_state, player_filter="ai")

        log.debug(
            f"Beat: {current_beat}  npcs: {list(npc_chars)}  ai_pcs: {list(ai_pc_chars)}"
        )
        print(f"\n--- Beat: {current_beat} ---")

        # ── Phase 1: NPC wave ────────────────────────────────────────────────
        npc_crew = build_npc_crew(sr_ctx, narrator_ctx, npc_chars)
        with verbose_to_file(verbose_path):
            npc_crew.kickoff()

        narrator_text = _get_task_output(npc_crew, "Narrator")
        npc_outputs = _collect_wave_outputs(npc_crew, "NPC Voice Actor")

        if narrator_text:
            print(f"\n{narrator_text}")
        for npc_id, text in npc_outputs.items():
            if text:
                print(f"\n[{npc_id}]\n{text}")

        log.info(f"Phase 1 complete: {len(npc_outputs)} NPCs voiced")

        # ── Player input ─────────────────────────────────────────────────────
        player_action = prompt_player_action("Z-4P0")
        log.info(f"Player action: {player_action!r}")

        if player_action.strip().lower() in ("quit", "exit", "q"):
            print("Session ended.")
            log.info("Session ended by player.")
            break

        # ── Phase 2: PC wave + check identification ──────────────────────────
        npc_wave_text = "\n\n".join(
            f"[{npc_id}]: {text}" for npc_id, text in npc_outputs.items()
        )

        pc_crew = build_pc_crew(npc_wave_text, ai_pc_chars, player_action, sr_ctx)
        with verbose_to_file(verbose_path):
            pc_crew.kickoff()

        ai_pc_outputs = _collect_wave_outputs(pc_crew, "NPC Voice Actor")
        review_output = _get_task_output(pc_crew, "Show Runner")

        for pc_id, text in ai_pc_outputs.items():
            if text:
                print(f"\n[{pc_id}]\n{text}")

        check_specs = _parse_check_specs(review_output)
        log.info(f"Phase 2 complete: {len(check_specs)} checks identified")

        # ── Phase 3: Resolution ───────────────────────────────────────────────
        full_turn_summary = (
            f"Beat: {current_beat}\n"
            f"NPCs active: {', '.join(npc_outputs.keys()) or 'none'}\n"
            f"AI PCs active: {', '.join(ai_pc_outputs.keys()) or 'none'}\n"
            f"Player action: {player_action}"
        )

        resolution_crew = build_resolution_crew(check_specs, scribe_ctx, full_turn_summary)
        with verbose_to_file(verbose_path):
            resolution_crew.kickoff()

        for task in resolution_crew.tasks:
            if task.agent.role == "Rules Engine" and task.output:
                result_text = task.output.raw.strip()
                if result_text and "no check" not in result_text.lower():
                    print(f"\n[Referee]\n{result_text}")

        scribe_summary = _get_task_output(resolution_crew, "State Keeper")
        log.info(f"Phase 3 complete: {len(check_specs)} checks resolved")

        # ── State writes ──────────────────────────────────────────────────────
        all_last_actions = {**npc_outputs, **ai_pc_outputs, "Z-4P0": player_action}
        update_scene_state({"last_actions": all_last_actions})

        if scribe_summary:
            log_path = Path("state/session_log.md")
            with log_path.open("a") as f:
                f.write(f"{scribe_summary}\n")
            log.info(f"Session log: {scribe_summary[:120]}")

        # ── Beat advancement ──────────────────────────────────────────────────
        choice = _beat_prompt(scene, current_beat)
        if choice in ("quit", "exit", "q"):
            print("Session ended.")
            log.info("Session ended by player.")
            break

        if choice == "stay":
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
