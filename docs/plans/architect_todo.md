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

**NOTE FROM PROGRAMMER (2026-05-13): Small models (3B/8B) cannot reliably use tools in CrewAI's ReAct loop**

Observed during Phase 4 playthrough: any agent running on alien (3B) or sardinia (8B) that
is given tools will crash with `ValueError: Invalid response from LLM call - None or empty`
or will emit JSON Schema syntax as its "final answer" instead of calling the tool.

Root cause: CrewAI's ReAct loop injects tool schemas and thought/action/observation scaffolding
into the prompt. Small models either overflow their context window under this added load, or
generate output that doesn't conform to the expected format, causing CrewAI to reject the
response entirely after retries.

**Fix applied so far:** removed all tools from NPC Voice Actor (`tools=[]`). Same fix
needed for the Referee (`roll_dice`, `read_state`, `consult_show_runner` — all three).

**Architectural decision needed: Dice rolling without a tool-capable Referee**

The Referee is the rules engine; real dice randomness is part of that. Three options:

- **Option A — Strip tools; Referee narrates a fictional result.** Simple. Zero randomness.
  Good enough for early playtesting but undermines the rules engine role.

- **Option B — Roll in the orchestrator; Referee interprets.** Orchestrator calls `roll_pool()`
  directly using the check spec, passes the result string to the Referee task description.
  Referee narrates the outcome without needing to call tools. Real randomness; no ReAct loop.
  Requires the Show Runner review output to include characteristic *values* (e.g. "Agility 3"),
  not just names, so the orchestrator can build the correct dice pool.

- **Option C — Move Referee to a larger/cloud model.** Gemini or a model with reliable tool
  use handles the ReAct loop. Adds latency and cost per combat roll. Avoids prompt surgery.

**Current status:** Referee still has tools (`referee.py:create_referee`); game crashes on
first check. See "Resolved Decisions: Resolution Pipeline" below for the chosen design.

---

## Resolved Decisions

### Resolution Pipeline: Five-Step File-Mediated Design (2026-05-13)

**Context:** The Referee agent (alien 3B) crashes when given tools in CrewAI's ReAct loop.
The root problem is not just the Referee — the pattern of handing a small model a large
undifferentiated context and expecting structured output is fragile. The solution is a
decomposed pipeline where each small model gets one focused job and the orchestrator manages
data flow between steps via intermediate files.

Additionally, the Show Runner review at the end of Phase 2 was doing two jobs at once:
summarising what happened and identifying required checks. Separating these makes both jobs
smaller and more reliable.

**Decision: Remove Show Runner review from Phase 2. Replace Phase 3 with a five-step pipeline.**

---

#### Pipeline steps

**3a — Action summaries** (alien 3B, one task per character that acted)
- Input: one character's action text (from NPC/AI PC outputs + player action)
- Output: 1–2 sentence plain-language summary of what that character did
- No tools. No stats. No rules reasoning.
- Orchestrator collects all outputs and writes `logs/turn_{turn_ts}_{beat}_summaries.txt`

**3b — Check identification** (sardinia 8B / Show Runner, single task)
- Input: all summaries from 3a + character stats from YAML for each character that acted
  (characteristic values and skill ranks, passed as structured text by the orchestrator)
- Output: formatted check list, one line per required check:
  ```
  1. Z-4P0 | Negotiation | Presence 2 | Skill 1 | Opposed vs Bargos Cool 3 | notes
  ```
  Or `NO_CHECKS`. Characteristic and skill rank values must be in the output so the
  orchestrator can build a real dice pool without further lookups.
- Orchestrator writes `logs/turn_{turn_ts}_{beat}_checks.txt`
- **This replaces the Show Runner review that previously ended Phase 2.**

**3c — Dice rolling + rulings** (orchestrator Python + sardinia 8B, one task per check)
- Orchestrator reads `turn_checks.txt`, parses each line, builds dice pool from the
  embedded stat values, calls `roll_pool()` directly in Python.
- Each check + its pre-computed roll result is passed to a sardinia task:
  ```
  Check: Z-4P0 | Negotiation | vs Bargos Cool | ...
  Roll result: Roll passed: net +2 successes, +1 advantage
  ```
- Task output: ruling and mechanical consequence (wounds dealt, check passed/failed, etc.)
- No tools required on the sardinia task — dice are already rolled.
- Orchestrator collects all rulings and writes `logs/turn_{turn_ts}_{beat}_results.txt`

**3d — Resolution narrative** (sardinia 8B now / Gemini eventually, single task)
- Input: all three files (summaries, checks, results) read by the orchestrator and
  passed as task description context.
- Output: player-facing narrative prose describing what just happened.
- Printed directly to terminal. Not written to a log.
- This is a Show Runner task using the show_runner agent config.

**3e — Last action extraction** (sardinia 8B / Narrator, one task per active character)
- Input: same three files + character name
- Output: a single sentence capturing that character's last action for the next turn's
  context (replaces the raw `last_actions` dict currently assembled from output.raw strings)
- Orchestrator writes extracted values to `scene_state.yaml` under `last_actions`.

---

#### File naming

Turn files are named: `logs/turn_{turn_timestamp}_{beat_id}_{type}.txt`
where `turn_timestamp` is a `datetime.now()` taken at the top of each turn iteration
(distinct from the session timestamp). `type` is `summaries`, `checks`, or `results`.

Files persist — one set per turn, never overwritten. Useful for debugging and as a
natural audit trail.

---

#### Character stats access for 3b

`load_scene_characters()` currently returns `{id: rendered_prompt_str}`. Step 3b needs
raw stat values (characteristic scores, skill ranks) that are buried in that string.
Add a companion function `load_scene_yamls(scene, characters_dir) -> dict[str, dict]`
that returns `{id: raw_yaml_dict}` for the same character set. The orchestrator calls
this alongside `load_scene_characters()` and builds the stats block for the 3b task
description from the raw YAML.

---

#### What this removes

- `build_resolution_crew()` in `crew.py` — replaced by the new pipeline.
- Show Runner review task from `build_pc_crew()` — moved to 3b.
- `_parse_check_specs()` in `orchestrator.py` — replaced by file-based parsing.
- Tools from `create_referee()` — Referee agent is retired; sardinia handles 3c rulings.

---

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
