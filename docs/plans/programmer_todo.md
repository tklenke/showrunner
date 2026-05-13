# Programmer TODO

Implementation tasks for the showrunner engine.
Follow TDD: write the failing test first, then write only enough code to make it pass.

Reference documents:
- `docs/plans/terminology.md` — **canonical terms; read before touching any character or turn-loop code**
- `docs/plans/game_loop.md` — **source of truth for the turn loop; if code diverges, the code is wrong**
- `docs/plans/architecture.md` — system design
- `docs/plans/character_schema.md` — character file schema and `render_actor_prompt` spec
- `docs/plans/architect_todo.md` — phased plan with open decisions

---

## Current Priority: Phase 4 — End-to-End Scene Playthrough

Tasks are listed in dependency order. Complete each before starting the next.

---

### [x] 4.16 — Terminology: rename `player: "ai"` → `"companion"` across Python code

Docs and YAML files are already updated. This task propagates the change into Python.

**`player` field value:** `"ai"` → `"companion"` in all comparisons and string literals.

Files to update:
- `src/showrunner/runner.py` — `player == "ai"` guard in `run_pc_wave()`
- `src/showrunner/orchestrator.py` — any `player == "ai"` filtering
- `src/showrunner/agents/actors.py` — any `"ai"` string references
- `tests/test_runner.py`, `tests/test_actors.py`, `tests/test_orchestrator.py` — fixture data and assertions

**Function rename:** `run_pc_wave` → `run_companion_wave` in `runner.py` and all call sites
(`orchestrator.py`, `tests/test_runner.py`, `tests/test_orchestrator.py`).

**Terms to replace in comments/docstrings:** "AI PC", "ai party member", "AI party member" → "Companion".

No logic changes — pure rename/string substitution. Run full test suite after.

---

### [x] 4.17 — Rename runner.py functions: drop `_phase` suffix

The `_phase` suffix on runner functions conflicts with the "step" vocabulary used in
`game_loop.md`. Rename for consistency. **Do this before 4.18** — the instrumentation
log will show calling function names, so they should be right first.

| Current name | New name |
|---|---|
| `run_summary_phase` | `run_summaries` |
| `run_check_phase` | `run_checks` |
| `run_ruling_phase` | `run_rulings` |
| `run_narrative_phase` | `run_narrative` |
| `run_last_action_phase` | `run_last_actions` |

`run_npc_wave` is already clean — keep it. `run_pc_wave` is renamed in 4.16.
`run_scribe_phase` is deleted in 4.19 — do not rename it here.

Update all import and call sites: `orchestrator.py`, `tests/test_runner.py`,
`tests/test_orchestrator.py`. No logic changes — pure rename.

Tests: update test function names that reference the old names; verify full suite passes.

---

### [x] 4.18 — Concise per-call instrumentation log

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

### [x] 4.19 — Remove Scribe; orchestrator appends Step 7 output to session_log.md

Session log is now written by the orchestrator directly — no LLM call needed.

- Delete `run_scribe()` from `runner.py`
- Remove `run_scribe()` call from `orchestrator.py`
- After `run_narrative()` returns, orchestrator appends its output to `state/session_log.md`
- Remove `scribe` agent from any test fixtures that reference it
- Update `tests/test_runner.py` and `tests/test_orchestrator.py` to remove Scribe tests

Run full test suite after.

---

### [x] 4.20 — Step 0: beat initialization + Narrator opener on first turn of each beat

**Do 4.16 and 4.17 first** — this task uses the renamed functions.

On the first turn of a new beat Step 0 does two things: injects beat-specific context
into the SR and Narrator context strings, and calls the Narrator to produce a player-facing
opener. Subsequent turns within the same beat skip beat initialization entirely.

**Beat transition detection** — in `run_turn_loop()`:
- Track `_last_beat: str = ""` and `_turn_num: int = 1` before the `while True:` loop
- After loading `scene_state`, compare `current_beat != _last_beat`
- If transition: run beat initialization, then set `_last_beat = current_beat` and `_turn_num = 1`
- At end of each turn: `_turn_num += 1`

**Beat initialization (turn 1 of beat only):**
1. Look up the current beat dict from `scene["beats"]` by `id == current_beat`
2. Load `character_plans` from `beat["character_plans"]` and write to
   `scene_state.yaml` → `character_plans` (initial plans for all characters in this beat)
3. Append `show_runner_notes` and `narrator_notes` from the beat to the
   `sr_ctx` and `narrator_ctx` strings — prefixed with `## Beat Director Notes:`
4. Call `run_beat_opener(beat, last_log_entry)` — see below
5. If `verbose` flag is set: print `\n=== {beat["title"]} ===` to terminal
6. Log the beat transition: `log.info(f"Beat transition: {current_beat}")`

**`run_beat_opener(beat, last_log_entry)` — new function in `runner.py`:**
- Agent: Narrator
- Input: beat notes (`show_runner_notes`, `narrator_notes`) + last entry from
  `state/session_log.md` (pass empty string if file doesn't exist yet)
- Output: 2–3 sentences of player-facing prose printed directly to terminal
- No return value needed; printed output is the product

**`verbose` flag** — add to `run_turn_loop(scene, verbose=False)` signature.
Pass it through from `main.py`. Wire a `--verbose` / `-v` CLI flag in `main.py`.

**Beat YAML `character_plans` field** — add `character_plans` dict to each beat in
`state/scene_0.yaml`. Key is character id; value is the initial plan string. The
orchestrator reads this on beat transition (step 2 above).

**Tests:**
- Beat notes injected into sr_ctx on turn 1 (mock scene with beat that has notes)
- Beat notes NOT injected on turn 2 of same beat
- `run_beat_opener` called on turn 1, not called on turn 2
- `run_beat_opener` receives empty string when session_log.md does not exist
- `verbose=True` → beat title printed; `verbose=False` → not printed
- `_last_beat` updates after transition; `_turn_num` resets to 1 then increments

---

### [x] 4.21 — Log file naming: implement scene-beat-turn sort format

All turn log files must use the zero-padded naming scheme from `game_loop.md`:
`{scene:02d}_{beat:02d}_{beat_id}_{turn:04d}_{type}.txt`

**What changes:**
- `orchestrator.py` — replace `logs/turn_{ts}_{beat}_` prefix with `logs/{scene:02d}_{beat:02d}_{beat_id}_{turn:04d}_`
- Orchestrator must track `scene_num` (integer, from loaded scene), `beat_num` (index of
  current beat in `scene["beats"]`), `beat_id` (string), and `_turn_num` (int, per beat)
- `_turn_num` resets to 1 on each beat transition (see 4.20)
- Update all log path construction in `runner.py` call sites and orchestrator
- Update any tests that assert log file paths or names

**Tests:**
- Log file for turn 3 of beat 2 (`gamorrean_rumble`) in scene 0 produces
  `logs/00_02_gamorrean_rumble_0003_summaries.txt`
- `_turn_num` increments each turn; resets to 1 on beat transition

---

### [x] 4.22 — Step 3: NPC wave with inline Narrator summaries (2N call pattern)

Per `game_loop.md` Step 3: each NPC call is immediately followed by a Narrator call that
produces a compact 1–2 sentence summary. The next NPC receives the summary, not the full
output. Full outputs are printed to terminal; summaries are pipeline-internal and written
to the summaries log file.

**`run_npc_wave()` signature change:**
```python
run_npc_wave(npcs, beat_ctx, user_action, companion_outputs, summaries_log_path) -> dict[str, str]
```
Returns `{npc_id: full_output}` (full outputs for Steps 5–7).

**Call sequence per NPC:**
1. `call_llm(actors, ...)` — NPC acts; receives plan + beat context + user action +
   companion outputs + compact summaries of all prior NPCs
2. Print full NPC output to terminal
3. `call_llm(narrator, ...)` — produces 1–2 sentence summary of NPC output
4. Append summary to `summaries_log_path`
5. Pass summary (not full output) to next NPC

Total: 2N `call_llm()` calls for N NPCs.

**Tests:**
- For 2 NPCs: 4 `call_llm()` calls total (2 NPC + 2 Narrator)
- Second NPC receives summary of first NPC, not full output
- Summaries appended to log file in NPC order
- Full outputs returned in result dict; summaries are not

---

### [x] 4.23 — Step 4: Party Action Summaries (User + Companions)

Per `game_loop.md` Step 4: after the NPC wave, the Narrator produces a 1–2 sentence
summary for each party member that acted (User + any Companions). Summaries are appended
to the same `_summaries.txt` log file that Step 3 wrote NPC summaries to.

**`run_summaries(party_actions, summaries_log_path)` — new function in `runner.py`:**
- `party_actions`: dict of `{character_id: action_text}` for User and Companions that acted
- One `call_llm(narrator, ...)` per entry
- Appends each summary to `summaries_log_path` (NPC summaries already present from Step 3)

**Tests:**
- One `call_llm()` per party member
- Summaries appended to existing log (not overwritten)
- Empty `party_actions` → no calls, file unchanged

---

### [x] 4.24 — Step 5: Check Identification — N calls, one per character

Per `game_loop.md` Step 5: the Show Runner identifies required checks one character at a
time. One `call_llm()` per character — focused on one actor at a time rather than the
full batch, keeping the task within 8B capability.

**`run_checks()` signature change:**
- Current (if batch): single call with all summaries
- New: one call per character that acted; each receives that character's summary + their stats

**Each call receives:**
- That character's 1–2 sentence summary (from summaries log)
- Their stat block (characteristic values + skill ranks, rendered by orchestrator from raw YAML)
- Show Runner system prompt (rules context for this scene)

**Output format per call** (written to checks log, one line per check identified):
```
{actor} | {skill} | {characteristic} {value} | {skill_rank} | {difficulty} | {notes}
```
Or `NO_CHECKS` if no check needed for that character.

**Tests:**
- For 3 characters: 3 `call_llm()` calls
- Each call receives only that character's summary and stats (not the full party batch)
- `NO_CHECKS` output produces no check lines in the log
- Check lines from all characters combined into single checks log file

---

### [x] 4.25 — Structured Output Chain: parse-repair loop in orchestrator

Per `game_loop.md` Ref C: the orchestrator never parses free-form LLM output cold.
It always leads with a programmatic best-guess (regex, keyword extraction), then hands
that to an LLM to confirm or correct if the first parse fails.

**`parse_structured(raw, schema, *, context) -> (result, recovered: bool)` — new function in `orchestrator.py`:**

Repair chain:
1. Orchestrator parses `raw` directly → success: return result
2. Orchestrator makes programmatic best-guess → `call_llm(narrator, raw + best-guess)` → re-parse → success: log recovery, return
3. Orchestrator makes new best-guess → `call_llm(show_runner, raw + best-guess)` → re-parse → success: log escalation, return
4. Prompt User (free-form) → Orchestrator best-guess → `call_llm(narrator, user_input + best-guess)` → re-parse → success: log, return (max 2 User attempts)
5. Zero fallback: use best-guess as-is, write loud warning to session log

Every recovery and escalation is appended to `state/session_log.md`.

**Tests:**
- Clean input → direct parse, no LLM calls
- Malformed input → Narrator called with best-guess; clean result returned
- Narrator also fails → SR called; result returned
- SR also fails → User prompted; Narrator interprets User input
- All fail twice → zero fallback applied, session log contains warning
- User skips → zero fallback immediately

---

### [x] 4.26 — Step 6: party_stats.yaml tracking after each ruling

Per `game_loop.md` Step 6: the orchestrator updates `party_stats.yaml` after parsing each
ruling. Each `call_llm()` for Step 6 receives current `party_stats` (not prior ruling text)
as context. Parsing uses the Structured Output Chain (see 4.25).

**What changes in `run_rulings()`:**
- After each `call_llm()` ruling, pass the raw output to the Structured Output Chain parser
- On successful parse: orchestrator writes updated `party_stats.yaml` before the next ruling call
- Each subsequent ruling receives the updated `party_stats` (not the prior ruling text)

**Tracked values** (what the orchestrator extracts from each ruling):
- Wounds applied/healed per character
- Strain applied/healed per character
- Characters at or past wound threshold (critical injury trigger)

**`party_stats.yaml` schema** (per character entry):
```yaml
characters:
  z4p0:
    wounds_current: 3
    wounds_threshold: 12
    strain_current: 2
    strain_threshold: 13
```

**Tests:**
- After ruling applies 2 wounds to Z-4P0: `party_stats.yaml` shows updated `wounds_current`
- Next ruling call receives the updated `party_stats` (not the text of the prior ruling)
- Parse failure → Structured Output Chain invoked (mock the chain for this test)
- Character at wound threshold → logged (critical injury handling is future work)

---

### [x] 4.27 — Step 9: plan update — SR sets overall plan then individual plans

**Do 4.20 first** — this step runs after last-action extraction in the same turn loop.

SR reviews the full turn and updates each character's plan for next turn.
Same code path for NPCs and Companions.

**`run_plan_update(characters, summaries, results, last_actions)` — new function in `runner.py`:**

```
1 call:  SR  →  summaries + results + last_actions  →  overall_plan (str)
N calls: SR  →  overall_plan + character id + current situation  →  individual plan (str)
```

- `characters` = dict of all NPCs and Companions active in the current beat
- Overall plan is logged to `logs/{scene:02d}_{beat:02d}_{beat_id}_{turn:04d}_sr_plan.txt`
  (debug artifact, not shared with characters)
- Individual plans written to `scene_state.yaml` → `character_plans` (keyed by character id)

**Orchestrator wiring:**
- Call `run_plan_update()` after `run_last_actions()` (Step 9 in game loop)
- Pass the same `characters` dict used for summaries

**Tests:**
- Overall plan call fires once with full context
- Individual plan call fires once per character (NPC and Companion, same path)
- `character_plans` in scene_state updated with returned plans
- SR plan logged to `logs/{scene:02d}_{beat:02d}_{beat_id}_{turn:04d}_sr_plan.txt`
- Empty characters dict → no individual plan calls, no file written

---

### [ ] 4.29 — Output labeling: character headers always; step labels in verbose mode

**Why:** The current output mixes GM-internal blobs, character responses, and narrative
with no visual separation. We can't tell which step produced bad output. This task adds
labeled section headers so every printed block has a clear origin.

**Character headers — always on (not verbose-gated):**

Replace the current `[name]` prefix style with a proper section header on its own line.

| Current | New |
|---|---|
| `[bargos_the_hutt] He stares...` | `\n=== bargos_the_hutt ===\nHe stares...` |
| `[kaelen_sunara] She nods...` | `\n=== kaelen_sunara ===\nShe nods...` |

Files: `runner.py` → `run_npc_wave` and `run_companion_wave` both call
`print(f"[{npc_id}] {full_output}")` / `print(f"[{pc_id}] {output}")`.
Change both to `print(f"\n=== {id} ===\n{output}")`.

**Step labels — verbose mode only:**

When `--verbose` / `-v` is passed, print a `=== Step Name ===` header before each
major output block. Add a `verbose: bool = False` parameter to the runner functions
that print, thread it through from the orchestrator.

| Block | Label | Currently printed by |
|---|---|---|
| Beat opener | `=== Beat Opener ===` | `run_beat_opener()` in `runner.py` |
| Resolution narrative | `=== Resolution Narrative ===` | `orchestrator.py` after `run_narrative()` |

`run_beat_opener(beat, last_log_entry, verbose=False)` — add `verbose` parameter;
prefix the output with `=== Beat Opener ===\n` when verbose.

The resolution narrative is already printed in the orchestrator's turn loop:
```python
if narrative:
    print(f"\n{narrative}")
```
Change to:
```python
if narrative:
    label = "\n=== Resolution Narrative ===" if verbose else ""
    print(f"{label}\n{narrative}")
```

**`--verbose` is already a real CLI flag** (`-v` / `--verbose` in `main.py`, passed to
`run_turn_loop`). It currently only controls beat-title printing in `_run_beat_initialization`.
That existing behavior stays; this task adds step labels on top of it.

**Tests:**
- `run_npc_wave` output contains `=== {npc_id} ===` (no brackets)
- `run_companion_wave` output contains `=== {pc_id} ===`
- `run_beat_opener` with `verbose=True` prints `=== Beat Opener ===`
- `run_beat_opener` with `verbose=False` does NOT print `=== Beat Opener ===`

---

### [ ] 4.30 — Directory restructure: skin/, config/prompts/, state/ cleanup

Implements the directory layout decided in `docs/plans/architect_todo.md`
(Design Decision: Prompt Architecture and Directory Restructure).
Do this before 4.31 and 4.32 — those tasks depend on the new paths.

**Step 1 — Create `skin/` and move content:**

```bash
mkdir -p skin/characters skin/scenes
git mv characters/* skin/characters/
git mv state/scene_0.yaml skin/scenes/scene_0.yaml
git mv state/scene_1.yaml skin/scenes/scene_1.yaml
```

**Step 2 — Create `config/prompts/` (empty for now; populated in 4.31):**

```bash
mkdir config/prompts
```

**Step 3 — Update all path references in Python code:**

Files that load characters or scenes must be updated to read from new paths.

| Old path | New path |
|---|---|
| `characters/{name}.yaml` | `skin/characters/{name}.yaml` |
| `state/scene_N.yaml` | `skin/scenes/scene_N.yaml` |

Files to update:
- `src/showrunner/tools/state_reader.py` — `load_character()` and `load_adventure_scene()`
- `src/showrunner/agents/actors.py` — any hardcoded character paths
- Any test fixtures that reference `characters/` or `state/scene_*.yaml`

**Step 4 — Update all `skin` references in docs:**

- `docs/plans/architecture.md`
- `docs/plans/character_schema.md`
- `docs/plans/programmer_todo.md` (Phase 5, 6 entries below)
- `README.md` if any references exist

**Step 5 — Create `skin/world.yaml` with placeholder text:**

```yaml
world:
  name: "Star Wars: Edge of the Empire"
  description:
    large: |
      [TODO: full world description for large-context models]
    medium: |
      [TODO: condensed world description for 8B models]
    small: |
      [TODO: minimal world description for 3B models]
```

Actual content is authored in 4.32. This task just creates the file and schema.

**Tests:**
- `load_adventure_scene(0)` successfully loads from `skin/scenes/scene_0.yaml`
- `load_character("bargos_the_hutt")` successfully loads from `skin/characters/`
- Full test suite passes after path updates

---

### [ ] 4.31 — Prompt files: extract task prompts from runner.py into config/prompts/

Each runner function that calls `call_llm()` has a task description baked as an
inline f-string. Move the static frame of each task description into a `.md` file
under `config/prompts/`. Python continues to interpolate dynamic values (actor names,
roll results, stat values) into the loaded template.

**Files to create** (one per step that has a static frame):

| File | Runner function |
|---|---|
| `config/prompts/task_run_checks.md` | `run_checks()` |
| `config/prompts/task_run_rulings.md` | `run_rulings()` |
| `config/prompts/task_run_narrative.md` | `run_narrative()` |
| `config/prompts/task_run_summaries.md` | `run_summaries()` |
| `config/prompts/task_run_last_actions.md` | `run_last_actions()` |
| `config/prompts/task_run_plan_update.md` | `run_plan_update()` |
| `config/prompts/task_run_beat_opener.md` | `run_beat_opener()` |

**Loading pattern** — add a helper to `llm.py`:

```python
def load_task_prompt(name: str) -> str:
    """Load a task prompt template from config/prompts/task_{name}.md."""
    path = Path("config/prompts") / f"task_{name}.md"
    return path.read_text()
```

Dynamic values are interpolated by the calling function after loading:
```python
template = load_task_prompt("run_checks")
msg = template.format(char_id=char_id, summary=summary, stats=stats)
```

Use `{placeholder}` syntax in the `.md` files for values Python fills in.
Use `{{literal_braces}}` for any braces that should appear verbatim.

**Agent prompt files** — also extract agent role definitions:

| File | Replaces in agents.yaml |
|---|---|
| `config/prompts/agent_show_runner.md` | `role` + `goal` + `backstory` for show_runner |
| `config/prompts/agent_narrator.md` | same for narrator |
| `config/prompts/agent_actors.md` | same for actors |

Add `prompt_file: prompts/agent_show_runner.md` to each agent entry in `agents.yaml`.
`build_system_prompt()` in `llm.py` reads this file instead of assembling from fields.

**Tests:**
- `load_task_prompt("run_checks")` returns a non-empty string
- Each runner function produces the same user message content before and after extraction
  (verify via existing tests — they check message content)

---

### [ ] 4.32 — Node chunk: world.yaml world context injected into every system prompt

Implements the node layer of the prompt architecture. Every agent call gets a
world-context prefix sized appropriately for the model.

**`skin/world.yaml`** — fill in real content (created as placeholder in 4.30):

Write three versions of the Star Wars: Edge of the Empire world context:
- `large`: rich setting description, faction overview, tone, genre — 400–600 words
- `medium`: condensed — key factions, tone, genre — 100–150 words
- `small`: minimal — 2–3 tight sentences that orient any model

**Tier mapping in `config/agents.yaml`** — add `context_tier` to each agent:

```yaml
show_runner:
  context_tier: medium   # sardinia 8B
  ...
narrator:
  context_tier: medium
  ...
actors:
  context_tier: medium
  ...
```

Gemini-backed agents would use `large`. 3B agents use `small`.

**`build_system_prompt(agent_name)` in `llm.py`** — prepend world context:

```python
def build_system_prompt(agent_name: str) -> str:
    cfg = load_agent_configs()[agent_name]
    tier = cfg.get("context_tier", "medium")
    world = _load_world_description(tier)   # reads skin/world.yaml
    agent = _load_agent_prompt(agent_name)  # reads config/prompts/agent_*.md
    return f"{world}\n\n{agent}"
```

Add `_load_world_description(tier: str) -> str` helper — reads `skin/world.yaml`,
returns `world.description[tier]`.

**Tests:**
- `build_system_prompt("narrator")` return value contains text from `world.yaml`
  `medium` section
- Changing `context_tier` to `large` in config changes which section is prepended
- Missing tier falls back to `medium` (don't crash)

---

### [~] 4.33 — End-to-End Scene Playthrough

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
  - Output: section files in `skin/rules/` (dice.md, combat.md, skills.md, talents.md)
  - Use `pymupdf` (already installed)
- [ ] Write `skin/rules/index.md` — section list with page references
- [ ] Implement `rules_lookup(keyword: str) -> str` in `src/showrunner/tools/rules_lookup.py`
  - Keyword search against indexed sections; returns most relevant section text
- [ ] Wire `rules_lookup()` into the Show Runner agent
- [ ] Smoke test: Show Runner can retrieve the correct rule for "critical injury", "soak", "Brawl"

---

## Phase 6 — OggDude Data Ingestion

Do not begin Phase 6 until Phase 5 is complete.

This phase replaces inline NPC stats with a proper data source for Phase 7.

- [ ] Write `tools/xml_to_md.py` — convert OggDude XML exports to structured Markdown
- [ ] Output to `skin/data/`: `weapons.md`, `skills.md`, `talents.md`, `careers.md`
- [ ] Smoke test: Show Runner can look up Gamorrean vibro-ax damage, crit, range, special from `weapons.md`
