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
    agents/          ← narrator, world_runner, actors, referee, scribe
    tools/           ← dice_roller, state_reader, state_writer
    crew.py          ← CrewAI crew assembly
    orchestrator.py  ← turn loop
    main.py          ← CLI entry point
  config/
    agents.yaml      ← CrewAI agent definitions
    tasks.yaml       ← CrewAI task definitions
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

| Agent | Model | Node | Role |
|-------|-------|------|------|
| **Narrator** | Gemini 2.0 Flash | Cloud | GM brain: adventure state, scene beat decisions, ticking clocks, NPC knowledge |
| **World Runner** | Llama 3.1 8B | Sardinia | GM voice: prose narration, atmosphere, scene descriptions |
| **Actors** | Llama 3.1 8B | Sardinia | NPC voices: live dialogue, physical action, character decisions |
| **Referee** | Llama 3.2 3B | Alien | Rules engine: dice pool construction, skill check difficulty, combat validation |
| **Scribe** | Llama 3.2 3B | Alien | State keeper: session log and party stats after each resolved action |

CrewAI hierarchical process with Narrator as the manager agent.

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
| Orchestration | CrewAI (hierarchical process) |
| Inference routing | LiteLLM → local OpenAI-compatible endpoints + Gemini API |
| Interface | CLI (primary), VS Code terminal |
| State storage | YAML + Markdown files (human-readable, git-tracked) |
| Language | Python 3.11+ |

---

## Communication Patterns

**Hierarchical delegation** — Narrator (Gemini) is the CrewAI manager. It delegates tasks
to World Runner, Actors, Referee, and Scribe. Those agents do not call each other directly.

**Escalation** — Sardinia and Alien agents call `consult_narrator()` when they hit genuine
uncertainty (ambiguous rules, plot-critical decisions). This invokes a Gemini call. Used
sparingly to control API cost.

**Player injection** — Tom can push direction at any time using a `!` prefix in the CLI
(`! have Bargos look more nervous`). This is injected into the Narrator's context before
the next beat decision.

**Player turn** — When it is a human character's turn, the CLI prompts: `What does [name]
do?` The response is fed to the Referee (if a check is triggered) and the World Runner
(for narration).

**Narrator ↔ Player** — Narrator calls `ask_player()` when a preference question surfaces
(e.g., "do you want to avoid this fight or escalate?").

---

## Turn Loop

```
Narrator   → assess scene state → decide next beat
World Runner → narrate scene to player
  ↓
[if player's turn]
  CLI: "What does [character] do?"
  player inputs action (optionally with manual dice result)

[if AI character's turn]
  Actors: generate action from rendered character prompt

Referee    → is a check needed? → set difficulty → construct dice pool
DiceRoller → auto-roll OR display pool + accept manual symbol input
Referee    → interpret symbols → determine outcome

World Runner → narrate result
Scribe     → update state files
  ↓
[loop]
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
Scribe is the only agent with write access.

| File | Format | Description |
|------|--------|-------------|
| `session_log.md` | Markdown | Full timestamped narrative record |
| `party_stats.yaml` | YAML | Current wounds, strain, credits, inventory for all PCs |
| `scene_state.yaml` | YAML | Location, active NPCs, ticking clock status, character scene plans |
| `draft.md` | Markdown | Pre-commit sandbox for agent negotiation |

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
