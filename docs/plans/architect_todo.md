# Architect TODO

Open decisions and phased work for the showrunner engine.
For the stable design record, see `architecture.md`.

---

## Design Notes

**NOTE FROM PROGRAMMER (2026-05-12): LiteLLM callbacks are not viable for prompt logging with CrewAI**

Root cause discovered during Phase 4 playthrough debugging:

CrewAI's `Agent.execute_task()` (in `crewai/agent/core.py`) assigns
`executor.callbacks = [TokenCalcHandler(self._token_process)]` on every agent call.
`StepExecutor` then calls `LLM.call(callbacks=[TokenCalcHandler(...)])`.
Inside `LLM.call()`, any non-empty `callbacks` list triggers
`LLM.set_callbacks(callbacks)` which does `litellm.callbacks = [TokenCalcHandler(...)]`,
completely overwriting any logger we registered. This fires on every model call,
so re-registering after `build_crew()` only helps until the first agent executes.

**Fix implemented**: replaced `litellm.CustomLogger` + `litellm.callbacks` with a
`BaseEventListener` subclass that subscribes to CrewAI's own event bus
(`LLMCallCompletedEvent`). The event contains `model`, `messages`, and `response`,
giving us the same data without fighting CrewAI's callback management.

**Architectural implication**: `architecture.md` describes the instrumentation as
"LiteLLM prompt/response logging via CustomLogger callback" — this should be updated
to reflect that prompt logging uses CrewAI's event bus, not LiteLLM callbacks.

---

## Resolved Decisions

### Turn Loop: Two-Phase Kickoff + Per-Check Referee Isolation (2026-05-13)

**Context:** After implementing the sequential crew, we observed that the Referee was
guessing what checks were needed from the beat plan alone. Post-action state — what the
NPCs actually did, what the player did, what Kaelen did — was not visible to the
Referee in a structured way. The beat plan is intent; the action outputs are reality.

**Options considered:**

**Option A — Show Runner review → single Referee task.**
Show Runner reads all NPC/PC outputs, produces a structured check list, hands the whole
list to one Referee task that resolves all checks in a single response. Simple, no
dynamic task creation. Weakness: less per-check isolation; harder for a small model to
juggle multiple checks cleanly.

**Option B — Three kickoffs per turn with dynamic Referee tasks. (CHOSEN)**
1. **NPC wave kickoff:** Show Runner (beat plan) → Narrator → NPCs chained by context.
2. **PC wave kickoff:** Player input → Kaelen (sees NPC outputs + player action) →
   Show Runner review (sees all outputs, emits structured check list). Orchestrator
   parses the check list.
3. **Resolution kickoff:** N Referee tasks built dynamically (one per check, each
   receives only its check), then Scribe.

**Why Option B:** Per-check isolation gives the Referee (a small model) one clear job
per invocation. It also matches how the game actually works — each roll is a discrete
event, not a batch. The third kickoff is small and the overhead is acceptable. Option A
is faster to implement but bets on the Referee handling multiple checks cleanly, which
the 3B model is unlikely to do reliably as combat grows in complexity.

**Show Runner review output format:**
```
CHECKS:
1. {actor} | {skill} | {characteristic} | {difficulty} | {notes}
CHECKS_END
```
If no checks needed: a single line `NO_CHECKS`. The orchestrator splits on `|`, builds
one Referee task per line. The Referee receives its check spec in the task description
and outputs: dice pool, roll result (auto-rolled or prompted), and outcome ruling.

**Ordering within the turn:**
- NPCs act in scene YAML order (status hierarchy: `npcs_present` first, `inline_npcs`
  second). Each NPC sees all prior NPC outputs via chained task context.
- Player inputs a single free-form action. Can include direction to Kaelen embedded
  in natural language ("I yell to Kae, 'cover the door' then I approach Bargos").
- Kaelen (AI party member, `player: "ai"`) sees all NPC outputs + player action text.
- Show Runner review sees everything (NPC outputs + Kaelen + player action).
- Referee handles each check in isolation.
- Scribe records outcomes.

**Characters filtered by `player` field:**
- No `player` field (or `player: null`) → pure NPC → NPC wave
- `player: "ai"` → AI party member → PC wave (Kaelen)
- `player: "human"` → human player → prompted directly (Z-4P0)

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

---

## Phase 0: Pre-Implementation Setup

- [ ] Tom provides PC character YAML + MD (at least one, for Phase 4)
- [ ] Parse Genesys Core Rulebook into indexed sections (`swskin/rules/`)
  - `rules/index.md`, `rules/dice.md`, `rules/combat.md`, `rules/skills.md`
- [ ] Verify LiteLLM can reach llama.cpp on Alien and LM Studio on Sardinia

---

## Phase 4: MVP Scene — Bargos Mansion

Target: run the full Bargos mansion scene from *Debts to Pay* end-to-end.

Scene covers: arrival, audience with Bargos, the Gamorrean Rumble combat encounter.
Reference: `swskin/Game_masters_kit.pdf` Acts 1–2.

Phases 5 and 6 are **not required** for this phase. The Referee operates with the specific
rules and NPC stats for this scene baked inline — no `rules_lookup()` tool needed.

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
