# Programmer TODO

Implementation tasks for the showrunner engine.
Follow TDD: write the failing test first, then write only enough code to make it pass.

Reference documents:
- `docs/plans/architecture.md` — system design
- `docs/plans/character_schema.md` — character file schema and `render_actor_prompt` spec
- `docs/plans/architect_todo.md` — phased plan with open decisions

---

## Current Priority: Phase 4 — MVP Scene

### Architect deliverables (ready for Phase 4)

- `characters/kaelen_sunara.yaml` + `.md` — AI-driven Smuggler/Thief
- `characters/Z-4P0.yaml` + `.md` — Human-driven droid companion (`player: "human"`)
- `docs/plans/scene_format.md` — Scene YAML specification and Narrator prompt assembly design
- `state/scene_0.yaml` — Bargos mansion scene (Act 1: audience + Gamorrean Rumble)
- `state/scene_1.yaml` — Gavos arrival scene (Act 2: landing pad + EV-8D3 deception)

---

### [x] 4.8a — Session Instrumentation

New file: `src/showrunner/instrumentation.py`

#### Verbose log — CrewAI output to file

Redirect `sys.stdout` to `logs/verbose_TIMESTAMP.log` for the duration of `crew.kickoff()`,
then restore it. All user-facing `print()` calls in `run_turn_loop()` happen outside that
window, so they stay on the terminal.

Implement as a context manager `verbose_to_file(log_path: Path)`.

#### Prompt/response log — LiteLLM callback

Register a `CustomLogger` subclass via `litellm.callbacks` at session startup. It writes
every prompt and response to `logs/prompts_TIMESTAMP.log` in this format:

```
2026-05-12 16:45:23 | gemini | prompt
================================================================================
[system]
You are the Show Runner...

[user]
Run a single scene beat...
================================================================================

2026-05-12 16:45:25 | gemini | response
================================================================================
The Gamorreans have arrived...
================================================================================
```

**Server name mapping**: at startup, read `config/litellm.yaml` and build a reverse map
from `litellm_params.model` → the prefix of `model_name`. Example:
`"openai/Llama-3.2-3B-Instruct.gguf"` → `"alien"`. Use this map in the callback to
resolve the server label from the model string LiteLLM passes to the callback.

#### Functions to implement in `instrumentation.py`

- `_build_server_map(config_path: Path) -> dict[str, str]`
- `_PromptLogger(CustomLogger)` — implements `log_pre_api_call` (writes prompt block) and
  `log_success_event` (writes response block)
- `verbose_to_file(log_path: Path)` — context manager for stdout redirect
- `setup_instrumentation(timestamp: str) -> tuple[Path, Path]` — registers the LiteLLM
  callback, returns `(verbose_path, prompts_path)`

#### Changes to `orchestrator.py`

- Call `setup_instrumentation(timestamp)` alongside `_setup_session_log`; use the same
  `timestamp` string so all three log files share a common prefix
- Print both paths at session start:
  `Verbose log: logs/verbose_TIMESTAMP.log  (tail -f to watch)`
  `Prompt log:  logs/prompts_TIMESTAMP.log`
- Wrap `crew.kickoff()` with `verbose_to_file(verbose_path)`

#### Tests (`tests/test_instrumentation.py`)

- `test_server_map_alien` — alien model string maps to `"alien"`
- `test_server_map_sardinia` — sardinia model string maps to `"sardinia"`
- `test_server_map_gemini` — gemini model string maps to `"gemini"`
- `test_server_for_known_model` — `_PromptLogger._server_for` returns correct label
- `test_server_for_unknown_model_returns_model` — unknown model falls back to model string
- `test_format_messages_single` — single message formatted with role header
- `test_format_messages_multiple_roles` — system + user both present and labelled
- `test_write_creates_file` — `_write` creates the log file
- `test_write_format_contains_header_fields` — server, type, and text all present
- `test_write_appends_on_multiple_calls` — both entries present after two writes
- `test_verbose_redirect_captures_stdout` — output inside context lands in file
- `test_verbose_redirect_restores_stdout` — `sys.stdout` is the real stdout after exit
- `test_verbose_redirect_restores_stdout_on_exception` — restored even if exception raised

---

### [ ] 4.8b — Worker Agent Context Enrichment

**Problem**: Worker agents (Narrator, Referee, Scribe) have thin backstories. When the
Show Runner delegates a task and the worker lacks context to complete it, CrewAI's
hierarchical loop escalates back to the Show Runner — a Gemini call. More confused
rounds = more Gemini cost. Giving workers complete deterministic context upfront
eliminates those rounds.

**Note on `consult_show_runner`**: that tool is a stub — it never calls Gemini. It
returns a "proceed with your judgment" message. Do not remove it; it is a useful
fallback for small models. Gemini calls come from CrewAI's orchestration loop, not
from this tool.

---

#### 1. Enrich `render_narrator_context()`

File: `src/showrunner/agents/narrator.py`

Current signature:
```python
render_narrator_context(scene: dict, beat_id: str) -> str
```

New signature:
```python
render_narrator_context(scene: dict, beat_id: str, last_action: str, party_stats: dict) -> str
```

Add two new sections at the bottom of the rendered string (dynamic content, after the
static beat notes):

```
## Last Player Action
<last_action text, or "None yet." if empty>

## Party Status
<name>: wounds <n>, strain <n>
<name>: wounds <n>, strain <n>
```

Update the call in `orchestrator.py` to pass `last_action` and `party_stats`.

Tests to add to `tests/test_narrator.py`:
- `test_narrator_context_includes_last_action`
- `test_narrator_context_no_action_shows_placeholder`
- `test_narrator_context_includes_party_status`
- `test_narrator_context_empty_party_stats_renders_cleanly`

---

#### 2. Add `render_referee_context()`

File: `src/showrunner/agents/referee.py`

New function:
```python
render_referee_context(scene: dict, beat_id: str) -> str
```

Renders scene-specific context for the current beat. Append this to the existing
`build_referee_backstory()` output — do not replace it. The general rules stay in
the backstory; the scene-specific data goes in the appended context.

Include:

**Current beat checks** (if any):
```
## Checks This Beat
- Skill: Negotiation | Characteristic: Presence | Difficulty: 2 | Opposed: Cool
  Notes: PCs may attempt to negotiate better terms. Opposed by Bargos's Cool
  (ranks 2, Presence 3). ...
```

**Minion groups** (always include if present in scene):
```
## Minion Groups
Renegade Gamorrean Guards (count: 6, soak: 4, wound threshold: 5 per minion)
  Brawn 3, Agility 2, Melee 1, Brawl 1
  Vibro-Axe: damage 5, crit 3, Engaged, Vicious 2
```

Wire into `create_referee()`: accept a `context: str = ""` param; if provided, append
to backstory (same pattern as `create_narrator(context=...)`).

Wire into `build_crew()`: add `referee_context: str = ""` param; pass to
`create_referee()`.

Wire into `orchestrator.py`: call `render_referee_context(scene, current_beat)` and
pass to `build_crew()`.

Tests to add to `tests/test_referee.py`:
- `test_referee_context_includes_beat_checks`
- `test_referee_context_includes_check_notes`
- `test_referee_context_empty_checks_renders_cleanly` — beat with `checks: []`
- `test_referee_context_includes_minion_group_stats`
- `test_referee_context_includes_minion_weapons`
- `test_referee_context_no_minion_groups_renders_cleanly`

Use fixture scene data in tests — do not read from `state/` or `characters/`.

---

#### 3. Add `render_scribe_context()`

File: `src/showrunner/agents/scribe.py`

New function:
```python
render_scribe_context(scene_state: dict, party_stats: dict) -> str
```

Renders current state values so the Scribe knows the starting point for updates
and what it is and is not allowed to touch.

Include:

```
## Current State (read before writing)

### party_stats.yaml — update wounds and strain after each resolved action
<character name>: wounds <n>, strain <n>
<character name>: wounds <n>, strain <n>

### scene_state.yaml — update character_plans and ticking_clocks only
Current beat: <beat_id>  ← DO NOT CHANGE THIS. Beat progression is Show Runner only.
Ticking clocks: <clock data or "none">
Character plans: <plans or "none">

### session_log.md — append a one-sentence narrative summary of what happened
Format: "YYYY-MM-DD HH:MM — <what happened>"
```

Wire into `create_scribe()`: accept `context: str = ""`, append to backstory.

Wire into `build_crew()`: add `scribe_context: str = ""` param; pass to
`create_scribe()`.

Wire into `orchestrator.py`: call `render_scribe_context(scene_state, party_stats)`
and pass to `build_crew()`.

Tests in `tests/test_scribe.py` (create if it doesn't exist):
- `test_scribe_context_includes_character_wounds`
- `test_scribe_context_includes_current_beat`
- `test_scribe_context_warns_against_changing_beat`
- `test_scribe_context_includes_ticking_clocks_when_present`
- `test_scribe_context_no_clocks_renders_cleanly`
- `test_scribe_context_includes_log_format`

Use fixture YAML data in tests — do not read from `state/`.

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

### Referee in Phase 4

The Referee's system prompt for this scene must include inline:
- Pool construction rule (already in `dice_roller.py` comments — copy to prompt)
- Vigilance check: Average difficulty (2 purple), opposed by Stealth if Gamorreans are hiding
- Brawl/Melee combat: difficulty = target's defense rating, +1 purple per range band beyond engaged
- Soak: damage - soak = wounds taken (minimum 0)
- Critical injuries: triggered on Advantage spend or when wounds exceed threshold

Do NOT wire `rules_lookup()` in Phase 4. Leave it raising `NotImplementedError`.

### What to do when you hit an issue

Issues found during play are bugs — fix them. If something requires an architectural
decision, document it and raise it with Tom before implementing a workaround.

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
