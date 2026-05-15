# Tom Blockers

Questions and decisions made autonomously during Phase 100 implementation.
Flagged here for Tom's review — no work was blocked.

---

## Phase 4.33 prerequisite

**Decision:** Proceeding with Phase 100 per Tom's explicit instruction.
The programmer_todo.md says "Do not begin until Phase 4 playthrough is signed off"
but Tom waived this.

---

## pytest-asyncio configuration

**Decision:** Added `asyncio_mode = "auto"` to `[tool.pytest.ini_options]` in
`pyproject.toml`. This makes all async test functions run under asyncio automatically,
removing the need for `@pytest.mark.asyncio` decorators.

---

## New dependencies added to requirements.txt

**Decision:** Added the following packages (all required by the spec):
- `starlette>=0.40` — web framework for Phase 100.4
- `uvicorn>=0.30` — ASGI server for Phase 100.6
- `httpx>=0.27` — async HTTP client for testing the web layer
- `pytest-asyncio>=0.23` — async test support for Phase 100.1+

---

## Per-NPC output streaming

**Decision:** In the async turn loop (100.3), NPC and companion outputs are
yielded as a batch after all calls for that wave complete, not streamed
individually as each LLM call finishes. This simplifies the runner.py interface
significantly. If per-NPC streaming is desired for UX, it requires making runner
functions async generators — a bigger interface change. For now, YAGNI.

**Impact:** Web clients will see all NPC dialogue appear at once after the wave
completes, not one character at a time.

---

## parse_structured async pattern

**Decision:** `parse_structured` becomes an async generator (`_parse_structured_async`)
that yields `parse_error` events and stores the result in a mutable dict. The caller
uses `async for event in _parse_structured_async(..., result_out): yield event`.
This is needed because Python async generators cannot return values, so we use the
mutable container pattern.

---

## verbose flag removal (100.2)

**Decision:** The `--verbose` / `-v` CLI flag is removed. argparse will reject it
as an unrecognized argument if a user passes it. This is "rejected" in the spec's
sense. No silent-ignore shim added.

---

## Session log format (100.2)

**Decision:** Each turn's structured entries are written in a lightweight format:
```
[Beat: {beat_id} | Turn {n}]
SR decision: ADVANCE → {next_id}   (or STAY)
Checks: 1. Actor | Skill | ...     (or NO_CHECKS)
Rulings: Actor: [ruling summary]
Plans: {char_id}: [plan text]
```
No markdown headers — keeps the log scan-friendly without too much markup.

---

## 100.6 TLS/certbot

**Decision:** The nginx.conf includes a commented-out HTTPS section with a
placeholder for Let's Encrypt. The README instructions cover running certbot
manually. Full automated certbot setup is out of scope for this phase.

---

## Marked.js CDN

**Decision:** Using `https://cdn.jsdelivr.net/npm/marked/marked.min.js` per spec.
This requires internet access from the client browser.
