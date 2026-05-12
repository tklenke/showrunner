# Architect TODO: showrunner — AI Agent RPG Orchestration Engine

## System Architecture

### Agent Roster

| Agent | Model | Node | Responsibilities |
|-------|-------|------|-----------------|
| **Narrator** | Gemini | Cloud | GM brain: adventure state, scene beat decisions, ticking clocks, NPC knowledge tracking |
| **World Runner** | Llama 3.1 8B | Sardinia | GM voice: prose narration, atmosphere, scene descriptions |
| **Actors** | Llama 3.1 8B | Sardinia | NPC voices: live dialogue for Bargos, EV-8D3, Marv, etc. |
| **Referee** | Llama 3.2 3B | Alien | Rules engine: dice pool construction, skill check difficulty, combat validation |
| **Scribe** | Llama 3.2 3B | Alien | State keeper: writes session log and party stats after each resolved action |

Sardinia agents can call `consult_narrator()` to escalate uncertainty to Gemini.
Narrator can call `ask_player()` to surface preference questions to Tom in the CLI.
Tom can push unsolicited direction at any time using `!` prefix in the CLI.

### Hardware Nodes

#### Alien (Logic & Rule Hub)
- i7-6700, 16GB RAM, GTX 960 (2GB VRAM), Debian 12
- llama.cpp server, Llama 3.2 3B Instruct (10 GPU layers, 4096 ctx)
- Hosts: Referee, Scribe

#### Sardinia (Creative & Actor Hub)
- i9-9900k, 64GB RAM, RTX 2070 (8GB VRAM), Windows
- LM Studio (Developer Mode), Llama 3.1 8B Instruct
- Hosts: World Runner, Actors

#### Gemini (Narrative Hub)
- Gemini via Google AI Studio API
- Consulted at scene transitions and major decision points (not every turn)
- Hosts: Narrator

### Software Stack

- **Orchestration**: CrewAI (Hierarchical process, Narrator as manager)
- **Inference Bridge**: LiteLLM routing to local nodes and Gemini API
- **Interface**: CLI + VS Code initially
- **State Management**: Markdown/YAML files — human-readable audit trail

### State File Schema

| File | Format | Write Access | Description |
|------|--------|--------------|-------------|
| `state/session_log.md` | Markdown | Scribe only | Full narrative record of the session |
| `state/party_stats.yaml` | YAML | Scribe only | Current wounds, strain, credits, inventory |
| `state/scene_state.yaml` | YAML | Scribe only | Current location, active NPCs, ticking clock status |
| `state/draft.md` | Markdown | All agents | Pre-commit sandbox for agent negotiation before action is finalized |
| `world/characters/*.yaml` | YAML | Read-only | PC and NPC character sheets |

### Turn Loop

```
Narrator   → assess scene state, decide next beat
World Runner → narrate scene to player(s)
[if player's turn] → CLI prompt: "What does [character] do?"
[if AI character's turn] → Actor generates action
Referee    → determine if check needed; set difficulty; construct dice pool
DiceRoller → roll (automatic) or display pool + accept manual input (physical dice)
Referee    → interpret symbols; determine outcome
World Runner → narrate result
Scribe     → update state files
[loop]
```

### Character Sheet Format

YAML files in `world/characters/[name].yaml` (lives in swskin repo).
See `docs/plans/character_schema.md` for full schema.
`player: "human"` or `player: "ai"` controls who drives that character.

### Genesys Dice — Canonical Face Distribution

From Genesys Core Rulebook, Table I.1-2 (page 11):

| Die | Faces (1→last) |
|-----|----------------|
| Boost d6 | blank, blank, S, SA, AA, A |
| Setback d6 | blank, blank, F, F, T, T |
| Ability d8 | blank, S, S, SS, A, A, SA, AA |
| Difficulty d8 | blank, F, FF, T, T, T, TT, FT |
| Proficiency d12 | blank, S, S, SS, SS, A, SA, SA, SA, AA, AA, Tr |
| Challenge d12 | blank, F, F, FF, FF, T, T, FT, FT, TT, TT, De |

Symbols: S=Success, F=Failure, A=Advantage, T=Threat, Tr=Triumph, De=Despair

Pool construction rule: take MAX(characteristic, skill) Ability dice; upgrade MIN(characteristic, skill) of them to Proficiency dice.

Symbol cancellation: S cancels F (net determines pass/fail). A cancels T (net determines side effects). Tr counts as S for math but does not cancel De. De counts as F for math but does not cancel Tr.

---

## Repository Structure

```
showrunner/          ← this repo (engine, no copyrighted content)
  src/
    agents/          ← narrator.py, world_runner.py, actors.py, referee.py, scribe.py
    tools/           ← dice_roller.py, state_reader.py, state_writer.py, rules_lookup.py
    orchestrator.py  ← main CrewAI loop
    cli.py           ← player input/output interface
  config/
    litellm.yaml     ← model routing config
    crew.yaml        ← agent and task definitions
  state/             ← runtime state files (gitignored)
  docs/
    plans/
    references/      ← READ ONLY

swskin/              ← separate repo (world assets, copyrighted content)
  characters/        ← PC and NPC YAML sheets
  data/              ← converted OggDude markdown (weapons, talents, etc.)
  rules/             ← parsed Genesys rulebook sections
  adventure/         ← Debts to Pay in structured format
```

---

## Implementation Phases

### Phase 0: Pre-Implementation Setup

- [x] Architecture design finalized
- [ ] `docs/plans/character_schema.md` — document YAML schema for character files
- [ ] Tom provides `swskin/characters/[pc_name].yaml` for MVP character
- [ ] Parse Genesys Core Rulebook into indexed sections (rules/index.md, rules/dice.md, rules/combat.md, rules/skills.md)
- [ ] `config/litellm.yaml` — define model routes for Alien, Sardinia, Gemini
- [ ] Verify LiteLLM can reach llama.cpp on Alien and LM Studio on Sardinia

### Phase 1: DiceRoller (Critical Path — everything depends on this)

- [ ] `src/tools/dice_roller.py` — implement exact face tables from rulebook
- [ ] Pool builder: `build_pool(characteristic, skill_ranks, difficulty, boost, setback, upgrades)`
- [ ] Roller: returns raw symbol counts per die
- [ ] Interpreter: cancels symbols, returns `DiceResult` (net_successes, net_advantage, triumphs, despairs, pass/fail)
- [ ] Manual input mode: display pool description, parse `2s 1a 1f` or `1tr 2a` notation
- [ ] Unit tests for all dice types and cancellation logic

### Phase 2: CrewAI Scaffold

- [ ] Install and configure CrewAI + LiteLLM
- [ ] Agent definitions: Narrator (Gemini), World Runner (Sardinia), Actors (Sardinia), Referee (Alien), Scribe (Alien)
- [ ] Tool stubs: `consult_narrator()`, `ask_player()`, `read_state()`, `write_state()`, `roll_dice()`
- [ ] Verify each agent can make a simple inference call through LiteLLM to its assigned model
- [ ] Basic turn loop in `orchestrator.py` — no content yet, just message passing

### Phase 3: State Management

- [ ] State file reader/writer (`src/tools/state_reader.py`, `state_writer.py`)
- [ ] Initial state loader: reads character YAML, initializes `party_stats.yaml` and `scene_state.yaml`
- [ ] Scribe agent: writes structured updates to state files after each resolved action
- [ ] Session log format: timestamped narrative entries in `state/session_log.md`

### Phase 4: MVP Scene — Bargos Mansion

Target: run the full Bargos mansion scene from "Debts to Pay" end-to-end.
Includes: arrival, audience with Bargos, the Gamorrean Rumble combat encounter.

- [ ] Adventure scene format: `swskin/adventure/scene_[n].yaml` (location, NPCs present, triggers, read-aloud text)
- [ ] Convert Bargos mansion scenes to YAML format
- [ ] Narrator: load scene, decide beats, manage the Gamorrean Rumble ticking arrival
- [ ] World Runner: narrate scene descriptions and outcomes
- [ ] Actors: voice Bargos, Genko, C3-P9, Gamorreans
- [ ] Referee: handle Vigilance check (spotting Gamorreans), Brawl/Melee combat checks
- [ ] CLI: player turn prompt, `!` directive injection, manual dice input option
- [ ] Play through the scene; identify and fix issues

### Phase 5: Genesys Rules Parser (swskin)

- [ ] Script to extract sections from Genesys Core Rulebook PDF into `swskin/rules/`
- [ ] `rules/index.md` — section list with page references
- [ ] Priority sections: `rules/dice.md`, `rules/combat.md`, `rules/skills.md`, `rules/talents.md`
- [ ] Referee `rules_lookup()` tool: retrieves relevant section by keyword

### Phase 6: OggDude Data Ingestion (swskin)

- [ ] Script: `tools/xml_to_md.py` — converts OggDude XML files to structured Markdown
- [ ] Output: `swskin/data/weapons.md`, `skills.md`, `talents.md`, `careers.md`
- [ ] Validate Referee can look up a weapon stat (e.g., Gamorrean vibro-ax) from the converted data

### Phase 7: Full Gavos Adventure

- [ ] Convert all 15 Gavos mine rooms to scene YAML
- [ ] Ticking clock mechanic: storm barrier generator countdown in `scene_state.yaml`
- [ ] Lookout vehicle chase (space combat variant)
- [ ] Way station encounter and miner rescue
- [ ] Final negotiation with Bargos (Charm check resolution)

### Phase 8: Polish and Extensibility

- [ ] World skin loader: `config/world.yaml` points to any swskin-compatible repo
- [ ] Document the world skin schema so other skins can be built
- [ ] Session resume: save/restore `state/` between sessions
- [ ] Consider richer CLI output (color, formatted stat blocks)
