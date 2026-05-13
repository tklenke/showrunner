# Programmer TODO

Implementation tasks for the showrunner engine.
Follow TDD: write the failing test first, then write only enough code to make it pass.

Reference documents:
- `docs/plans/terminology.md` — **canonical terms; read before touching any character or turn-loop code**
- `docs/plans/architecture.md` — system design
- `docs/plans/character_schema.md` — character file schema and `render_actor_prompt` spec
- `docs/plans/architect_todo.md` — phased plan with open decisions

---

## Current Priority: Phase 4 — End-to-End Scene Playthrough

### [ ] 4.19 — Terminology: rename `player: "ai"` → `"companion"` across Python code

Docs and YAML files are already updated. This task propagates the change into Python.

**`player` field value:** `"ai"` → `"companion"` in all comparisons and string literals.

Files to update:
- `src/showrunner/runner.py` — `player == "ai"` guard in `run_pc_wave()`
- `src/showrunner/orchestrator.py` — any `player == "ai"` filtering
- `src/showrunner/agents/actors.py` — any `"ai"` string references
- `tests/test_runner.py`, `tests/test_actors.py`, `tests/test_orchestrator.py` — fixture data and assertions

**Function rename:** `run_pc_wave` → `run_companion_wave` in `runner.py` and all call sites
(`orchestrator.py`, `tests/test_runner.py`, `tests/test_orchestrator.py`).

Note: update 4.17's "keep them" note — `run_pc_wave` is now included in the rename list.

**Terms to replace in comments/docstrings:** "AI PC", "ai party member", "AI party member" → "Companion".

No logic changes — pure rename/string substitution. Run full test suite after.

---

### [ ] 4.17 — Rename runner.py functions: drop `_phase` suffix

The `_phase` suffix on runner functions conflicts with the "step" vocabulary used in
`game_loop.md`. Rename for consistency. **Do this before 4.16** — the instrumentation
log will show calling function names, so they should be right first.

| Current name | New name |
|---|---|
| `run_summary_phase` | `run_summaries` |
| `run_check_phase` | `run_checks` |
| `run_ruling_phase` | `run_rulings` |
| `run_narrative_phase` | `run_narrative` |
| `run_last_action_phase` | `run_last_actions` |
| `run_scribe_phase` | `run_scribe` |

`run_npc_wave` and `run_pc_wave` are already clean — keep them.

Update all import and call sites: `orchestrator.py`, `tests/test_runner.py`,
`tests/test_orchestrator.py`. No logic changes — pure rename.

Tests: update test function names that reference the old names; verify full suite passes.

---

### [~] 4.16 — Concise per-call instrumentation log

Replace the verbose full-content prompt/response log with a single summary line per LLM call.
**Do 4.17 first** — the log captures the calling function name automatically.

**Log format** — one line per call:
```
HH:MM:SS  show_runner  sardinia  run_npc_wave    1247p →  342r
HH:MM:SS  narrator     sardinia  run_npc_wave     892p →  218r
HH:MM:SS  actors       sardinia  run_summaries    534p →   45r
HH:MM:SS  show_runner  sardinia  run_checks      1823p →  342r
HH:MM:SS  show_runner  sardinia  run_rulings      534p →  156r
```

The "step" column is captured automatically in `call_llm()` via
`inspect.currentframe().f_back.f_code.co_name` — no explicit `task=` parameter needed.

**What changes:**

`instrumentation.py`:
- Replace `_PromptLogger._write(server, type, text)` + `_format_messages()` + `_server_for()` + `server_map`
  with a single `log(agent, server, step, prompt_len, response_len)` method that writes one line
- Remove `verbose_path` from `setup_instrumentation()` — return only `prompts_path` (single `Path`)

`llm.py`:
- Remove any `task=` parameter (not needed — caller is captured automatically)
- Add `import inspect` at top
- Compute `server` from `cfg["model_alias"].split("/")[0]`
- Compute `step = inspect.currentframe().f_back.f_code.co_name`
- Replace the two `_prompt_logger._write()` calls with one
  `_prompt_logger.log(agent_name, server, step, len(system_prompt) + len(user_message), len(content))`

`orchestrator.py`:
- Fix `verbose_path, prompts_path = setup_instrumentation(timestamp)` → `prompts_path = setup_instrumentation(timestamp)`

**Test changes:** `tests/test_instrumentation.py` and `tests/test_llm.py` have a partial start
from the previous iteration that used `task=` parameter — **that approach is superseded**.
Revise those tests to match the `inspect`-based design:
- `test_instrumentation.py`: keep the new `log()` method tests; keep the single-path `setup_instrumentation` tests
- `test_llm.py`: remove all `task=` additions; add a test that the log line contains the
  calling function's name (write a helper that calls `call_llm` from a known function name)

---

### [ ] 4.18 — Step 0: beat initialization + Narrator opener on first turn of each beat

**Do 4.17 and 4.19 first** — this task uses the renamed functions.

On the first turn of a new beat Step 0 does two things: injects beat-specific context
into the NPC wave (Step 3), and calls the Narrator to produce a player-facing opener.
Subsequent turns within the same beat skip beat initialization entirely.

**Beat transition detection** — in `run_turn_loop()`:
- Track `_last_beat: str = ""` before the `while True:` loop
- After loading `scene_state`, compare `current_beat != _last_beat`
- If transition: run beat initialization, then set `_last_beat = current_beat`

**Beat initialization (turn 1 of beat only):**
1. Look up the current beat dict from `scene["beats"]` by `id == current_beat`
2. Append `show_runner_notes` and `narrator_notes` from the beat to the
   `sr_ctx` and `narrator_ctx` strings passed into `run_npc_wave()` —
   prefix them with a clear header so the agents treat them as authoritative context:
   ```
   ## Beat Director Notes:\n{beat["show_runner_notes"]}
   ```
3. Call `run_beat_opener(beat, last_log_entry)` — see below
4. If `verbose` flag is set: print `\n=== {beat["title"]} ===` to terminal
5. Log the beat transition: `log.info(f"Beat transition: {current_beat}")`

**`run_beat_opener(beat, last_log_entry)` — new function in `runner.py`:**
- Agent: Narrator
- Input: beat notes (`show_runner_notes`, `narrator_notes`) + last entry from
  `state/session_log.md` (pass empty string if file doesn't exist yet)
- Output: 2–3 sentences of player-facing prose printed directly to terminal
- No return value needed; printed output is the product

**`verbose` flag** — add to `run_turn_loop(scene, verbose=False)` signature.
Pass it through from `main.py`. Wire a `--verbose` / `-v` CLI flag in `main.py`.

**Tests:**
- Beat notes injected into sr_ctx on turn 1 (mock scene with beat that has notes)
- Beat notes NOT injected on turn 2 of same beat
- `run_beat_opener` called on turn 1, not called on turn 2
- `run_beat_opener` receives empty string when session_log.md does not exist
- `verbose=True` → beat title printed; `verbose=False` → not printed
- `_last_beat` updates after transition

---

### [~] 4.8 — End-to-End Scene Playthrough

No tests for this task — this is exploratory play. Run `src/showrunner/main.py` and
play through `state/scene_0.yaml` (Bargos mansion) from entry to exit condition.

Checklist before calling Phase 4 done:
- [ ] Scene entry read-aloud is delivered by the Narrator
- [ ] Bargos audience beat runs; Negotiation check can be triggered
- [ ] Gamorrean warning beat triggers; Vigilance check fires
- [ ] Gamorrean Rumble combat resolves with dice (auto or manual input)
- [ ] Wounds are tracked correctly; minions die at wound threshold multiples
- [ ] Mission brief beat runs after combat
- [ ] Scene exits cleanly; scene_state.yaml updated

Issues found during play are bugs — fix them. If something requires an architectural
decision, stop and raise it with Tom.

---

## Completed: Phase 4 Implementation

The following tasks are complete as of 2026-05-13. See git log for details.

- **4.9** — Sequential pipeline; `initialize_scene_state()`; `last_actions` tracking
- **4.10** — Display agent outputs to player; move state writes from Scribe to orchestrator
- **4.12** — Fix Rich console leak in verbose output
- **4.13** — Three-phase turn loop (NPC wave / PC wave / resolution)
- **4.14** — Five-step resolution pipeline (summaries → checks → dice+rulings → narrative → last-action)
- **4.15** — Remove CrewAI; replace with direct LiteLLM calls via `llm.py` and `runner.py`

---

## Phase 5 — Genesys Rules Parser

Do not begin Phase 5 until Phase 4 has been played through successfully.

This phase delivers the data that `rules_lookup()` queries. It unblocks Phase 7.

- [ ] Write a PDF extraction script: `tools/parse_rulebook.py`
  - Input: `docs/references/Genesys_Core_Rulebook.pdf`
  - Output: section files in `swskin/rules/` (dice.md, combat.md, skills.md, talents.md)
  - Use `pymupdf` (already installed)
- [ ] Write `swskin/rules/index.md` — section list with page references
- [ ] Implement `rules_lookup(keyword: str) -> str` in `src/showrunner/tools/rules_lookup.py`
  - Keyword search against indexed sections; returns most relevant section text
- [ ] Wire `rules_lookup()` into the Referee agent
- [ ] Smoke test: Referee can retrieve the correct rule for "critical injury", "soak", "Brawl"

---

## Phase 6 — OggDude Data Ingestion

Do not begin Phase 6 until Phase 5 is complete.

This phase replaces inline NPC stats with a proper data source for Phase 7.

- [ ] Write `tools/xml_to_md.py` — convert OggDude XML exports to structured Markdown
- [ ] Output to `swskin/data/`: `weapons.md`, `skills.md`, `talents.md`, `careers.md`
- [ ] Smoke test: Referee can look up Gamorrean vibro-ax damage, crit, range, special from `weapons.md`
