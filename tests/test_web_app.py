# ABOUTME: Tests for the Starlette web layer (100.4) — SSE endpoint, POST input, session management.
# ABOUTME: Uses httpx AsyncClient to test GET /play streaming and POST /play/input.

import asyncio
import json
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
        "beats": [{"id": "beat_0", "title": "Opening", "trigger": ""}],
        "characters_present": [],
        "inline_npcs": [],
        "minion_groups": [],
    }


async def _simple_generator(scene, queue):
    """Minimal fake generator for testing the SSE layer without the full turn loop."""
    yield {"type": "narrative", "text": "Hello from the generator."}
    yield {"type": "player_prompt"}
    player_action = await queue.get()
    if player_action.strip().lower() in ("q", "quit"):
        yield {"type": "session_end", "reason": "player_quit"}
        return
    yield {"type": "narrative", "text": f"You said: {player_action}"}
    yield {"type": "session_end", "reason": "scene_complete"}


# ---------------------------------------------------------------------------
# SSE endpoint: GET /play
# ---------------------------------------------------------------------------

async def test_get_play_streams_sse_events(tmp_path, monkeypatch):
    """GET /play streams JSON-encoded SSE events from the generator."""
    import httpx
    from showrunner.web.app import create_app

    monkeypatch.chdir(tmp_path)
    (tmp_path / "state").mkdir()

    async def _selfcomplete_gen(scene, queue):
        yield {"type": "narrative", "text": "Hello from the generator."}
        yield {"type": "player_prompt"}
        yield {"type": "session_end", "reason": "scene_complete"}

    app = create_app(scene=_make_scene(), generator_factory=_selfcomplete_gen)

    events = []
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream("GET", "/play") as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers.get("content-type", "")
            async for line in resp.aiter_lines():
                if line.startswith("data:"):
                    events.append(json.loads(line[5:].strip()))

    types = [e["type"] for e in events]
    assert "narrative" in types
    assert "player_prompt" in types


async def test_post_play_input_enqueues_value_and_returns_204(tmp_path, monkeypatch):
    """POST /play/input puts value into the queue and returns 204."""
    import httpx
    from showrunner.web.app import create_app

    monkeypatch.chdir(tmp_path)
    (tmp_path / "state").mkdir()

    app = create_app(scene=_make_scene(), generator_factory=_simple_generator)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Start SSE in background so session is initialized
        sse_task = asyncio.create_task(
            client.get("/play")
        )
        # Give the SSE handler a moment to initialize and yield player_prompt
        await asyncio.sleep(0.1)

        resp = await client.post("/play/input", json={"value": "test input"})
        assert resp.status_code == 204

        sse_task.cancel()
        try:
            await sse_task
        except (asyncio.CancelledError, Exception):
            pass


async def test_post_play_input_without_active_session_returns_404(tmp_path, monkeypatch):
    """POST /play/input with no active session returns 404."""
    import httpx
    from showrunner.web.app import create_app

    monkeypatch.chdir(tmp_path)
    (tmp_path / "state").mkdir()

    app = create_app(scene=_make_scene(), generator_factory=_simple_generator)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/play/input", json={"value": "hello"})
        assert resp.status_code == 404


async def test_sse_session_end_event_terminates_stream(tmp_path, monkeypatch):
    """When the generator yields session_end, the SSE stream closes."""
    import httpx
    from showrunner.web.app import create_app

    monkeypatch.chdir(tmp_path)
    (tmp_path / "state").mkdir()

    async def _quit_gen(scene, queue):
        yield {"type": "session_end", "reason": "scene_complete"}

    app = create_app(scene=_make_scene(), generator_factory=_quit_gen)

    events = []
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream("GET", "/play") as resp:
            async for line in resp.aiter_lines():
                if line.startswith("data:"):
                    events.append(json.loads(line[5:].strip()))

    assert any(e.get("type") == "session_end" for e in events)
