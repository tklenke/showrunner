# Architect TODO

Open decisions and phased work for the showrunner engine.
For the stable design record, see `architecture.md`.
For resolved decisions, see git log.

---

## Open Decisions

Items that have not yet been fully resolved. These need an answer before the relevant
implementation phase begins.

- [ ] **Sardinia context window** — LM Studio / Llama 3.1 8B max context. The rendered
  actor prompt for a complex NPC + scene state could be 2–3K tokens. Confirm the model
  can handle this while leaving enough room for generation.

- [ ] **! directive scope** — Exactly what context does a `!` player directive inject into?
  Narrator only? Or broadcast to all agents on that turn? Decide before Phase 4.

- [ ] **Manual dice input format** — Confirm the symbol notation Tom wants to type.
  Current plan: `2s 1a 1f 1t`, `1tr`, `1de`. Ratify or change before Phase 1.

---

## Phase 0: Pre-Implementation Setup

- [ ] Parse Genesys Core Rulebook into indexed sections (`skin/rules/`)
  - `rules/index.md`, `rules/dice.md`, `rules/combat.md`, `rules/skills.md`
- [ ] Verify LiteLLM can reach llama.cpp on Alien and LM Studio on Sardinia

---

## Phase 4: MVP Scene — Bargos Mansion

Target: run the full Bargos mansion scene from *Debts to Pay* end-to-end.

Scene covers: arrival, audience with Bargos, the Gamorrean Rumble combat encounter.
Reference: `skin/Game_masters_kit.pdf` Acts 1–2.

Phases 5 and 6 are **not required** for this phase. The Show Runner operates with the
specific rules and NPC stats for this scene baked inline — no `rules_lookup()` tool needed.

- [ ] Prompts log enhancements (tasks 4.34–4.35): call ID, character label, --dump-prompts full capture
- [ ] Show Runner: manage beat progression, Gamorrean arrival ticking clock
- [ ] Narrator: beat openers and session log entries
- [ ] Actors: voice Bargos, Genko, C3-P9, Gamorreans — using `render_actor_prompt()`
- [ ] Resolution pipeline: handle Vigilance check (spotting Gamorreans), Brawl/Melee combat checks
  - Show Runner system prompt includes the specific rules needed for this scene inline
  - `rules_lookup()` is a future Phase 5 concern
- [ ] CLI: player turn prompt, `!` directive injection, manual dice input option
- [ ] Play through the scene; identify and fix issues

---

## Phase 5: Genesys Rules Parser (skin)

Needed before Phase 7. Not blocking Phase 4.

- [ ] Script to extract sections from Genesys Core Rulebook PDF → `skin/rules/`
- [ ] `rules/index.md` — section list with page references
- [ ] Priority sections: `rules/dice.md`, `rules/combat.md`, `rules/skills.md`, `rules/talents.md`
- [ ] Wire `rules_lookup()` tool in Show Runner agent — keyword search against indexed sections

---

## Phase 6: OggDude Data Ingestion (skin)

Needed before Phase 7. Not blocking Phase 4.

- [ ] `tools/xml_to_md.py` — converts OggDude XML exports to structured Markdown
- [ ] Output: `skin/data/weapons.md`, `skills.md`, `talents.md`, `careers.md`
- [ ] Validate Show Runner can look up a weapon stat (e.g., Gamorrean vibro-ax) from converted data

---

## Phase 7: Full Gavos Adventure

- [ ] Convert all 15 mine rooms to scene YAML
- [ ] Ticking clock: storm barrier generator countdown in `scene_state.yaml`
- [ ] Lookout vehicle chase (cloud car space/planetary combat variant)
- [ ] Way station encounter and miner rescue
- [ ] Final negotiation with Bargos (Charm check resolution)

---

## Phase 8: Polish and Extensibility

- [ ] Document the skin/ schema so other skins can be built (the Star Wars skin is the reference impl)
- [ ] Session resume: save/restore `state/` between sessions
- [ ] Consider richer CLI output (colour, formatted stat blocks)
