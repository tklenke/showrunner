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

## Design Decision: Prompt Architecture and Directory Restructure

**Decision date:** 2026-05-13  
**Status:** Decided — implementation tracked in programmer_todo.md tasks 4.30–4.32

### Prompt layering

Every `call_llm()` assembles a prompt from four layers in order:

| Layer | What it is | Lifetime | Source |
|---|---|---|---|
| **Node** | World context sized for the model | Per model tier | `skin/world.yaml` |
| **Agent** | Role definition (who the agent is) | Per session | `config/prompts/agent_*.md` |
| **Task** | What this specific call is asking for | Per function call | `config/prompts/task_*.md` |
| **Dynamic** | Current game state (beat, last actions, stats) | Per turn | Built programmatically |

System prompt = Node + Agent  
User message = Task + Dynamic

#### Node chunk — `skin/world.yaml`

The node chunk is world context: setting, tone, factions, genre. It is the first thing
every agent reads. Because models vary drastically in context budget, `world.yaml` carries
three versions keyed by model tier:

```yaml
world:
  name: "Star Wars: Edge of the Empire"
  description:
    large: |
      [Full rich description — several paragraphs. For Gemini and other large-context models.]
    medium: |
      [Condensed — one to two paragraphs. For 8B models (Sardinia).]
    small: |
      [Minimal — 2–3 sentences. For 3B models (Alien).]
```

The orchestrator selects tier based on the model alias for that agent call.
Tier mapping lives in `config/agents.yaml` — add a `context_tier` field
(`large` / `medium` / `small`) per agent entry.

#### Agent chunk — `config/prompts/agent_*.md`

Role identity files, one per agent. Replace the inline `role`/`goal`/`backstory` fields
in `agents.yaml` (those become pointers: `prompt_file: prompts/agent_show_runner.md`).

Files: `agent_show_runner.md`, `agent_narrator.md`, `agent_actors.md`

#### Task chunk — `config/prompts/task_*.md`

One file per runner function that calls `call_llm()`. Replaces inline f-string
task descriptions in `runner.py`. The programmatic parts (actor name, roll result,
stat values) are still interpolated by Python — the file contains the static frame.

Files (one per step): `task_run_checks.md`, `task_run_rulings.md`,
`task_run_narrative.md`, `task_run_summaries.md`, `task_run_last_actions.md`,
`task_run_plan_update.md`, `task_run_beat_opener.md`

---

### Directory restructure

#### `skin/` — all adventure content (read-only during play)

Rename `skin/` → `skin/`. Consolidate characters and scenes here.
All references to `skin` in docs, code, and config must be updated.

```
skin/
  world.yaml              ← NEW: world context at three model-tier sizes
  characters/             ← MOVED from characters/
    bargos_the_hutt.yaml
    kaelen_sunara.yaml
    Z-4P0.yaml
  scenes/                 ← MOVED from state/ (startup YAMLs only)
    scene_0.yaml
    scene_1.yaml
  rules/                  ← future Phase 5
  data/                   ← future Phase 6
```

#### `state/` — dynamic only (written during play)

Remove scene YAMLs and character YAMLs. Retain only files the engine writes:

```
state/
  scene_state.yaml
  party_stats.yaml
  session_log.md
```

#### `config/` — system infrastructure

Add `prompts/` subdirectory. Agent YAML entries gain `context_tier` and `prompt_file`.

```
config/
  agents.yaml
  litellm.yaml
  prompts/
    agent_show_runner.md
    agent_narrator.md
    agent_actors.md
    task_run_checks.md
    task_run_rulings.md
    task_run_narrative.md
    task_run_summaries.md
    task_run_last_actions.md
    task_run_plan_update.md
    task_run_beat_opener.md
```

#### `characters/` — deleted after migration

Currently at project root. Contents move to `skin/characters/`. Delete after.

---

---

## Phase 0: Pre-Implementation Setup

- [ ] Parse Genesys Core Rulebook into indexed sections (`skin/rules/`)
  - `rules/index.md`, `rules/dice.md`, `rules/combat.md`, `rules/skills.md`
- [ ] Verify LiteLLM can reach llama.cpp on Alien and LM Studio on Sardinia

---

## Phase 4: MVP Scene — Bargos Mansion

Prompt architecture (tasks 4.29–4.32) is Phase 4 work — required to fix the output
issues found during first playthrough. End-to-end playthrough (4.33) is the
phase-complete gate.

Target: run the full Bargos mansion scene from *Debts to Pay* end-to-end.

Scene covers: arrival, audience with Bargos, the Gamorrean Rumble combat encounter.
Reference: `skin/Game_masters_kit.pdf` Acts 1–2.

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

## Phase 5: Genesys Rules Parser (skin)

Needed before Phase 7. Not blocking Phase 4.

The Show Runner's `rules_lookup()` tool is stubbed but unimplemented. This phase
delivers the data it queries. Without it the Show Runner must have rules hard-coded per
scene, which becomes unmanageable across the full 15-room Gavos adventure.

- [ ] Script to extract sections from Genesys Core Rulebook PDF → `skin/rules/`
- [ ] `rules/index.md` — section list with page references
- [ ] Priority sections: `rules/dice.md`, `rules/combat.md`, `rules/skills.md`, `rules/talents.md`
- [ ] Wire `rules_lookup()` tool in Show Runner agent — keyword search against indexed sections

---

## Phase 6: OggDude Data Ingestion (skin)

Needed before Phase 7. Not blocking Phase 4.

Provides structured weapon, skill, talent, and career data. Without it, NPC and weapon stats
must be hand-transcribed into scene or character files — manageable for the MVP scene,
not for a full adventure.

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
