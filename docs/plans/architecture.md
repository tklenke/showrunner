# showrunner — System Architecture

This document describes the design of the showrunner engine. It is a reference, not a
todo list. For open decisions and phased work, see `architect_todo.md`.

---

## Purpose

showrunner is an AI agent orchestration engine for tabletop RPG sessions. It coordinates
multiple language models — running locally and in the cloud — to handle the distinct roles
of a tabletop game: narrator, world builder, character voice actor, rules referee, and
state keeper.

The initial world skin targets the Genesys / Star Wars FFG system. The engine is designed
to be skin-agnostic; world-specific assets live in a separate repo.

---

## Repository Layout

Two repos, kept separate from day one (copyright and content concerns):

```
showrunner/          ← this repo: engine, config, runtime state, character files
  src/showrunner/    ← Python package
    agents/          ← show_runner, narrator, actors, referee, scribe
    tools/           ← dice_roller, state_reader, state_writer
    llm.py           ← call_llm(), build_system_prompt(), prompt logging
    runner.py        ← phase runners: NPC/PC waves, resolution pipeline
    config.py        ← agent config loading, litellm settings
    instrumentation.py ← session/prompt log paths
    orchestrator.py  ← turn loop
    main.py          ← CLI entry point
  config/
    agents.yaml      ← agent definitions (role, goal, backstory, model)
    litellm.yaml     ← model routing (Alien, Sardinia, Gemini)
  characters/        ← PC and NPC character files (YAML + MD pairs)
  state/             ← runtime state files, tracked in git
  tests/
  docs/
    plans/           ← architecture, todo docs (this file lives here)
    references/      ← READ ONLY (rulebooks, source PDFs)

swskin/              ← separate repo: raw world assets, copyrighted source material
  characters/        ← OggDude exports, raw XML/MD (source only, not runtime)
  data/              ← converted weapon/skill/talent/career data
  rules/             ← parsed Genesys rulebook sections
  adventure/         ← Debts to Pay in structured format
```

Runtime state files and character sheets live in `showrunner/`, not `swskin/`.
`swskin/` is the raw asset library; scripts in `showrunner/` consume and transform it.

---

## Agent Roster

| Agent | Config Key | Model | Node | Role |
|-------|-----------|-------|------|------|
| **Show Runner** | `show_runner` | Llama 3.1 8B | Sardinia | GM brain: beat decisions, check identification, dice rulings, resolution narrative |
| **Narrator** | `narrator` | Llama 3.1 8B | Sardinia | GM voice: prose narration, last-action extraction |
| **Actors** | `actors` | Llama 3.1 8B | Sardinia | NPC and AI PC dialogue, physical actions, action summaries |
| **Scribe** | `scribe` | Llama 3.2 3B | Alien | State keeper: one-sentence session log entry per turn |

Gemini (gemini-2.5-flash) is configured in `config/litellm.yaml` but not currently assigned to an agent.
The `referee` config exists in `config/agents.yaml` but is not called by the current pipeline —
check identification and rulings are handled by Show Runner via `run_check_phase()` and `run_ruling_phase()`.

---

## Hardware Nodes

### Alien (Rules Hub)
- i7-6700, 16 GB RAM, GTX 960 (2 GB VRAM), Debian 12
- llama.cpp server, Llama 3.2 3B Instruct (10 GPU layers, 4096 ctx)
- Hosts: Referee, Scribe

### Sardinia (Creative Hub)
- i9-9900k, 64 GB RAM, RTX 2070 (8 GB VRAM), Windows
- LM Studio (Developer Mode), Llama 3.1 8B Instruct
- Hosts: World Runner, Actors

### Gemini (Narrative Hub)
- Google AI Studio API (Gemini 2.0 Flash)
- Consulted at scene transitions and major decisions — not every turn
- Hosts: Narrator

---

## Software Stack

| Layer | Technology |
|-------|-----------|
| Orchestration | `runner.py` — direct `litellm.completion` calls via `llm.py` |
| Inference routing | LiteLLM → local OpenAI-compatible endpoints + Gemini API |
| Interface | CLI (primary), VS Code terminal |
| State storage | YAML + Markdown files (human-readable, git-tracked) |
| Language | Python 3.11+ |

---

## Communication Patterns

**Three-phase turn loop** — Each turn runs three phases sequentially. Outputs from earlier
phases flow forward as inputs to later phases via the orchestrator; no agent calls another
directly.

**Phase 1 — NPC Wave** — Show Runner receives scene state and produces a beat plan. Narrator
receives the beat plan and produces read-aloud narration. Each NPC (in scene order) receives
the beat plan and all prior NPC outputs, then voices its dialogue and actions.

**Phase 2 — PC Wave** — Collected after player CLI input. Each AI PC receives the assembled
NPC wave text and the player's action, then responds. Human PCs act via CLI prompt only.

**Phase 3 — Resolution Pipeline** — Five orchestrator-driven steps: action summaries (3a) →
check identification (3b) → Python dice rolling + LLM rulings (3c) → resolution narrative
(3d) → last-action extraction (3e). Intermediate files (`logs/turn_{ts}_{beat}_{type}.txt`)
serve as both debug trail and inter-step context.

**Player injection** — Tom can push direction using a `!` prefix in the CLI
(`! have Bargos look more nervous`). Injected into the Show Runner's context before the
next beat decision. Planned but not yet implemented.

---

## Narrative Hierarchy

The engine organises play into four nested levels:

| Level | Definition | Example |
|-------|-----------|---------|
| **Session** | One continuous play session from startup to quit | An evening playing *Debts to Pay* |
| **Scene** | A self-contained event at a location, loaded from `state/scene_N.yaml` | The Bargos mansion visit |
| **Beat** | A dramatic sub-unit within a scene with a specific purpose and trigger | The Gamorrean guards burst in |
| **Turn** | One `crew.kickoff()` — Narrator assesses, agents act, Referee resolves, Scribe records | One round of combat |

A beat may take **multiple turns** to resolve. The `gamorrean_rumble` beat, for example, spans
as many turns as it takes to defeat all six Gamorrean guards. The beat does not advance until
its exit condition is met. A simpler beat like `summons` might resolve in a single turn.

The Narrator is responsible for recognising when a beat is complete and what the next beat
should be. In the current Phase 4 implementation the human player advances beats manually
via the CLI; automatic beat progression by the Narrator is a future milestone.

---

## Turn Loop

```
while True:
    [load scene_state.yaml: current_beat, last_actions, party_stats]

    ── Phase 1: NPC Wave ─────────────────────────────────────────────
    Show Runner  → scene state + last_actions → beat plan
    Narrator     → beat plan → narration (printed to player)
    NPCs in order→ beat plan + all prior NPC outputs → dialogue (printed)

    ── Player Input ──────────────────────────────────────────────────
    CLI: "What do you and your companions do?"

    ── Phase 2: PC Wave ──────────────────────────────────────────────
    AI PCs in order → npc_wave_text + player action → response (printed)

    ── Phase 3: Resolution Pipeline ──────────────────────────────────
    3a  Actors      → 1 call per actor → 1–2 sentence summary
                    → logs/turn_{ts}_{beat}_summaries.txt
    3b  Show Runner → summaries + character stats → check list or NO_CHECKS
                    → logs/turn_{ts}_{beat}_checks.txt; parsed into specs
    3c  Python      → roll_pool() per spec; result embedded in spec
        Show Runner → 1 call per spec → ruling (each call sees prior rulings)
                    → logs/turn_{ts}_{beat}_results.txt
    3d  Show Runner → summaries + checks + results → narrative (printed)
    3e  Narrator    → 1 call per actor → last-action sentence

    ── State Writes ──────────────────────────────────────────────────
    Orchestrator  → scene_state.yaml: last_actions updated
    Scribe        → 1 call → one-sentence entry → appended to state/session_log.md

    ── Beat Advancement ──────────────────────────────────────────────
    CLI: [Enter] stay  |  [a] advance  |  [beat ID] jump  |  [q] quit
```

---

## Dice System

### Physical Dice Option

The player can roll real dice and enter the results. The CLI displays the pool description
(`2 Proficiency, 1 Ability, 2 Difficulty`) and accepts symbol notation:

```
> 2s 1a 1f 1t
```

Or triumph/despair shorthand: `1tr`, `1de`.

### Automatic Rolling

`dice_roller.py` implements the exact face tables from Genesys Core Rulebook Table I.1-2
(page 11). Random face selection; returns a `DiceResult`.

### Die Types and Faces

| Die | Sides | Symbols |
|-----|-------|---------|
| Boost (blue d6) | 6 | blank×2, S, SA, AA, A |
| Setback (black d6) | 6 | blank×2, F×2, T×2 |
| Ability (green d8) | 8 | blank, S×2, SS, A×2, SA, AA |
| Difficulty (purple d8) | 8 | blank, F, FF, T×3, TT, FT |
| Proficiency (yellow d12) | 12 | blank, S×2, SS×2, A, SA×3, AA×2, Tr |
| Challenge (red d12) | 12 | blank, F×2, FF×2, T×2, FT×2, TT×2, De |

S=Success, F=Failure, A=Advantage, T=Threat, Tr=Triumph, De=Despair

### Symbol Cancellation

- S cancels F; net determines pass/fail
- A cancels T; net determines side effects
- Tr counts as S but does not cancel De
- De counts as F but does not cancel Tr

### Pool Construction

```
ability_dice    = max(characteristic, skill_ranks)
proficiency_dice = min(characteristic, skill_ranks)
```

Difficulty dice are added per check difficulty level. Boost/Setback from situational
modifiers. Some talents upgrade Ability → Proficiency.

---

## Character System

Each character has two files in `characters/`:

| File | Purpose | Volatility |
|------|---------|-----------|
| `[name].yaml` | Mechanical stats, skills, equipment, status | Partly volatile (status section changes in play) |
| `[name].md` | Persona: backstory, voice, personality, scene notes | Static — rarely changes |

`player: "human"` in the YAML = Tom drives this character via CLI.
`player: "ai"` = Actors agent drives this character.

See `docs/plans/character_schema.md` for the full YAML schema.

### render_actor_prompt

A deterministic Python function (no LLM call). Combines the persona MD and the YAML
mechanical summary into the full system prompt for the Actors agent.

**Sort order — most static to least static** (for prompt cache efficiency):

1. Name, species, career (identity — never changes)
2. Persona file content (personality, voice, backstory, relationships — static)
3. Characteristics (change only with rare advancement)
4. Skills with descriptors (change only when XP is spent)
5. Talents (same cadence as skills)
6. Base derived stats (wound/strain thresholds, soak, defense)
7. Equipment (changes during play)
8. Credits (changes frequently)
9. Current scene plan (from `scene_state.yaml`; stable across several turns)
10. Active critical injuries (acquired in play)
11. Current wounds / strain (most volatile; can change every round)

---

## State Files

All state files live in `showrunner/state/`, tracked in git.
The orchestrator handles all state writes directly. The Scribe produces a one-sentence log
entry as a string; the orchestrator appends it to `state/session_log.md`.

| File | Format | Description |
|------|--------|-------------|
| `session_log.md` | Markdown | Full narrative record; one entry per turn appended by the orchestrator |
| `party_stats.yaml` | YAML | Current wounds, strain, credits, inventory for all PCs |
| `scene_state.yaml` | YAML | Location, active NPCs, ticking clock status, last_actions, character scene plans |

---

## Design Principles

**Skin-agnostic engine** — showrunner knows nothing about Star Wars. World assets (weapons,
NPCs, adventure text, rules) are loaded from swskin at startup. The engine handles
orchestration, state management, and the turn loop.

**Human-readable state** — All state is YAML and Markdown. A human can read and edit the
session log, fix a wrong wound count, or inject a narrative note between sessions without
touching code.

**Cache-aware prompt design** — Stable content (identity, persona, stats) is placed at the
top of every agent prompt so it sits in the LLM's prompt cache across turns. Volatile
content (wounds, active injuries) goes at the bottom.

**Local-first** — The creative and rules work runs on hardware Tom owns. Gemini is used
only at scene transitions and decision escalations, not per-turn.

**Physical dice respected** — The system is designed to accept manual dice input from the
start, not as an afterthought. Rolling real dice at a table is part of the experience.
