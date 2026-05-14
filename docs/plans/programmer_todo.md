# Programmer TODO

Reference documents:
- `docs/plans/terminology.md` — canonical terms
- `docs/plans/game_loop.md` — source of truth for the turn loop
- `docs/plans/architecture.md` — system design
- `docs/plans/character_schema.md` — character file schema

---

## Phase 4 — End-to-End Scene Playthrough

### [~] 4.33 — Play through scene_0.yaml

Run `python -m showrunner.main -v --dump-prompts --reset` and play the Bargos mansion
scene from entry to exit.

- [ ] Scene entry read-aloud delivered
- [ ] Bargos audience beat runs; Negotiation check can be triggered
- [ ] Gamorrean warning beat triggers; Vigilance check fires
- [ ] Gamorrean Rumble combat resolves with dice (auto or manual input)
- [ ] Wounds tracked correctly; minions die at wound threshold multiples
- [ ] Mission brief beat runs after combat
- [ ] Scene exits cleanly; scene_state.yaml updated

Fix any bugs found. Raise architectural issues with Tom before implementing.

---

## Phase 5 — Genesys Rules Parser

Do not begin until Phase 4 playthrough is signed off.

- [ ] `tools/parse_rulebook.py` — extract PDF sections to `skin/rules/` (use pymupdf)
- [ ] `skin/rules/index.md` — section list with page references
- [ ] `rules_lookup(keyword) -> str` in `src/showrunner/tools/rules_lookup.py`
- [ ] Wire `rules_lookup()` into Show Runner agent
- [ ] Smoke test: can retrieve rules for "critical injury", "soak", "Brawl"

---

## Phase 6 — OggDude Data Ingestion

Do not begin until Phase 5 is complete.

- [ ] `tools/xml_to_md.py` — convert OggDude XML exports to `skin/data/`
- [ ] Smoke test: Show Runner can look up Gamorrean vibro-ax stats from `weapons.md`
