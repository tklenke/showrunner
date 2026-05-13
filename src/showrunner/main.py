# ABOUTME: CLI entry point — starts a session, loads state, hands off to the turn loop.
# ABOUTME: Supports player input, ! directives, and manual dice entry.

import argparse
import logging
import os
import sys

from dotenv import load_dotenv

logging.getLogger("opentelemetry").setLevel(logging.ERROR)
logging.getLogger("crewai.telemetry").setLevel(logging.ERROR)

from showrunner.orchestrator import run_turn_loop
from showrunner.tools.state_reader import load_adventure_scene


def main() -> None:
    """Start a showrunner session."""
    load_dotenv()

    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY not set. Add it to .env or export it.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Run a showrunner session.")
    parser.add_argument("scene", nargs="?", type=int, default=0, help="Scene number (default: 0)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print beat titles on transition")
    args = parser.parse_args()

    scene = load_adventure_scene(args.scene)
    run_turn_loop(scene, verbose=args.verbose)


if __name__ == "__main__":
    main()
