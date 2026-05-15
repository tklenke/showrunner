# ABOUTME: CLI adapter for the async turn loop — drives run_turn_loop_async from the terminal.
# ABOUTME: Renders events to stdout and feeds player input into the async queue.

import asyncio
from pathlib import Path

from showrunner.orchestrator import run_turn_loop_async

_DIVIDER = "─" * 60


def _render_event(event: dict) -> None:
    """Print an event to stdout based on its type."""
    t = event.get("type")
    if t == "narrative":
        print(event["text"])
    elif t == "status":
        print(event["text"])
    elif t == "dice_prompt":
        print(f"\n{_DIVIDER}")
        print(f"  Roll: {event['actor']} — {event['skill']} | {event['difficulty']}")
        print(f"  Pool: {event['pool']}")
        if event.get("notes"):
            print(f"  Notes: {event['notes']}")
    elif t == "player_prompt":
        pass  # input() is called immediately after by the adapter
    elif t == "parse_error":
        print(f"[Parse failed for: {event.get('context', 'unknown')}]")
    elif t == "session_end":
        reason = event.get("reason", "")
        if reason == "scene_complete":
            print("Scene complete.")
        else:
            print("Session ended.")


async def run_cli(scene: dict) -> None:
    """Drive the async turn loop from the terminal."""
    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_event_loop()

    async def _read_input(prompt: str) -> str:
        return await loop.run_in_executor(None, input, prompt)

    gen = run_turn_loop_async(scene, queue)
    async for event in gen:
        _render_event(event)

        if event["type"] == "player_prompt":
            print(f"\n{_DIVIDER}")
            text = await _read_input("  What do you and your companions do? > ")
            await queue.put(text)

        elif event["type"] == "dice_prompt":
            text = await _read_input("  Enter result (S2A1T1) or Enter to auto-roll: ")
            await queue.put(text)

        elif event["type"] == "parse_error":
            text = await _read_input("  Enter correction (or press Enter to skip): ")
            await queue.put(text)
