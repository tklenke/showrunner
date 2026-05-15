# Programmer TODO

Reference documents:
- `docs/plans/terminology.md` — canonical terms
- `docs/plans/game_loop.md` — source of truth for the turn loop
- `docs/plans/architecture.md` — system design
- `docs/plans/character_schema.md` — character file schema

---

## Phase 4 — End-to-End Scene Playthrough

### [x] 4.40 — SR-driven beat advancement

Replace the manual `[a / beat-id / Enter]` prompt with a Show Runner call that decides
whether to advance the beat after each turn.

---

#### Turn loop placement

Insert between Step 8 (last-action extraction) and Step 9 (plan update):

```
8.   Last-action extraction  (unchanged)
8.5  SR beat advance check   ← NEW
9.   Plan update             (runs with new beat already set if advanced)
```

If the beat advances, **reload `active_chars` from the new beat's `active_ids`** before
Step 9 runs, so plans are written for the characters who are actually present in the new beat.

---

#### New task prompt — `config/prompts/task_run_beat_advance.md`

```
## Current Beat
{current_beat_title}

## Next Beat Trigger
{next_beat_trigger}

## What just happened
{results_text}

## Last actions
{last_actions}

The next beat begins when its trigger condition is met.
Has that condition been met by what just happened this turn?

Output exactly one word: ADVANCE or STAY
```

---

#### New function — `run_beat_advance` in `runner.py`

```python
def run_beat_advance(
    current_beat_title: str,
    next_beat_trigger: str,
    results_text: str,
    last_actions: str,
) -> bool:
    """Ask the Show Runner whether the current beat's exit condition has been met.

    Returns True if the SR responds ADVANCE, False otherwise.
    Returns False (stay) if there is no next beat.
    """
```

- One `call_llm("show_runner", ...)` call.
- Parse response: if the word `ADVANCE` appears (case-insensitive), return `True`; otherwise `False`.
- If `next_beat_trigger` is empty (no next beat exists), return `False` without calling the LLM.

---

#### Orchestrator changes

**Between Step 8 and Step 9:**

```python
# ── Step 8.5: SR beat advancement ────────────────────────────────────────
next_id = _next_beat_id(scene, current_beat)
if next_id:
    next_beat = next((b for b in beat_list if b["id"] == next_id), {})
    should_advance = run_beat_advance(
        current_beat_title=beat.get("title", current_beat),
        next_beat_trigger=next_beat.get("trigger", ""),
        results_text=results_text,
        last_actions="\n".join(f"{k}: {v}" for k, v in last_actions_extracted.items()),
    )
    if should_advance:
        advance_beat(next_id)
        log.info(f"SR advanced beat: {current_beat} → {next_id}")
        # Reload active roster for the new beat before plan update
        active_ids = _active_npc_ids(scene, next_id)
        npc_chars = load_scene_characters(scene, scene_state, player_filter="npc", active_ids=active_ids)
        companion_chars = load_scene_characters(scene, scene_state, player_filter="companion")
        active_chars = {**npc_chars, **companion_chars}
```

**`_beat_prompt`** — keep the function but only call it in `--verbose` mode, after the SR
decision, as a manual override. Print the SR's decision before showing the prompt so Tom
can see what the SR chose.

```python
if verbose:
    sr_decision = "ADVANCE" if should_advance else "STAY"
    print(f"[SR beat decision: {sr_decision}]")
    choice = _beat_prompt(scene, scene_state.get("current_beat", current_beat))
    # apply manual override if given ...
```

**Remove** the unconditional `_beat_prompt` call from its current position at the bottom
of the loop.

---

#### `game_loop.md` update

Add Step 8.5 to the turn loop table and step descriptions. The existing Step 8 and Step 9
entries are unchanged; just insert the new step between them.

---

Follow TDD. Key tests:
- `run_beat_advance` returns `True` when LLM responds with any casing of "ADVANCE"
- `run_beat_advance` returns `False` for "STAY" and any other response
- `run_beat_advance` returns `False` without calling LLM when `next_beat_trigger` is empty
- Orchestrator reloads `active_chars` after advancing (integration: verify correct char set
  is passed to `run_plan_update` after a beat change)

---

### [~] 4.33 — Play through scene_0.yaml

Run `python -m showrunner.main -v --dump-prompts --reset` and play the Bargos mansion
scene from entry to exit.

- [ ] Scene entry read-aloud delivered
- [ ] Bargos audience beat runs; Negotiation check can be triggered
- [ ] Gamorrean warning beat triggers; Vigilance check fires
- [ ] Gamorrean Rumble combat resolves with dice (auto or manual input)
- [ ] Wounds tracked correctly; minions die at wound threshold multiples
- [ ] Mission brief beat runs after combat
- [ ] Scene exits cleanly; scene_state.yaml updated

Fix any bugs found. Raise architectural issues with Tom before implementing.

---

## Phase 100 — Web App (Starlette)

Do not begin until Phase 4 playthrough is signed off.

See `docs/plans/architect_todo.md` Phase 100 for full design rationale and decisions.

---

### [x] 100.1 — Async LLM calls

Convert `call_llm()` in `llm.py` to an async version using `litellm.acompletion()`.
Keep the synchronous `call_llm()` for the CLI path until 100.3 is done; add
`call_llm_async()` alongside it. Update all callers in `runner.py` once the CLI
adapter (100.3) is ready.

Follow TDD. Key tests:
- `call_llm_async()` returns the same response shape as `call_llm()`
- `call_llm_async()` passes prompt logging arguments correctly
- All existing `runner.py` tests still pass after callers are updated

---

### [x] 100.2 — Remove verbose mode; enrich session log

Remove `_beat_prompt()`, the `--verbose` / `-v` flag, and all `if verbose:` branches
from `orchestrator.py` and `main.py`. Beat progression is fully SR-driven (4.40);
manual beat override is gone.

Add richer writes to `state/session_log.md` in place of what verbose mode revealed:
- SR beat decision (ADVANCE/STAY) and the beat being evaluated
- Check specs identified in Step 5
- Rulings summary from Step 6
- Plan update summary from Step 9

Follow TDD. Key tests:
- Session log contains SR beat decision after a turn
- Session log contains check specs when checks are identified
- Session log contains `NO_CHECKS` when no checks fire
- `--verbose` flag is rejected by the CLI (or silently ignored — pick one)
- `_beat_prompt` is gone; no code path calls it

---

### [x] 100.3 — Async turn loop + CLI adapter

Convert `run_turn_loop()` to an async generator: `async def run_turn_loop(scene, queue)`.
The generator yields typed event dicts (see event types below) and suspends at 3 input
points via `await queue.get()`.

**Event types** (yield these dicts):
```python
{"type": "narrative",    "text": "..."}
{"type": "status",       "text": "..."}          # beat/turn header
{"type": "dice_prompt",  "actor": "...", "skill": "...", "pool": "...",
                         "difficulty": "...", "notes": "..."}
{"type": "player_prompt"}
{"type": "parse_error",  "context": "..."}
{"type": "session_end",  "reason": "..."}
```

**Input suspension points** — `await queue.get()` at:
1. Player action (replaces `prompt_player_action`)
2. Dice result per check spec (replaces `input()` in `_roll_specs` — loops)
3. Parse failure correction (replaces `input()` in `parse_structured`)

**CLI adapter** — `src/showrunner/cli_adapter.py`. Drives the async generator from
the terminal:
- Renders events to stdout (narrative → print, dice_prompt → print pool description,
  player_prompt → print divider)
- Reads input via `await loop.run_in_executor(None, input, prompt)` and puts into queue
- Entry point replaces current `run_turn_loop()` call in `main.py`

Follow TDD. Key tests:
- Generator yields `player_prompt` event before suspending on player input
- Generator yields `dice_prompt` event for each check spec before suspending
- Generator yields `narrative` event containing resolution narrative text
- Generator yields `session_end` when quit input received
- CLI adapter drives a full turn with mocked LLM calls and fake queue input
- Quit input from CLI terminates the generator cleanly

---

### [x] 100.4 — Starlette web layer

`src/showrunner/web/app.py` — the Starlette application.

**SSE endpoint** `GET /play`:
- Creates an `asyncio.Queue` for this session
- Starts `run_turn_loop(scene, queue)` as a background task
- Streams generator events as JSON-encoded SSE: `data: {"type": "...", ...}\n\n`
- On disconnect: cancels the background task, calls `--reset` logic, clears state

**POST endpoint** `POST /play/input`:
- Accepts `{"value": "..."}` JSON body
- Puts `value` into the session queue
- Returns 204

**Session manager** — module-level dict `_session: dict` holding the single active
session `{queue, task}`. v0 is single-user; a second connection cancels the first.

**Static files** — serve `src/showrunner/web/static/` at `/`.

Follow TDD. Key tests:
- GET /play streams SSE events from the generator
- POST /play/input puts value into the queue and returns 204
- Disconnect cancels the generator task and resets state
- Second connection cancels the first session

---

### [ ] 100.5 — Frontend

`src/showrunner/web/static/index.html` — single file, no build step.

- SSE connection to `GET /play`; event handler dispatches on `type`:
  - `narrative` → append rendered markdown (Marked.js) to chat div
  - `status` → append styled header line
  - `dice_prompt` → show pool description + text input + "Auto-roll" button
  - `player_prompt` → show action text input + submit button
  - `parse_error` → show error message + correction input
  - `session_end` → show end message, disable inputs
- Input submission: POST `{"value": "..."}` to `/play/input`
- Input box disabled while waiting for `player_prompt` or `dice_prompt` event
- Auto-scroll to bottom on new content

No framework. Vanilla JS + Marked.js via CDN.

Manual test (no automated tests for frontend):
- Load page, full turn runs, narrative renders correctly
- Dice prompt appears with pool description; auto-roll and manual input both work
- Player action input submits and triggers next turn
- Disconnect and reload resets to scene 0

---

### [ ] 100.6 — Deployment

- `deploy/showrunner.service` — systemd unit: `uvicorn showrunner.web.app:app --host 127.0.0.1 --port 8000`
- `deploy/nginx.conf` — reverse proxy to uvicorn; serve static files directly; TLS via Let's Encrypt
- README section: how to deploy to AWS t4g.small, install deps, enable service

---

## Phase 5 — Genesys Rules Parser

Do not begin until Phase 4 playthrough is signed off.

- [ ] `tools/parse_rulebook.py` — extract PDF sections to `skin/rules/` (use pymupdf)
- [ ] `skin/rules/index.md` — section list with page references
- [ ] `rules_lookup(keyword) -> str` in `src/showrunner/tools/rules_lookup.py`
- [ ] Wire `rules_lookup()` into Show Runner agent
- [ ] Smoke test: can retrieve rules for "critical injury", "soak", "Brawl"

---

## Phase 6 — OggDude Data Ingestion

Do not begin until Phase 5 is complete.

- [ ] `tools/xml_to_md.py` — convert OggDude XML exports to `skin/data/`
- [ ] Smoke test: Show Runner can look up Gamorrean vibro-ax stats from `weapons.md`
