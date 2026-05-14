# Architect TODO

Open decisions and phased work for the showrunner engine.
For the stable design record, see `architecture.md`.
For resolved decisions, see git log.

---

## Known Issues (from playthrough)

- [x] **Inline NPC stats missing from check identification** — addressed by programmer
  task 4.37. Inline NPCs get an optional flat stats block in the scene YAML (same shape
  as minion_groups). `_build_char_stats` extended to cover both. `render_inline_npc_prompt`
  replaces the bare `key_traits` string so inline NPCs enter the NPC wave with name,
  pronoun, role, and mechanical context.

- [x] **Ruling actor ID doesn't reliably match party_stats keys** — addressed by programmer
  task 4.38. `_build_actor_name_map` builds a lowercase display-name → char_id lookup at
  session start from all character sources. `_make_ruling_callback` normalises the actor
  string through this map before touching party_stats.

---

## Open Decisions

Items that have not yet been fully resolved. These need an answer before the relevant
implementation phase begins.

- [ ] **SR-driven beat advancement** — Replace (or supplement) the manual `[a / beat-id / Enter]`
  prompt with a Show Runner call that decides whether to advance after each turn. Four design
  questions to resolve before implementation:
  1. **Trigger placement** — which step in the turn loop runs the SR advance check? After Step 9
     (plan update) is the natural slot; confirm what context it receives (summaries log, results,
     last_actions, or all three).
  2. **What the SR judges against** — beats currently have a `trigger` field describing when the
     beat *starts*, but no `exit_condition`. Options: (a) SR infers from narrative context alone,
     (b) add an explicit `exit_condition` string to each beat YAML so the SR has a concrete target.
     Option (b) is more reliable but requires a schema addition and scene file updates.
  3. **Output format** — simple `ADVANCE` / `STAY`, or can the SR name a specific beat ID to
     allow non-linear jumps (e.g. skip `gamorrean_warning` if the ambush was pre-empted)?
  4. **Manual override** — keep the `[a / beat-id / Enter]` prompt as a debug escape hatch
     (perhaps only in `--verbose` mode), or remove it entirely once SR advance is trusted?

- [ ] **Context window pre-flight check** — Before each `call_llm()`, estimate token
  count of the assembled prompt (characters ÷ 4 is a reasonable approximation) and warn
  or abort if it would exceed the model's limit. Requires: (1) `max_context_tokens` field
  added to each agent entry in `agents.yaml`; (2) pre-flight check in `call_llm()` that
  reads that field and compares against estimated prompt size. See programmer_todo for
  the implementation task.

- [x] **Manual dice input format** — Ratified. Single-letter keys with counts; spaces
  tolerated. Letters: S=Success, A=Advantage, T=Triumph, F=Failure, H=Threat, D=Despair.
  Example: `S2A1T1` = 2 Successes, 1 Advantage, 1 Triumph. `S2 A1 T1` also valid.
  See game_loop.md Step 6 for the full spec.

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
