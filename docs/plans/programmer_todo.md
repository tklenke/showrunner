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

### [ ] 4.8a — Session Instrumentation

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
