# Programmer TODO

Implementation tasks for the showrunner engine.
Follow TDD: write the failing test first, then write only enough code to make it pass.

Reference documents:
- `docs/plans/architecture.md` — system design
- `docs/plans/character_schema.md` — character file schema and `render_actor_prompt` spec
- `docs/plans/architect_todo.md` — phased plan with open decisions

---

## Current Priority: Phase 4 — Remove CrewAI

### [~] 4.15 — Replace CrewAI with Direct LiteLLM Calls

**Rationale:** CrewAI's value is the ReAct tool loop. We have stripped tools from every
agent. What remains is an expensive abstraction that has caused: ReAct loop crashes on small
models, LiteLLM callback interception, Pydantic serialization warnings, Rich console leaks,
empty crew validation errors, and batched output requiring `sys.__stdout__` hacks. The
replacement is a thin `call_llm()` function over bare litellm + plain Python phase functions.

**What we keep:** `config/agents.yaml`, `config/litellm.yaml`, all `render_*_context()`
functions, all orchestrator logic, all state tools (`dice_roller`, `state_reader`,
`state_writer`), all YAML/scene parsing.

**What we remove:** `crewai`, Pydantic (no longer a direct dependency), `crew.py`,
`agent_tools.py` (all tools are dead code — stripped from agents months ago).

**What changes:** `config.py`, `instrumentation.py`, `agents/*.py`, `orchestrator.py`;
new files `llm.py` and `runner.py`.

---

#### [x] 4.15a — Update `config.py`: remove `crewai.LLM`; expose raw litellm call params

`load_agent_configs()` currently returns `{"llm": crewai.LLM(...), ...}` per agent.
Replace the `"llm"` key with `"litellm_params": {"model": str, "api_base": str | None,
"api_key": str}` — plain strings that `call_llm()` can pass directly to `litellm.completion`.

Add `apply_litellm_settings()` that reads `litellm_settings` from `litellm.yaml` and sets
`litellm.drop_params`, `litellm.request_timeout`, `litellm.num_retries` globally. Called
once at session start from `run_turn_loop()`.

Keep the Gemini 2.5 thinking-mode guard — move it from `_build_llm_registry()` into
`call_llm()` as an `extra_body` kwarg: `if "gemini-2.5" in model: kwargs["thinking"] = {"type": "disabled"}`.

Tests:
- `load_agent_configs()` returns `"litellm_params"` dict for each agent (not a crewai.LLM)
- `litellm_params` contains `model`, and optionally `api_base` / `api_key`
- `apply_litellm_settings()` sets litellm globals from config values

---

#### [x] 4.15b — New `src/showrunner/llm.py`: `call_llm()` + prompt logging

```python
def call_llm(agent_name: str, system_prompt: str, user_message: str) -> str:
    ...
```

- Loads litellm_params for the agent from `load_agent_configs()`
- Assembles `messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}]`
- Calls `litellm.completion(model=..., api_base=..., api_key=..., messages=messages)`
- Returns `response.choices[0].message.content`
- If a module-level prompt logger is set (via `setup_llm_logging()`), logs prompt + response

```python
def build_system_prompt(agent_name: str) -> str:
    cfg = load_agent_configs()[agent_name]
    return f"You are {cfg['role']}.\n\n{cfg['goal']}\n\n{cfg['backstory']}"
```

```python
def setup_llm_logging(log_path: Path) -> None:
    """Set module-level prompt logger. Called once from setup_instrumentation()."""
    ...
```

The logger writes the same format as the current `_PromptLogger._write()` — timestamp, server
label, separator, prompt block, response block.

Tests (mock `litellm.completion`):
- Messages list has system + user roles with correct content
- Return value is `response.choices[0].message.content`
- Prompt and response are written to log file after a call
- Gemini 2.5 call includes `thinking: {type: disabled}` kwarg

---

#### [x] 4.15c — New `src/showrunner/runner.py`, part 1: NPC/PC waves

```python
def run_npc_wave(
    sr_context: str,
    narrator_context: str,
    npc_contexts: dict[str, str],
) -> dict[str, str]:
```

- Calls `call_llm("show_runner", ...)` → `beat_plan`
- Calls `call_llm("narrator", ..., user_message=f"{narrator_context}\n\n## Beat Plan:\n{beat_plan}")` → prints immediately
- For each NPC in order: builds user message from `npc_context + beat_plan + all prior NPC outputs`; calls `call_llm("actors", ...)`; prints `[npc_id]` + output immediately
- Returns `{"_narrator": narration, npc_id: output, ...}` (narrator keyed as `"_narrator"`)

```python
def run_pc_wave(
    npc_wave_text: str,
    ai_pc_contexts: dict[str, str],
    player_action: str,
) -> dict[str, str]:
```

- Returns `{}` for empty `ai_pc_contexts`
- For each AI PC: user message contains `pc_context + npc_wave_text + player_action`; prints `[pc_id]` + output immediately
- Returns `{pc_id: output, ...}`

Tests (mock `call_llm`):
- `run_npc_wave` calls `call_llm` once for show_runner, once for narrator, once per NPC
- Second NPC's user message contains first NPC's output (context chaining)
- Each NPC output is printed (mock `print` or capture stdout)
- `run_pc_wave({}, "...")` returns `{}`
- PC user message contains `npc_wave_text` and `player_action`

---

#### [x] 4.15d — New `src/showrunner/runner.py`, part 2: five-step pipeline

```python
def run_summary_phase(action_map: dict[str, str]) -> dict[str, str]:
def run_check_phase(summaries_text: str, stats_text: str) -> str:
def run_ruling_phase(check_specs: list[dict]) -> dict[str, str]:   # {} for empty
def run_narrative_phase(summaries: str, checks: str, results: str) -> str:
def run_last_action_phase(actor_summaries: dict[str, str]) -> dict[str, str]:  # {} for empty
def run_scribe_phase(scribe_context: str, full_turn_summary: str) -> str:
```

Agent assignments (same as current crew builders):
- `run_summary_phase` → `"actors"` (one call per actor)
- `run_check_phase` → `"show_runner"` (single call)
- `run_ruling_phase` → `"show_runner"` (one call per check; user message for check N includes all prior ruling outputs as context)
- `run_narrative_phase` → `"show_runner"` (single call)
- `run_last_action_phase` → `"narrator"` (one call per actor; each user message contains only that actor's summary)
- `run_scribe_phase` → `"scribe"` (single call)

System prompts: all built by `build_system_prompt(agent_name)` from `llm.py`.

Tests (mock `call_llm`):
- `run_summary_phase` calls `call_llm` once per actor; each call's user message contains that actor's action text
- `run_check_phase` calls `call_llm` once with summaries + stats in user message
- `run_ruling_phase` with 2 specs calls `call_llm` twice; second call's user message contains first ruling
- `run_ruling_phase([])` returns `{}`
- `run_last_action_phase({"bargos": "...", "kae": "..."})` calls `call_llm` twice; bargos call does not contain kae's summary
- `run_last_action_phase({})` returns `{}`

---

#### [x] 4.15e — Update `agents/*.py`: remove `create_*()` functions

Remove from each module:
- `actors.py`: `create_actors()` and `from crewai import Agent`
- `narrator.py`: `create_narrator()` and `from crewai import Agent`; also remove `from showrunner.tools.agent_tools import consult_show_runner`
- `scribe.py`: `create_scribe()` and `from crewai import Agent`
- `show_runner.py`: `create_show_runner()` and `from crewai import Agent`
- `referee.py`: `create_referee()` and `from crewai import Agent`; keep `build_referee_backstory()` and `render_referee_context()` — the rules content is still used by 3c rulings

Update tests that verified agent object properties (`test_narrator.py`,
`test_scribe.py`, `test_show_runner.py`, `test_referee.py`) — replace assertions on
Agent objects with assertions on the render functions' output where meaningful;
delete tests that only verified `create_*()` boilerplate.

---

#### [ ] 4.15f — Delete `src/showrunner/tools/agent_tools.py` and `tests/test_agent_tools.py` *(deferred — requires file deletion)*

All tools (`read_state`, `write_state`, `roll_dice`, `consult_show_runner`) are dead code.
They were stripped from all agents. Their `BaseTool` + `_unwrap_schema_args` pattern is
only needed for the CrewAI ReAct loop, which no longer exists.

Delete both files. State I/O is handled directly by `state_reader.py` / `state_writer.py`.
Dice rolls are handled directly by `dice_roller.py`. There is no `consult_show_runner`
dispatch mechanism — the orchestrator calls the LLM directly via `call_llm()`.

Phase 5 `rules_lookup()` will be a plain Python function in `src/showrunner/tools/` with
no `BaseTool` wrapper needed.

---

#### [x] 4.15g — Update `orchestrator.py`: call runner functions directly

Replace all `build_*_crew()` + `crew.kickoff()` + output-extraction patterns with direct
`run_*()` calls. The runner functions return plain dicts/strings — no `.output.raw`, no
`_collect_wave_outputs`, no `_get_task_output`.

Remove helpers that are no longer needed: `_collect_wave_outputs()`, `_get_task_output()`.
Remove all `with verbose_to_file(verbose_path):` wrappers (no more CrewAI Rich console to
redirect).

Phase 1 (NPC wave):
```python
npc_wave = run_npc_wave(sr_ctx, narrator_ctx, npc_chars)
npc_outputs = {k: v for k, v in npc_wave.items() if k != "_narrator"}
```

Phase 2 (PC wave):
```python
ai_pc_outputs = run_pc_wave(npc_wave_text, ai_pc_chars, player_action)
```

Phase 3a–3e: direct `run_*` calls replacing the current crew+kickoff blocks.
The intermediate file writes (`_write_turn_file`) stay in the orchestrator unchanged.
Printing the 3d narrative: `run_narrative_phase()` returns a string; orchestrator prints it.

Update `tests/test_orchestrator.py` where it mocks crew builders — mock runner functions
instead.

---

#### [x] 4.15h — Update `instrumentation.py`: remove CrewAI hooks

Remove:
- `from crewai.events.event_bus import crewai_event_bus`
- `from crewai.events.types.llm_events import LLMCallCompletedEvent`
- `from crewai.events.event_listener import event_listener` (used in `verbose_to_file`)
- `verbose_to_file()` context manager entirely
- `_PromptLogger._on_completed()` event bus method

Keep `_PromptLogger` class (its `_write()` method is still used by `llm.py`'s logging).

`setup_instrumentation()` changes:
- Still creates `verbose_path` and `prompts_path`; still returns both
- Replaces `crewai_event_bus.on(...)` registration with `setup_llm_logging(prompts_path)` call
- Remove the logger return value (it's now internal to `llm.py`)
- Signature becomes: `setup_instrumentation(timestamp, ...) -> tuple[Path, Path]`

Update `tests/test_instrumentation.py`: remove event-bus subscription tests; add test that
`setup_instrumentation()` calls `setup_llm_logging()` with the correct path.

---

#### [~] 4.15i — Remove `crew.py`; remove crewai from dependencies; final cleanup

1. Delete `src/showrunner/crew.py`
2. Delete `tests/test_crew.py` (replaced by `tests/test_runner.py` written in 4.15c/d)
3. In `pyproject.toml`: remove `crewai` from dependencies; remove the two CrewAI/callback filterwarnings
4. Run `pip install -e .` — verify crewai is no longer present in the environment
5. Run full test suite — must be green

Also delete or archive `config/tasks.yaml` — it is a CrewAI legacy artifact that was
never wired to any production code path.

---

### [~] 4.8 — End-to-End Scene Playthrough

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

### [x] 4.10a — Display Agent Outputs to Player

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

### [x] 4.10b — Move State Writing from Scribe to Orchestrator

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

### [x] 4.12 — Fix Rich Console Leak in Verbose Output

CrewAI uses a Rich Console that holds a reference to the original terminal fd. The
`verbose_to_file()` context manager only redirects `sys.stdout`, so Rich output (task
completion boxes, Crew Completion panel) bypasses the redirect and always prints to the
terminal — including the final "Crew Completion" box which currently appears mid-output
between NPC task prints.

Investigate: check which object CrewAI's Printer class uses for output — it may be
`sys.stdout` at print time (easy fix) or a Console created at import/init time (needs
patching). Run a quick grep against the installed crewai package source.

Fix: whichever approach closes the leak cleanly without monkey-patching internals fragily.
Acceptable outcomes in priority order:
1. Rich output goes to verbose log file, not terminal
2. Rich output suppressed entirely (set `verbose=False` on Crew — loses log detail but
   stops the leak)

---

### [x] 4.13 — Three-Phase Turn Loop with Per-Check Referee Isolation

See `docs/plans/architect_todo.md` — "Resolved Decisions: Turn Loop" for the full
design rationale and Option A vs B discussion. Option B was chosen.

**Overview:** Each turn runs three sequential kickoffs:

---

#### Phase 1 — NPC wave

`build_npc_crew(sr_context, narrator_context, npc_contexts: dict[str, str]) -> Crew`

Tasks: Show Runner → Narrator → NPCs in order, each chaining prior NPC task context.

```python
# Each NPC task:
context=[task_plan] + prior_npc_tasks  # sees beat plan + all earlier NPC outputs
```

After kickoff: print Narrator + NPC outputs to player. Collect `npc_wave_text`
(joined NPC task `output.raw` strings, labelled by npc_id).

---

#### Between Phase 1 and 2 — Player input

Single free-form prompt: `"What do {pc_name} and {ai_pc_name} do? >"`.
No separate nudge prompt — direction to Kaelen is embedded in the player's text.

---

#### Phase 2 — PC wave + check identification

`build_pc_crew(npc_wave_text, ai_pc_contexts, player_action, sr_review_context) -> Crew`

Tasks:
1. **Kaelen** (AI PC) — task description contains: character prompt + npc_wave_text +
   player action. No tools. Outputs Kaelen's dialogue and actions.
2. **Show Runner review** — task description contains: beat plan summary + npc_wave_text
   + player action + Kaelen output (via `context=[kaelen_task]`). Outputs structured
   check list:
   ```
   CHECKS:
   1. Z-4P0 | Negotiation | Presence | Opposed vs Bargos Cool | +1 Boost (diplomatic)
   CHECKS_END
   ```
   Or `NO_CHECKS` if nothing to resolve.

After kickoff: print Kaelen output. Parse Show Runner review output into check specs
(list of dicts with keys: actor, skill, characteristic, difficulty, notes).

---

#### Phase 3 — Resolution (dynamic, one Referee task per check + Scribe)

`build_resolution_crew(check_specs, scribe_context, full_turn_summary) -> Crew`

Tasks:
- One Referee task per entry in `check_specs`. Each task description contains only
  that check's spec (actor, skill, pool construction, difficulty, notes). Tasks chain
  so each Referee sees prior Referee results (relevant for multi-attack rounds).
- Scribe task at the end: sees all Referee outputs, outputs one-sentence session log.

If `check_specs` is empty (NO_CHECKS), skip Phase 3 entirely — run a single-task
Scribe crew or write the log entry from the orchestrator directly.

After kickoff: print Referee outputs (skip "No check required"). Write last_actions
(all NPC outputs + Kaelen + player action). Append Scribe session log entry.

---

**`load_scene_characters()` changes:**

Add `player_filter: str | None = None` parameter:
- `None` → all characters (backwards compatible)
- `"npc"` → only characters with no `player` field and inline NPCs
- `"ai"` → only characters with `player: "ai"`

Human characters (`player: "human"`) are always excluded from scene_chars (they act
via prompt, never as agent tasks).

---

**`crew.py` changes:**

Remove `build_crew()`. Replace with:
- `build_npc_crew(sr_context, narrator_context, npc_contexts)`
- `build_pc_crew(npc_wave_text, ai_pc_contexts, player_action, sr_review_context)`
- `build_resolution_crew(check_specs, scribe_context, full_turn_summary)`

---

**Tests:**
- `test_npc_crew_chains_npc_contexts` — 2nd NPC task has 1st in context
- `test_npc_crew_task_order` — SR, Narrator, NPC... in order
- `test_pc_crew_kaelen_sees_npc_wave` — Kaelen task description contains npc_wave_text
- `test_pc_crew_kaelen_sees_player_action` — Kaelen task description contains player action
- `test_pc_crew_show_runner_review_in_last_task` — final task assigned to Show Runner
- `test_resolution_crew_one_task_per_check` — 2 specs → 2 Referee tasks + 1 Scribe
- `test_resolution_crew_referee_tasks_chained` — 2nd Referee task has 1st in context
- `test_resolution_crew_empty_specs_has_only_scribe` — 0 checks → 1 Scribe task
- `test_load_scene_characters_npc_filter` — excludes ai PCs and human PCs
- `test_load_scene_characters_ai_filter` — returns only ai PCs

---

### [x] 4.14 — Five-Step Resolution Pipeline

Replace Phase 3 (the current `build_resolution_crew` + Show Runner review) with the
decomposed five-step pipeline. See `docs/plans/architect_todo.md` — "Resolved Decisions:
Resolution Pipeline" for full rationale and data flow.

---

#### [x] 4.14a — Remove Show Runner review from Phase 2

In `crew.py`: remove `task_sr_review` from `build_pc_crew()`. The crew now contains only
AI PC tasks. Update the return to exclude the Show Runner agent from `all_agents`.

In `orchestrator.py`: remove the `review_output` and `check_specs` variables that depended
on it. The Show Runner review role is now handled by step 3b.

Tests: update `test_pc_crew_show_runner_review_in_last_task` — it should now assert there
is no Show Runner task in the PC crew.

---

#### [x] 4.14b — `load_scene_yamls()` helper

Add `load_scene_yamls(scene: dict, characters_dir: str = "characters") -> dict[str, dict]`
to `src/showrunner/agents/actors.py`.

Returns `{character_id: raw_yaml_dict}` for every character in `scene["npcs_present"]`
that is not `player: "human"`. Does not include inline NPCs (they have no YAML file).

Tests:
- Returns raw YAML dicts keyed by character id
- Excludes human player characters
- Does not crash on inline NPCs (they're silently skipped)

---

#### [x] 4.14c — Step 3a: action summary tasks

Add `build_summary_crew(action_map: dict[str, str]) -> Crew` to `crew.py`.

`action_map` is `{actor_id: action_text}` covering all NPC outputs, AI PC outputs,
and the player action collected this turn.

Each actor gets one alien 3B task (use `create_actors()` with `tools=[]`, already correct).
Task description: "Summarise in 1–2 sentences what {actor_id} did: {action_text}".
Task `name` = actor_id so orchestrator can collect outputs by name.

Orchestrator after kickoff:
- Collects `{actor_id: summary_text}` from task outputs
- Writes `logs/turn_{turn_ts}_{beat_id}_summaries.txt` (one line per actor: `{id}: {summary}`)

Tests:
- Crew has one task per actor
- Each task assigned to alien 3B agent (role "NPC Voice Actor")
- Task names match actor_id keys

---

#### [x] 4.14d — Step 3b: check identification task

Add `build_check_crew(summaries_text: str, stats_text: str) -> Crew` to `crew.py`.

Single sardinia 8B task (Show Runner agent). Task description:
```
## Action Summaries
{summaries_text}

## Character Stats
{stats_text}

Review every action. List every skill check, opposed roll, or combat attack triggered.
Output format — one line per check:
{n}. {actor} | {skill} | {characteristic} {value} | {skill_rank} | {difficulty} | {notes}

If no checks are needed, output exactly: NO_CHECKS
```

Orchestrator before calling:
- Reads `turn_summaries.txt` → `summaries_text`
- Calls `load_scene_yamls()`, builds `stats_text` (one block per character: name,
  characteristics, skill names + ranks)

After kickoff:
- Writes `logs/turn_{turn_ts}_{beat_id}_checks.txt`
- Parses output into `check_specs: list[dict]` with keys:
  `actor, skill, characteristic, char_value, skill_rank, difficulty, notes`
  (new parser replaces `_parse_check_specs`; characteristic value and skill rank are now
  required fields)

Tests:
- Single Show Runner task in crew
- `NO_CHECKS` → empty list
- Valid check line parses all seven fields correctly

---

#### [x] 4.14e — Step 3c: dice rolling + ruling tasks

Add `build_ruling_crew(check_specs: list[dict]) -> Crew` to `crew.py`.

For each spec, roll the dice in Python (`roll_pool()` from `dice.py`), then create one
sardinia 8B task (Show Runner agent). Task description:
```
Resolve this check:
Actor: {actor} | Skill: {skill} | Difficulty: {difficulty}
Notes: {notes}

Dice roll result: {roll_result_string}

State the outcome: passed or failed, wounds dealt (if attack), and any triumph/despair effects.
One short paragraph.
```

Task `name` = actor (for output collection). Tasks chain so each sees prior rulings.

After kickoff:
- Collects `{actor: ruling_text}` from task outputs
- Writes `logs/turn_{turn_ts}_{beat_id}_results.txt`

If `check_specs` is empty, skip this crew entirely (no file written; 3d and 3e receive
empty results context).

Tests:
- One task per check spec
- Tasks chained (2nd task has 1st in context)
- Dice are rolled in Python before task creation (mock `roll_pool`, assert called once per spec)
- Empty specs → empty crew (or skip)

---

#### [x] 4.14f — Step 3d: resolution narrative

Add `build_narrative_crew(summaries: str, checks: str, results: str) -> Crew` to `crew.py`.

Single sardinia 8B task (Show Runner agent). Task description contains all three file
contents. Output: player-facing narrative prose. Expected output: 2–4 sentences describing
what just happened.

Orchestrator: print output directly to terminal. Do not write to log file.

Tests:
- Single Show Runner task
- Task description contains all three input strings

---

#### [x] 4.14g — Step 3e: last action extraction

Add `build_last_action_crew(actor_ids: list[str], summaries: str, checks: str, results: str) -> Crew`
to `crew.py`.

One sardinia 8B task per actor (Narrator agent). Task description:
```
Given these events:
{summaries}
{checks}
{results}

What was {actor_id}'s last action this turn? One sentence.
```

Task `name` = actor_id.

Orchestrator after kickoff:
- Collects `{actor_id: last_action_sentence}`
- Calls `update_scene_state({"last_actions": collected})` to replace raw action text
  with the extracted sentences

Tests:
- One task per actor_id
- Task names match actor_ids
- Orchestrator calls `update_scene_state` with correct structure

---

#### [x] 4.14h — Wire everything in orchestrator

Replace the current Phase 3 block in `run_turn_loop()` with the five-step pipeline:

```python
# 3a — summaries
action_map = {**npc_outputs, **ai_pc_outputs, player_id: player_action}
summary_crew = build_summary_crew(action_map)
with verbose_to_file(verbose_path):
    summary_crew.kickoff()
summaries_text = _write_turn_file(turn_ts, current_beat, "summaries", ...)

# 3b — check identification
stats_text = _build_stats_text(load_scene_yamls(scene))
check_crew = build_check_crew(summaries_text, stats_text)
with verbose_to_file(verbose_path):
    check_crew.kickoff()
check_specs = _parse_check_output(...)  # new parser
_write_turn_file(turn_ts, current_beat, "checks", ...)

# 3c — dice rolling + rulings
ruling_crew = build_ruling_crew(check_specs)  # rolls dice internally
with verbose_to_file(verbose_path):
    ruling_crew.kickoff()
results_text = _write_turn_file(turn_ts, current_beat, "results", ...)

# 3d — resolution narrative (print to player)
narrative_crew = build_narrative_crew(summaries_text, checks_text, results_text)
with verbose_to_file(verbose_path):
    narrative_crew.kickoff()
print(_get_task_output(narrative_crew, "Show Runner"))

# 3e — last action extraction
last_action_crew = build_last_action_crew(list(action_map.keys()), ...)
with verbose_to_file(verbose_path):
    last_action_crew.kickoff()
# collect + write to scene_state
```

Add `_write_turn_file(turn_ts, beat_id, type, content) -> str` helper: writes the file,
returns the content string for reuse.

Add `_build_stats_text(yamls: dict[str, dict]) -> str` helper: formats character stats
for the 3b prompt (characteristic values + skill names and ranks).

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
