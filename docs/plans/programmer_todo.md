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

---

### [x] 4.34 — Route pipeline-internal calls to Scribe agent

Per game_loop.md Ref A, the following `call_llm` calls must change agent:

- `run_companion_wave` — narrator summary call → `"scribe"`
- `run_npc_wave` — narrator summary call → `"scribe"`
- `run_summaries` — narrator call → `"scribe"`
- `run_checks` — show_runner call → `"referee"`
- `run_narrative` — show_runner call → `"narrator"`
- `run_last_actions` — narrator call → `"scribe"`
- `run_plan_update` — individual plan calls → `"scribe"`

Agent prompt files to create/update:
- Scribe: new `config/prompts/agent_scribe.md` — compact summarization, last-action
  extraction, and per-character plan generation (pipeline-internal). Add `prompt_file`
  to `agents.yaml`. Remove old state-writer goal/backstory.
- Referee: already has goal/backstory in `agents.yaml`; wire up `prompt_file` if needed.

Follow TDD. Update `test_runner.py` assertions that check `call_llm` agent names.

The following tests now fail due to config changes and must be updated to reflect current
model assignments (all agents now on gemini) and the referee/scribe prompt_file path:

- `test_config.py`: `test_show_runner_uses_sardinia`, `test_narrator_uses_sardinia_endpoint`,
  `test_referee_uses_alien_endpoint`, `test_scribe_uses_alien_endpoint`,
  `test_actors_uses_sardinia_endpoint` — assertions reference old local model endpoints;
  update to assert gemini model is used.
- `test_llm.py`: `test_call_llm_passes_model_from_config`,
  `test_call_llm_passes_api_base_for_local_models` — narrator now routes to gemini, not
  sardinia; update accordingly.
- `test_llm.py`: `test_call_llm_non_gemini_does_not_include_thinking` — narrator is now
  gemini; pick a genuinely non-gemini agent or use a fake config.
- `test_llm.py`: `test_build_system_prompt_referee_fallback_contains_role` — referee now
  has a `prompt_file`; the fallback path no longer applies. Delete or replace this test.

---

### [~] 4.33 — End-to-End Scene Playthrough

No tests for this task — this is exploratory play. Run `src/showrunner/main.py` and
play through `skin/scenes/scene_0.yaml` (Bargos mansion) from entry to exit condition.

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
