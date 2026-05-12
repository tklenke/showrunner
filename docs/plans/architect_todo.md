# Architect TODO

Open decisions and phased work for the showrunner engine.
Completed items are checked. For the stable design record, see `architecture.md`.

---

## Open Decisions

Items that have not yet been fully resolved. These need an answer before the relevant
implementation phase begins.

- [ ] **LAN addresses** — Confirm Alien's IP and Sardinia's IP (or DNS names) for
  `config/litellm.yaml`. Current placeholders: `http://alien:8080` and `http://sardinia:1234`.

- [ ] **Gemini model** — Confirm which Gemini model to use (currently `gemini-2.0-flash`).
  Verify Google AI Studio key is available and working before Phase 2.

- [ ] **Sardinia context window** — LM Studio / Llama 3.1 8B max context. The rendered
  actor prompt for a complex NPC + scene state could be 2–3K tokens. Confirm the model
  can handle this while leaving enough room for generation.

- [ ] **! directive scope** — Exactly what context does a `!` player directive inject into?
  Narrator only? Or broadcast to all agents on that turn? Decide before Phase 4.

- [ ] **Manual dice input format** — Confirm the symbol notation Tom wants to type.
  Current plan: `2s 1a 1f 1t`, `1tr`, `1de`. Ratify or change before Phase 1.

- [ ] **Scribe write strategy** — Atomic file writes (write to temp, rename) vs. direct
  overwrite. Decide before Phase 3. Low stakes but needs to be consistent.

- [ ] **MVP PC character sheet** — Tom to provide the PC character YAML and MD for the
  Bargos mansion scene. Bargos is done; at least one PC is needed to run Phase 4.

---

## Phase 0: Pre-Implementation Setup

- [x] Architecture design finalized — see `architecture.md`
- [x] `docs/plans/character_schema.md` — YAML schema for character files documented
- [x] `docs/plans/architecture.md` — this file
- [x] `characters/bargos_the_hutt.yaml` + `bargos_the_hutt.md` — Bargos NPC complete
- [x] Directory structure created: `src/showrunner/`, `config/`, `characters/`, `state/`, `tests/`
- [x] Python package stubs created with phase markers
- [x] `config/agents.yaml` — CrewAI agent definitions stub
- [x] `config/tasks.yaml` — CrewAI task definitions stub
- [x] `config/litellm.yaml` — LiteLLM routing stub (needs real IPs)
- [x] `requirements.txt` — dependency list stub
- [ ] Tom provides PC character YAML + MD (at least one, for Phase 4)
- [ ] Parse Genesys Core Rulebook into indexed sections (`swskin/rules/`)
  - `rules/index.md`, `rules/dice.md`, `rules/combat.md`, `rules/skills.md`
- [ ] Verify LiteLLM can reach llama.cpp on Alien and LM Studio on Sardinia

---

## Phase 1: DiceRoller (Critical Path)

Everything downstream depends on a working dice roller. Do this first.

- [ ] Implement `roll_pool()` in `src/showrunner/tools/dice_roller.py`
  - Face tables are already in the file; add random face selection
- [ ] Build and test: pool construction `build_pool(characteristic, skill_ranks, difficulty, boost, setback, upgrades)`
- [ ] Build and test: `DiceResult` symbol cancellation (S/F cancel, A/T cancel, Tr/De independent)
- [ ] Manual input parser: accept `2s 1a 1f` or `1tr 2a` notation, return `DiceResult`
- [ ] Unit tests for every die type (verify face table coverage)
- [ ] Unit tests for cancellation edge cases (exact tie, Tr+De in same pool)
- [ ] Unit tests for pool construction rule (max/min characteristic vs skill_ranks)

---

## Phase 2: CrewAI Scaffold

- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Implement agent classes in `src/showrunner/agents/` using `config/agents.yaml`
- [ ] Wire LiteLLM routing — verify each agent can make a test inference call
  - Alien endpoint test (Referee or Scribe makes a trivial call)
  - Sardinia endpoint test (World Runner or Actors makes a trivial call)
  - Gemini endpoint test (Narrator makes a trivial call)
- [ ] Implement `crew.py` — assemble CrewAI hierarchical Crew from agent + task configs
- [ ] Implement basic turn loop in `orchestrator.py` — message passing only, no game content
- [ ] Tool stubs wired: `consult_narrator()`, `ask_player()`, `roll_dice()`, `read_state()`, `write_state()`

---

## Phase 3: State Management

- [ ] `state_reader.py` — implement `load_scene_state()`, `load_party_stats()`, `load_character()`
- [ ] `state_writer.py` — implement `update_party_stats()`, `update_scene_state()`, `append_session_log()`
- [ ] Initial state loader: read character YAMLs, initialise `party_stats.yaml` and `scene_state.yaml` for a new session
- [ ] Scribe agent: write structured updates to state files after each resolved action
- [ ] `render_actor_prompt()` in `actors.py` — combine persona MD + YAML mechanical summary, sorted static-to-dynamic per `character_schema.md`
- [ ] Session log format: timestamped narrative entries in `state/session_log.md`

---

## Phase 4: MVP Scene — Bargos Mansion

Target: run the full Bargos mansion scene from *Debts to Pay* end-to-end.

Scene covers: arrival, audience with Bargos, the Gamorrean Rumble combat encounter.
Reference: `swskin/Game_masters_kit.pdf` Acts 1–2.

Phases 5 and 6 are **not required** for this phase. The Referee operates with the specific
rules and NPC stats for this scene baked inline — no `rules_lookup()` tool needed.

- [ ] Adventure scene format: `state/scene_[n].yaml` (location, NPCs present, triggers, read-aloud text)
- [ ] Convert Bargos mansion scenes (Acts 1–2) to YAML format
  - Include inline stats for Gamorrean guards (weapon, damage, skills) directly in scene YAML
- [ ] Narrator: load scene, decide beats, manage the Gamorrean arrival ticking clock
- [ ] World Runner: narrate scene descriptions and outcomes
- [ ] Actors: voice Bargos, Genko, C3-P9, Gamorreans — using `render_actor_prompt()`
- [ ] Referee: handle Vigilance check (spotting Gamorreans), Brawl/Melee combat checks
  - Referee system prompt includes the specific rules needed for this scene inline
  - `rules_lookup()` tool stub exists but is not wired; defer to Phase 5
- [ ] CLI: player turn prompt, `!` directive injection, manual dice input option
- [ ] Play through the scene; identify and fix issues

---

## Phase 5: Genesys Rules Parser (swskin)

Needed before Phase 7. Not blocking Phase 4.

The Referee's `rules_lookup()` tool is stubbed in Phase 2 but unimplemented. This phase
delivers the data it queries. Without it the Referee must have rules hard-coded per scene,
which becomes unmanageable across the full 15-room Gavos adventure.

- [ ] Script to extract sections from Genesys Core Rulebook PDF → `swskin/rules/`
- [ ] `rules/index.md` — section list with page references
- [ ] Priority sections: `rules/dice.md`, `rules/combat.md`, `rules/skills.md`, `rules/talents.md`
- [ ] Wire `rules_lookup()` tool in Referee agent — keyword search against indexed sections

---

## Phase 6: OggDude Data Ingestion (swskin)

Needed before Phase 7. Not blocking Phase 4.

Provides structured weapon, skill, talent, and career data. Without it, NPC and weapon stats
must be hand-transcribed into scene or character files — manageable for the MVP scene,
not for a full adventure.

- [ ] `tools/xml_to_md.py` — converts OggDude XML exports to structured Markdown
- [ ] Output: `swskin/data/weapons.md`, `skills.md`, `talents.md`, `careers.md`
- [ ] Validate Referee can look up a weapon stat (e.g., Gamorrean vibro-ax) from converted data

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
