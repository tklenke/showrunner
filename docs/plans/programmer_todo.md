# Programmer TODO

Reference documents:
- `docs/plans/terminology.md` — canonical terms
- `docs/plans/game_loop.md` — source of truth for the turn loop
- `docs/plans/architecture.md` — system design
- `docs/plans/character_schema.md` — character file schema

---

## Phase 4 — End-to-End Scene Playthrough

### [ ] 4.40 — SR-driven beat advancement

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
