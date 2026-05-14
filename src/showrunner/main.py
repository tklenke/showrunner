# ABOUTME: CLI entry point — starts a session, loads state, hands off to the turn loop.
# ABOUTME: Supports player input, ! directives, and manual dice entry.

import argparse
import logging
import os
import shutil
import sys
from pathlib import Path

import litellm
from dotenv import load_dotenv

logging.getLogger("opentelemetry").setLevel(logging.ERROR)
logging.getLogger("crewai.telemetry").setLevel(logging.ERROR)
logging.getLogger("LiteLLM").setLevel(logging.ERROR)
logging.getLogger("LiteLLM Router").setLevel(logging.ERROR)
litellm.suppress_debug_info = True

from showrunner.orchestrator import run_turn_loop
from showrunner.tools.state_reader import load_adventure_scene


def reset_session(state_dir: str = "state", logs_dir: str = "logs") -> None:
    """Delete scene state and all log files so the next run starts fresh.

    Preserves party_stats.yaml (wound/strain tracking survives a reset by design;
    delete manually if you want a fully clean slate).
    """
    state = Path(state_dir)
    logs = Path(logs_dir)

    for name in ("scene_state.yaml", "session_log.md"):
        target = state / name
        if target.exists():
            target.unlink()

    if logs.exists():
        for item in logs.rglob("*"):
            if item.is_file():
                item.unlink()


def main() -> None:
    """Start a showrunner session."""
    load_dotenv()

    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY not set. Add it to .env or export it.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Run a showrunner session.")
    parser.add_argument("scene", nargs="?", type=int, default=0, help="Scene number (default: 0)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print beat titles on transition")
    parser.add_argument("--dump-prompts", action="store_true", help="Write full prompt+response MD files to logs/prompts/")
    parser.add_argument("--reset", action="store_true", help="Clear all logs and scene state before starting")
    args = parser.parse_args()

    if args.reset:
        reset_session()
        print("Session reset: logs and scene state cleared.")

    scene = load_adventure_scene(args.scene)
    run_turn_loop(scene, verbose=args.verbose, dump_prompts=args.dump_prompts)


if __name__ == "__main__":
    main()
