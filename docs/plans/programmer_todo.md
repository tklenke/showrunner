# Programmer TODO

Implementation tasks for the showrunner engine.
Follow TDD: write the failing test first, then write only enough code to make it pass.

Reference documents:
- `docs/plans/architecture.md` — system design
- `docs/plans/character_schema.md` — character file schema and `render_actor_prompt` spec
- `docs/plans/architect_todo.md` — phased plan with open decisions

---

## Current Priority: Phase 4 — MVP Scene

### [x] 4.8c — Fix LiteLLM Prompt/Response Logging

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

### [x] 4.8d — Pass NPC Character Data to Actors Agent

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

### [x] 4.8e — Fix write_state Tool for 3B Model Reliability + Deep Merge

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

### [ ] 4.9 — Sequential Crew Refactor

**Goal:** replace the fragile hierarchical crew with a sequential pipeline where all five
agents execute in a guaranteed order every turn, each receiving proper per-turn context
in their task (not baked into backstory).

See `docs/plans/game_loop.md` for the current architecture and known weaknesses this fixes.

---

#### [x] 4.9a — Scene Initialization

Currently `scene_state.yaml` must be pre-populated manually. Initialize it
programmatically from the scene YAML at session start — no LLM involved.

Add `initialize_scene_state(scene: dict) -> None` to `src/showrunner/tools/state_writer.py`:
- Sets `current_beat` to `scene["beats"][0]["id"]`
- Sets `scene_id` from the scene
- Initializes `npc_knowledge: {}`, `flags: {}`, `last_actions: {}`
- Writes to `state/scene_state.yaml`
- Only runs if scene_state does not already exist OR if `scene_id` has changed
  (so a mid-session restart doesn't wipe state)

Call it from `run_turn_loop()` in `orchestrator.py` before the loop starts.

Tests:
- New scene → state file created with correct first beat and empty collections
- Same scene already initialized → existing state is preserved (no overwrite)
- Different scene_id → state is re-initialized

---

#### [x] 4.9b — Sequential Crew with Explicit Tasks

Rewrite `build_crew()` in `src/showrunner/crew.py`:

**Process:** `Process.sequential` (remove `manager_agent`, remove `Process.hierarchical`)

**Five tasks in order**, each with a focused description carrying dynamic context:

| # | Agent | Task description carries | Expected output |
|---|---|---|---|
| 1 | Show Runner | scene state, beat, last_actions, party stats | Beat plan: what to narrate, which NPCs act, any check needed |
| 2 | Narrator | Show Runner output (via `context=[task1]`) | Read-aloud narration for the player |
| 3 | Actors | Show Runner output + NPC data | NPC dialogue and actions for this beat |
| 4 | Referee | Show Runner + Narrator + Actors output | Check result, or "no check required" |
| 5 | Scribe | All prior outputs | Writes state files; records last_actions per actor |

Wire task context chaining: `Task(context=[prior_task, ...])` so each agent sees
relevant prior outputs without the Show Runner having to pass them manually.

`build_crew()` signature stays the same from the orchestrator's perspective —
it still receives the context strings, they just go into Task descriptions now
instead of agent backstories.

Tests:
- `build_crew()` returns a `Crew` with `Process.sequential`
- Crew has exactly 5 tasks in the correct agent order
- Task 5 (Scribe) has context referencing all 4 prior tasks

---

#### [x] 4.9c — Move Dynamic Context from Backstories to Tasks

Currently all per-turn data (scene state, beat info, NPC list) is injected into
agent backstories. Backstories should be static role descriptions only.

For each agent (`create_narrator`, `create_actors`, `create_referee`, `create_scribe`,
`create_show_runner`):
- Remove the `context` parameter and the backstory-append logic
- Backstory reverts to the static text from `config/agents.yaml` only

The dynamic context now lives exclusively in task descriptions (wired in 4.9b).
The `*_context` params move from `build_crew()` into the Task description strings
built inside `build_crew()`.

Tests: update existing tests that pass context strings to agent constructors.

---

#### [x] 4.9d — last_actions Tracking

Add `last_actions` to the scene state schema: a dict of `{actor_name: action_summary}`.

The Scribe's task description instructs it to call `write_state` with `last_actions`
containing one entry per actor who acted this beat (player character + any active NPCs).

In `orchestrator.py`:
- Remove the `last_action: str` variable
- After `kickoff()`, read `last_actions` from `load_scene_state()`
- Pass `last_actions` dict into the Show Runner task description next turn

The player's action is still collected via `prompt_player_action()`, but it is written
into `last_actions` by the orchestrator directly (not by the Scribe) under the PC's name
before the next `crew.kickoff()`.

Tests:
- `initialize_scene_state` produces `last_actions: {}` 
- After the Scribe writes, `last_actions` contains expected actor entries

---

### [ ] 4.10a — Display Agent Outputs to Player

Currently `crew.kickoff()` returns only the last task's output (State Keeper), which is
printed verbatim. The Narrator's prose, NPC dialogue, and Referee results are buried in
`crew.tasks[i].output.raw` and never shown to the player.

Fix in `orchestrator.py`:
- After `crew.kickoff()`, iterate `crew.tasks`
- Print outputs for Narrator, NPC Voice Actor (all), and Rules Engine tasks in order
- Skip Show Runner (internal planning) and State Keeper (bookkeeping)
- Label each section so the player can orient (e.g. `--- Narrator ---`, `--- Bargos ---`)
- The existing `print(f"\n{result_str}")` call should be removed

Tests:
- Add an integration test (or at minimum document the expected output format)

---

### [ ] 4.10b — Move State Writing from Scribe to Orchestrator

The Scribe (Alien 3B) cannot reliably call tools in a ReAct loop. It outputs tool call
syntax as text in its Final Answer (`Action: write_state { ... }`) instead of invoking
the tool. The root cause is that the 3B model does not understand the ReAct format well
enough to use tools.

**Design decision (confirmed with Tom):** Remove tool dependency from the Scribe. The
orchestrator handles all state writes deterministically after `kickoff()`.

Changes:

**`scribe.py`:**
- Remove `tools=[read_state, write_state, consult_show_runner]` — replace with `tools=[]`
- Keep `render_scribe_context()` as context input (the Scribe still needs to know current
  state to write a meaningful session log entry)
- Scribe task `expected_output` changes to: a one-sentence session log entry only
  (no tool calls needed)

**`orchestrator.py`** — after `crew.kickoff()`:
1. **last_actions**: collect NPC outputs from NPC Voice Actor task outputs
   (`task.output.raw` for each task where `task.agent.role == "NPC Voice Actor"`)
   and combine with the player action already captured via `prompt_player_action()`.
   Write via `update_scene_state({"last_actions": {...}})`.
2. **session_log.md**: take the Scribe task's `output.raw` (the prose summary sentence)
   and append it to `state/session_log.md` directly in the orchestrator — no tool call.
3. **party_stats.yaml**: wounds/strain — not implemented yet; leave a TODO comment.
   Will be wired when combat is added.

**NPC name mapping**: To build the `last_actions` dict, the orchestrator needs the NPC
id for each NPC task. Pass `scene_chars` (already a `dict[str, str]`) to the crew or
track task→npc_id mapping. Simplest approach: the NPC task description starts with the
rendered prompt which begins with `# {npc_name}` — or better, tag the task with the NPC
id in `build_crew()` by storing it as a `task.name` (CrewAI Task accepts a `name` param).

Tests:
- `test_scribe_has_no_tools` — verify `create_scribe()` has no tools
- `test_orchestrator_writes_last_actions_from_npc_outputs` — mock task outputs, verify
  `update_scene_state` is called with correct last_actions dict
- `test_session_log_appended_by_orchestrator` — verify session_log.md gets a new line

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
