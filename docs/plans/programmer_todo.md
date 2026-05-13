# Programmer TODO

Implementation tasks for the showrunner engine.
Follow TDD: write the failing test first, then write only enough code to make it pass.

Reference documents:
- `docs/plans/architecture.md` — system design
- `docs/plans/character_schema.md` — character file schema and `render_actor_prompt` spec
- `docs/plans/architect_todo.md` — phased plan with open decisions

---

## Current Priority: Phase 4 — End-to-End Scene Playthrough

### [~] 4.16 — Concise per-call instrumentation log

Replace the verbose full-content prompt/response log with a single summary line per LLM call.

**Log format** — one line per call:
```
HH:MM:SS  show_runner   sardinia  beat_plan     1247p →   342r
HH:MM:SS  narrator      sardinia  narration      892p →   218r
HH:MM:SS  actors        sardinia  npc_voice     1534p →   156r
```

**What changes:**

`instrumentation.py`:
- Replace `_PromptLogger._write(server, type, text)` + `_format_messages()` + `_server_for()` + `server_map`
  with a single `log(agent, server, task, prompt_len, response_len)` method that writes one line
- Remove `verbose_path` from `setup_instrumentation()` — return only `prompts_path` (single `Path`)

`llm.py`:
- Add `task: str` parameter to `call_llm()` (required, no default)
- Compute `server` from `cfg["model_alias"].split("/")[0]` (e.g. `sardinia/llama-3.1-8b` → `sardinia`)
- Replace the two `_prompt_logger._write()` calls with one `_prompt_logger.log(agent_name, server, task, prompt_len, response_len)`
  where `prompt_len = len(system_prompt) + len(user_message)`

`runner.py` — add `task=` to every `call_llm()` call:
- `run_npc_wave`: show_runner→`"beat_plan"`, narrator→`"narration"`, actors→`"npc_voice"`
- `run_pc_wave`: actors→`"pc_voice"`
- `run_summary_phase`: actors→`"summary"`
- `run_check_phase`: show_runner→`"check_id"`
- `run_ruling_phase`: show_runner→`"ruling"`
- `run_narrative_phase`: show_runner→`"narrative"`
- `run_last_action_phase`: narrator→`"last_action"`
- `run_scribe_phase`: scribe→`"session_log"`

`orchestrator.py`:
- Fix `verbose_path, prompts_path = setup_instrumentation(timestamp)` → `prompts_path = setup_instrumentation(timestamp)`

**Partial start:** `tests/test_instrumentation.py` and `tests/test_llm.py` have already been updated
to expect the new interface. Run `pytest tests/test_instrumentation.py tests/test_llm.py` — they
should be RED. Implement to make them GREEN, then verify the full suite passes.

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
