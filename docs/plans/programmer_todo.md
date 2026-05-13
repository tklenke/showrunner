# Programmer TODO

Implementation tasks for the showrunner engine.
Follow TDD: write the failing test first, then write only enough code to make it pass.

Reference documents:
- `docs/plans/architecture.md` — system design
- `docs/plans/character_schema.md` — character file schema and `render_actor_prompt` spec
- `docs/plans/architect_todo.md` — phased plan with open decisions

---

## Current Priority: Phase 4 — MVP Scene

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
