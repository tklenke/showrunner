# Architect TODO: Modular RPG Engine

## System Architecture

### Hardware Nodes

#### Node: Alien (Logic & Rule Hub)
- **Hardware**: i7-6700, 16GB RAM, GTX 960 (2GB VRAM)
- **Inference**: llama.cpp server (native Debian 12)
- **Model**: Llama 3.2 3B Instruct (10 GPU layers, 4096 ctx, ~1.5GB VRAM)
- **Roles**:
  - **The Referee**: Validates Genesys dice math and rule legality using `SYSTEM.md`
  - **The Scribe**: Formats and appends turn results to `SESSION_LOG.md` and `PARTY_STATS.md`

#### Node: Sardinia (Creative & Actor Hub)
- **Hardware**: i9-9900k, 64GB RAM, RTX 2070 (8GB VRAM)
- **Inference**: LM Studio (Developer Mode) or native Windows Ollama
- **Primary Model**: Llama 3.1 8B Instruct
- **Alt Model**: DeepSeek-R1-Distill-Qwen-1.5B Q8_0 (high-speed testing)
- **Roles**:
  - **World Runner**: Generates cinematic environment descriptions
  - **Actors**: Plays NPCs and AI Players using Character Cards

#### Node: Architect (Online Narrative Hub)
- **Model**: Gemini 1.5 Pro (via Google AI Studio)
- **Role**: Long-term memory, plot-arc coherence, Grand Librarian for full rulebook
- **Advantage**: 1M+ context window for full campaign history tracking

### Software & Orchestration

- **Framework**: CrewAI (Hierarchical process)
- **Inference Bridge**: LiteLLM routing tasks between local nodes (Alien/Sardinia) and cloud APIs
- **State Management**: Agents communicate via Markdown files (saves tokens, human-readable audit trail)
- **CLI Orchestrator**: Claude Code acts as primary developer and execution engine

### State File Structure

| File | Description | Write Access |
|------|-------------|--------------|
| `SYSTEM.md` | FFG/Genesys core rules and weapon/item stats (from OggDude XML) | Read-only for agents |
| `WORLD.md` | Lore data (from Wookieepedia/Kaggle datasets) | Read-only for agents |
| `SESSION_LOG.md` | Permanent record of the story | Scribe only |
| `PARTY_STATS.md` | Current HP, Strain, and Inventory | Scribe only |
| `DRAFT.md` | Pre-commitment sandbox for agent negotiations | All agents |
| `PROTOCOL.md` | Static Prefix with Cancellation Protocol (prompt caching optimization) | Read-only |

### Critical Logic: Genesys Narrative Dice

All agents — especially the Referee — must strictly follow the Cancellation Protocol:

- **Success** cancels **Failure** (Net Successes ≥ 1 = Action succeeds)
- **Advantage** cancels **Threat**
- **Triumph** and **Despair** are narrative triggers; they count as Success/Failure for math but do NOT cancel each other

---

## Implementation Phases

### Phase 1: Modular Repository Linkage

- [ ] Define Environment Variables: Create a `.env` in the Engine repo pointing to the current World repo:
  ```
  WORLD_DATA_PATH=/path/to/world-star-wars-ffg
  ```
- [ ] Implement Dynamic Loading: Update `main.py` to import system prompts and knowledge bases from `${WORLD_DATA_PATH}` instead of local relative paths
- [ ] Standardize Schema: Create `schema.md` in the Engine repo defining how any World repo must format its `items.md` or `npcs.md`

### Phase 2: Engine Development (rpg-engine-core)

- [ ] **The Universal Referee**
  - Initialize the Referee agent with Genesys Core mechanics
  - Must handle dice, wounds, and strain without knowing setting-specific items (sees "Weapon Stats", not "Lightsaber")
- [ ] **The Orchestrator (CrewAI)**
  - Develop the Negotiation Flow logic
  - Build the `DiceRoller` tool (Python) to handle Success/Advantage cancellation math
- [ ] **The State Scribe**
  - Develop automated update logic for `session_log.md` and `party_stats.md`

### Phase 3: World Development (world-star-wars-ffg)

- [ ] **Data Ingestion**
  - Convert OggDude XMLs to the standardized Markdown schema from Phase 1
  - Output: `/data/items.md`, `/data/talents.md`, `/data/skills.md`
- [ ] **Adventure Scaffolding**
  - Convert "Debts to Pay" into `/story/adventure_core.md` and `/story/npcs.md`
- [ ] **Flavor Layer**
  - Create `world_config.yaml` telling the Engine which Star Wars-specific terms to prioritize (e.g., "Use 'The Force' instead of 'Magic'")

### Phase 4: Integration & Injection

- [ ] **The Prompt Builder**
  - Configure the Engine to inject World lore into Agent backstories at runtime
  - Example: `Referee Backstory = Generic_Referee_Logic + World_Specific_Rules_Override`
- [ ] **The RAG Mount**
  - Set up Vector Database to index `${WORLD_DATA_PATH}/knowledge_base`

### Phase 5: Technical Implementation Logic

- [ ] **Negotiation Buffer**
  - Ensure Actor/World Runner dialogue happens in a temporary file before `[COMMIT]` triggers the Referee
- [ ] **Git-Save System**
  - Auto-commit changes to the `state/` folder in the World repo after every session (enables "Save Game" branching)

### Phase 6: Hand-off to Implementation

- [ ] Create directory structures for both repos
- [ ] Build `main.py` in the Engine repo with a `load_world()` function that validates the World repo's schema
- [ ] Convert one OggDude XML to Markdown and verify the Referee agent can read and use a Blaster Pistol stat from the external World repo
