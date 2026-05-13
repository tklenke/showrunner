# Programmer TODO

Implementation tasks for the showrunner engine.
Follow TDD: write the failing test first, then write only enough code to make it pass.

Reference documents:
- `docs/plans/architecture.md` — system design
- `docs/plans/character_schema.md` — character file schema and `render_actor_prompt` spec
- `docs/plans/architect_todo.md` — phased plan with open decisions

---

## Current Priority: Phase 4 — MVP Scene

### [ ] 4.8c — Fix LiteLLM Prompt/Response Logging

The `prompts_TIMESTAMP.log` file is never created during real sessions. The `_PromptLogger`
CustomLogger is registered via `litellm.callbacks` in `setup_instrumentation()`, but the
callbacks (`log_pre_api_call`, `log_success_event`) are never invoked in practice.

Diagnose why:
- Confirm whether CrewAI intercepts LiteLLM calls before callbacks fire
- Check whether `litellm.callbacks` is the correct registration API for this LiteLLM version
  (some versions use `litellm.success_callback`, `litellm.input_callback` lists instead)
- Check whether the callback is overwritten after `setup_instrumentation()` returns

Fix the integration so `prompts_TIMESTAMP.log` is produced after every session.

Add an integration test that wires the full chain: mock a LiteLLM call → verify the
prompts file is written. Do not just test `_write()` directly — test that the callback
actually fires when LiteLLM processes a call.

---

### [ ] 4.8d — Pass NPC Character Data to Actors Agent

`create_actors()` is called with no arguments. The Actors agent's backstory is the
generic config text — no NPC data. `load_scene_characters()` and `render_actor_prompt()`
exist in `actors.py` but are never called in the turn loop. The Show Runner cannot
effectively delegate to Actors because the agent has no character context to act from.

Fix:
- Add `context: str = ""` parameter to `create_actors()`, mirroring `create_narrator()`
- In `crew.py`, call `load_scene_characters(scene, scene_state)` to render NPC prompts,
  then pass the result to `create_actors(context=...)`
- The context string should contain each NPC's rendered prompt (from `render_actor_prompt()`)
  so the Actors agent knows who is present and how to voice them

The `load_scene_characters()` and `render_actor_prompt()` implementations are already
correct — this is purely a wiring gap in `crew.py` / `create_actors()`.

Add a test: build a minimal scene + scene_state, call `load_scene_characters()`, assert
the rendered context contains NPC identity and persona data.

---

### [ ] 4.8e — Fix write_state Tool for 3B Model Reliability + Deep Merge

Two bugs in `write_state` (`src/showrunner/tools/agent_tools.py`):

**Bug 1 — No schema unwrapping.** `write_state` uses the `@tool` decorator with no
input validation. The Scribe runs on Alien (Llama 3.2 3B), which emits JSON Schema
objects instead of actual arg values. Every other tool (`read_state`,
`consult_show_runner`) uses `BaseTool` with `_unwrap_schema_args` for exactly this
reason. Convert `write_state` to a `BaseTool` subclass with the same protection.

**Bug 2 — Shallow merge loses nested data.** `update_party_stats` and
`update_scene_state` call `current.update(updates)`, which overwrites entire nested
dicts. If the Scribe passes `{"characters": {"Z-4P0": {"wounds": 3}}}`, the full
`characters` dict is replaced, dropping all other characters. Change to a deep merge
so only the specified keys within nested dicts are updated.

Add tests:
- `test_write_state_unwraps_schema` — verify the tool handles a JSON Schema wrapper
  the same way `read_state` and `consult_show_runner` do
- `test_update_party_stats_deep_merge` — write stats for two characters; update one;
  assert the other is unchanged
- `test_update_scene_state_deep_merge` — same pattern for scene_state fields

---

### [~] 4.8 — End-to-End Scene Playthrough

No tests for this task — this is exploratory play. Run `src/showrunner/main.py` and
play through `state/scene_0.yaml` (Bargos mansion) from entry to exit condition.

Checklist before calling Phase 4 done:
- [ ] Scene entry read-aloud is delivered by World Runner
- [ ] Bargos audience beat runs; Negotiation check can be triggered
- [ ] Gamorrean warning beat triggers; Vigilance check fires
- [ ] Gamorrean Rumble combat resolves with dice (auto or manual input)
- [ ] Wounds are tracked correctly; minions die at wound threshold multiples
- [ ] Mission brief beat runs after combat
- [ ] Scene exits cleanly; scene_state.yaml updated

Issues found during play are bugs — fix them. If something requires an architectural
decision, stop and raise it with Tom.

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
