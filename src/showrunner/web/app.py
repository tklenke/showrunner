# ABOUTME: Starlette web application — SSE endpoint streams turn events; POST feeds player input.
# ABOUTME: Single-session v0: a second connection cancels the first.

import asyncio
import json
import logging
from pathlib import Path
from typing import AsyncGenerator, Callable

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

_log = logging.getLogger(__name__)

_STATIC_DIR = Path(__file__).parent / "static"


async def _sse_play(request: Request) -> Response:
    """GET /play — streams generator events as JSON-encoded SSE."""
    scene = request.app.state.scene
    generator_factory = request.app.state.generator_factory
    session = request.app.state.session

    # Cancel any existing session (second connection cancels first)
    if session.get("task") and not session["task"].done():
        session["task"].cancel()
        try:
            await session["task"]
        except (asyncio.CancelledError, Exception):
            pass
    session.clear()

    queue: asyncio.Queue = asyncio.Queue()
    session["queue"] = queue

    async def _event_generator() -> AsyncGenerator[bytes, None]:
        gen = generator_factory(scene, queue)
        try:
            async for event in gen:
                data = json.dumps(event)
                yield f"data: {data}\n\n".encode()
                if event.get("type") == "session_end":
                    break
        except asyncio.CancelledError:
            pass
        finally:
            session.clear()

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def _post_input(request: Request) -> Response:
    """POST /play/input — puts value into the session queue; returns 204."""
    session = request.app.state.session
    if "queue" not in session:
        return Response(status_code=404)
    body = await request.json()
    value = body.get("value", "")
    await session["queue"].put(value)
    return Response(status_code=204)


def create_server_app() -> Starlette:
    """Factory for uvicorn --factory: loads scene from APP_SCENE env var (default 0)."""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    scene_num = int(os.environ.get("APP_SCENE", "0"))
    from showrunner.tools.state_reader import load_adventure_scene
    scene = load_adventure_scene(scene_num)
    return create_app(scene)


def create_app(scene: dict, generator_factory: Callable | None = None) -> Starlette:
    """Create the Starlette application.

    generator_factory(scene, queue) defaults to run_turn_loop_async.
    """
    if generator_factory is None:
        from showrunner.orchestrator import run_turn_loop_async
        generator_factory = run_turn_loop_async

    routes = [
        Route("/play", _sse_play, methods=["GET"]),
        Route("/play/input", _post_input, methods=["POST"]),
    ]

    if _STATIC_DIR.exists():
        routes.append(Mount("/", app=StaticFiles(directory=str(_STATIC_DIR), html=True)))

    app = Starlette(routes=routes)
    app.state.scene = scene
    app.state.generator_factory = generator_factory
    app.state.session = {}
    return app
