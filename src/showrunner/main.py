# ABOUTME: CLI entry point — starts a session, loads state, hands off to the turn loop.
# ABOUTME: Supports player input, ! directives, and manual dice entry.

import logging
import os
import sys

from dotenv import load_dotenv

logging.getLogger("opentelemetry").setLevel(logging.ERROR)
logging.getLogger("crewai.telemetry").setLevel(logging.ERROR)

from showrunner.orchestrator import run_turn_loop
from showrunner.tools.state_reader import load_adventure_scene
from showrunner.tools.state_writer import initialize_scene_state


def main() -> None:
    """Start a showrunner session."""
    load_dotenv()

    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY not set. Add it to .env or export it.")
        sys.exit(1)

    n = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    scene = load_adventure_scene(n)
    initialize_scene_state(n, scene["beats"][0]["id"])

    run_turn_loop(scene)


if __name__ == "__main__":
    main()
