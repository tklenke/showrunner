# ABOUTME: CLI entry point — starts a session, loads state, hands off to the turn loop.
# ABOUTME: Supports player input, ! directives, and manual dice entry.

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from showrunner.orchestrator import run_turn_loop


def main() -> None:
    """Start a showrunner session."""
    load_dotenv()

    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY not set. Add it to .env or export it.")
        sys.exit(1)

    scene = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else (
        "The party stands in the receiving hall of Bargos the Hutt's estate on Gavos. "
        "The air reeks of sulfur from the gas mines. A Gamorrean guard eyes you from the corner."
    )

    run_turn_loop(scene)


if __name__ == "__main__":
    main()
