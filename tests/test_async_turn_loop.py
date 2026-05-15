# ABOUTME: Tests for the async turn loop generator (100.3) and CLI adapter.
# ABOUTME: Verifies event types, suspension points, and the full async generator contract.

import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scene():
    return {
        "scene_id": "scene_0",
        "scene_num": 0,
        "title": "Test Scene",
        "location": {"read_aloud": "You are in a room."},
        "beats": [
            {"id": "beat_0", "title": "Opening", "trigger": ""},
            {"id": "beat_1", "title": "Conflict", "trigger": "When the alarm sounds."},
        ],
        "characters_present": [],
        "inline_npcs": [],
        "minion_groups": [],
    }


def _patch_context(tmp_path, llm_responses):
    """Return a stack of patches needed to run the async turn loop in tests."""
    from contextlib import ExitStack
    import contextlib

    stack = ExitStack()
    # LLM calls go through litellm.acompletion in both runner and orchestrator
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "mock"

    responses = list(llm_responses)

    async def _acompletion(**kwargs):
        if responses:
            val = responses.pop(0)
        else:
            val = "default"
        r = MagicMock()
        r.choices[0].message.content = val
        return r

    stack.enter_context(patch("litellm.acompletion", side_effect=_acompletion))
    stack.enter_context(patch("showrunner.orchestrator.initialize_scene_state"))
    stack.enter_context(patch("showrunner.orchestrator.initialize_npc_stats"))
    stack.enter_context(patch("showrunner.orchestrator.load_scene_yamls", return_value={}))
    stack.enter_context(patch("showrunner.orchestrator.load_scene_state",
                              return_value={"current_beat": "beat_0", "last_actions": {}}))
    stack.enter_context(patch("showrunner.orchestrator.load_party_stats", return_value={}))
    stack.enter_context(patch("showrunner.orchestrator.render_show_runner_context", return_value="sr ctx"))
    stack.enter_context(patch("showrunner.orchestrator.render_narrator_context", return_value="nar ctx"))
    stack.enter_context(patch("showrunner.orchestrator.render_actor_beat_context", return_value="beat ctx"))
    stack.enter_context(patch("showrunner.orchestrator._active_npc_ids", return_value=[]))
    stack.enter_context(patch("showrunner.orchestrator.load_scene_characters", return_value={}))
    stack.enter_context(patch("showrunner.orchestrator.setup_instrumentation",
                              return_value=Path(tmp_path / "prompts.log")))
    stack.enter_context(patch("showrunner.orchestrator.apply_litellm_settings"))
    stack.enter_context(patch("showrunner.orchestrator.update_scene_state"))
    stack.enter_context(patch("showrunner.orchestrator.advance_beat"))
    return stack


# ---------------------------------------------------------------------------
# Async turn loop generator contract
# ---------------------------------------------------------------------------

async def test_run_turn_loop_async_yields_player_prompt_before_input(tmp_path, monkeypatch):
    """Generator yields player_prompt event before suspending for player input."""
    from showrunner.orchestrator import run_turn_loop_async
    monkeypatch.chdir(tmp_path)
    (tmp_path / "state").mkdir()
    (tmp_path / "logs").mkdir()

    scene = _make_scene()
    queue = asyncio.Queue()

    with _patch_context(tmp_path, ["beat opener"]):
        await queue.put("q")
        events = [e async for e in run_turn_loop_async(scene, queue)]

    types = [e["type"] for e in events]
    assert "player_prompt" in types, f"Expected player_prompt in {types}"


async def test_run_turn_loop_async_yields_narrative_event(tmp_path, monkeypatch):
    """Generator yields a narrative event containing resolution narrative text."""
    from showrunner.orchestrator import run_turn_loop_async
    monkeypatch.chdir(tmp_path)
    (tmp_path / "state").mkdir()
    (tmp_path / "logs").mkdir()

    scene = _make_scene()
    queue = asyncio.Queue()

    # Exact LLM call order in the loop with one player action (no NPCs/companions):
    # 1. run_beat_opener_async (narrator)
    # 2. run_summaries_async Z-4P0 (scribe)
    # 3. run_checks_async Z-4P0 (referee) → must return "NO_CHECKS" to avoid repair path
    # 4. run_narrative_async (narrator)
    # 5. run_last_actions_async Z-4P0 (scribe)
    # 6. run_beat_advance_async (show_runner)
    llm_responses = [
        "Beat opener text.",    # 1
        "Z-4P0 looked around.", # 2 summaries
        "NO_CHECKS",            # 3 checks — must be NO_CHECKS to avoid parse repair
        "The scene resolves.",  # 4 narrative
        "last action text",     # 5 last actions
        "STAY",                 # 6 beat advance
    ]

    with _patch_context(tmp_path, llm_responses):
        await queue.put("I look around.")
        await queue.put("q")
        events = [e async for e in run_turn_loop_async(scene, queue)]

    narrative_events = [e for e in events if e["type"] == "narrative"]
    assert narrative_events, f"Expected narrative events, got: {[e['type'] for e in events]}"
    texts = " ".join(e["text"] for e in narrative_events)
    assert "opener" in texts.lower() or "resolves" in texts.lower() or "room" in texts.lower(), texts


async def test_run_turn_loop_async_yields_session_end_on_quit(tmp_path, monkeypatch):
    """Generator yields session_end event when player inputs quit."""
    from showrunner.orchestrator import run_turn_loop_async
    monkeypatch.chdir(tmp_path)
    (tmp_path / "state").mkdir()
    (tmp_path / "logs").mkdir()

    scene = _make_scene()
    queue = asyncio.Queue()

    with _patch_context(tmp_path, ["opener"]):
        await queue.put("q")
        events = [e async for e in run_turn_loop_async(scene, queue)]

    end_events = [e for e in events if e["type"] == "session_end"]
    assert end_events, f"Expected session_end, got: {[e['type'] for e in events]}"
    assert end_events[0]["reason"] == "player_quit"


async def test_run_turn_loop_async_yields_dice_prompt_for_check_specs(tmp_path, monkeypatch):
    """Generator yields dice_prompt event for each check spec before suspending."""
    from showrunner.orchestrator import run_turn_loop_async
    monkeypatch.chdir(tmp_path)
    (tmp_path / "state").mkdir()
    (tmp_path / "logs").mkdir()

    # Need a scene with characters so checks fire
    scene = _make_scene()
    queue = asyncio.Queue()

    check_line = "Bargos | Negotiation | Presence 4 | 2 | Average |"

    # Patch run_checks_async to return a check directly (avoids char loop complexity)
    with _patch_context(tmp_path, ["opener", "Bargos passed.", "The scene resolves.", "last act", "STAY", "overall plan"]):
        with patch("showrunner.orchestrator.run_checks_async",
                   new=AsyncMock(return_value=f"1. {check_line}")):
            with patch("showrunner.orchestrator.run_summaries_async", new=AsyncMock()):
                await queue.put("I negotiate.")   # player action
                await queue.put("")               # auto-roll the dice prompt
                await queue.put("q")              # quit next turn

                events = [e async for e in run_turn_loop_async(scene, queue)]

    dice_events = [e for e in events if e["type"] == "dice_prompt"]
    assert dice_events, f"Expected dice_prompt events, got: {[e['type'] for e in events]}"
    assert dice_events[0]["actor"] == "Bargos"
    assert dice_events[0]["skill"] == "Negotiation"


# ---------------------------------------------------------------------------
# CLI adapter
# ---------------------------------------------------------------------------

async def test_cli_adapter_drives_full_turn(tmp_path, monkeypatch, capsys):
    """CLI adapter drives the async generator and prints output to stdout."""
    from showrunner.cli_adapter import run_cli
    monkeypatch.chdir(tmp_path)
    (tmp_path / "state").mkdir()
    (tmp_path / "logs").mkdir()

    scene = _make_scene()
    llm_responses = [
        "Beat opener.",         # beat opener
        "Z-4P0 acted.",         # summaries
        "NO_CHECKS",            # checks — NO_CHECKS avoids parse repair
        "The scene resolves.",  # narrative
        "last act",             # last actions
        "STAY",                 # beat advance
    ]

    with _patch_context(tmp_path, llm_responses):
        inputs = iter(["I look around.", "q"])
        with patch("showrunner.cli_adapter.input", side_effect=inputs):
            await run_cli(scene)

    out = capsys.readouterr().out
    assert "Beat opener." in out or "scene resolves" in out.lower() or "room" in out.lower()


async def test_cli_adapter_terminates_cleanly_on_quit(tmp_path, monkeypatch):
    """CLI adapter terminates without error when quit is entered."""
    from showrunner.cli_adapter import run_cli
    monkeypatch.chdir(tmp_path)
    (tmp_path / "state").mkdir()
    (tmp_path / "logs").mkdir()

    scene = _make_scene()

    with _patch_context(tmp_path, ["opener"]):
        with patch("showrunner.cli_adapter.input", return_value="q"):
            await run_cli(scene)  # must not raise
