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

- [ ] Parse Genesys Core Rulebook into indexed sections (`swskin/rules/`)
  - `rules/index.md`, `rules/dice.md`, `rules/combat.md`, `rules/skills.md`
- [ ] Verify LiteLLM can reach llama.cpp on Alien and LM Studio on Sardinia

---

## Phase 4: MVP Scene — Bargos Mansion

Target: run the full Bargos mansion scene from *Debts to Pay* end-to-end.

Scene covers: arrival, audience with Bargos, the Gamorrean Rumble combat encounter.
Reference: `swskin/Game_masters_kit.pdf` Acts 1–2.

Phases 5 and 6 are **not required** for this phase. The Show Runner operates with the
specific rules and NPC stats for this scene baked inline — no `rules_lookup()` tool needed.

- [ ] Show Runner: manage beat progression, Gamorrean arrival ticking clock
- [ ] Narrator: beat openers and session log entries
- [ ] Actors: voice Bargos, Genko, C3-P9, Gamorreans — using `render_actor_prompt()`
- [ ] Resolution pipeline: handle Vigilance check (spotting Gamorreans), Brawl/Melee combat checks
  - Show Runner system prompt includes the specific rules needed for this scene inline
  - `rules_lookup()` is a future Phase 5 concern
- [ ] CLI: player turn prompt, `!` directive injection, manual dice input option
- [ ] Play through the scene; identify and fix issues

---

## Phase 5: Genesys Rules Parser (swskin)

Needed before Phase 7. Not blocking Phase 4.

The Show Runner's `rules_lookup()` tool is stubbed but unimplemented. This phase
delivers the data it queries. Without it the Show Runner must have rules hard-coded per
scene, which becomes unmanageable across the full 15-room Gavos adventure.

- [ ] Script to extract sections from Genesys Core Rulebook PDF → `swskin/rules/`
- [ ] `rules/index.md` — section list with page references
- [ ] Priority sections: `rules/dice.md`, `rules/combat.md`, `rules/skills.md`, `rules/talents.md`
- [ ] Wire `rules_lookup()` tool in Show Runner agent — keyword search against indexed sections

---

## Phase 6: OggDude Data Ingestion (swskin)

Needed before Phase 7. Not blocking Phase 4.

Provides structured weapon, skill, talent, and career data. Without it, NPC and weapon stats
must be hand-transcribed into scene or character files — manageable for the MVP scene,
not for a full adventure.

- [ ] `tools/xml_to_md.py` — converts OggDude XML exports to structured Markdown
- [ ] Output: `swskin/data/weapons.md`, `skills.md`, `talents.md`, `careers.md`
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

- [ ] World skin loader: `config/world.yaml` points to any swskin-compatible repo
- [ ] Document the world skin schema so other skins can be built
- [ ] Session resume: save/restore `state/` between sessions
- [ ] Consider richer CLI output (colour, formatted stat blocks)
