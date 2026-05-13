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

### [x] 4.36 — Remove all dead fields from agents.yaml and config.py

Three categories of dead fields identified. Remove all in one pass.

**Dead for `show_runner`, `narrator`, `actors` (have `prompt_file`):**

`role`, `goal`, `backstory` — `build_system_prompt()` reads from `prompt_file` and
never touches these fields for these three agents. Content lives in `config/prompts/agent_*.md`.

Do NOT remove from `referee` and `scribe` — they have no `prompt_file` and still use the
fallback path `f"You are {cfg['role']}.\n\n{cfg['goal']}\n\n{cfg['backstory']}"`.

**Fully dead for all agents (CrewAI remnants):**

`verbose` and `allow_delegation` — loaded by `load_agent_configs()` into the config dict
but never read by any code. Were CrewAI agent constructor parameters; nothing in the
current engine uses them.

Remove from all five agents in `config/agents.yaml` and from `load_agent_configs()` in
`config.py`.

**Changes:**
- `config/agents.yaml`: remove `role`, `goal`, `backstory` from `show_runner`, `narrator`,
  `actors`; remove `verbose` and `allow_delegation` from all five agents
- `config.py` `load_agent_configs()`: remove `"verbose"` and `"allow_delegation"` from
  the returned dict; make `"role"`, `"goal"`, `"backstory"` optional (use `.get()`) so
  the fallback path still works for `referee`/`scribe` without crashing on missing keys
  for the others

**Tests:**
- `build_system_prompt("narrator")` still returns non-empty string with world context
- `build_system_prompt("referee")` still works via fallback path (no `prompt_file`)
- `load_agent_configs()` does not raise for entries missing `role`/`goal`/`backstory`
- No test references `cfg["verbose"]` or `cfg["allow_delegation"]` (remove those assertions)

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
