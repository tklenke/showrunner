# Terminology

Canonical terms for the showrunner engine. Use these consistently across all code,
docs, and comments. When in doubt, come here first.

---

## People

| Term | Definition |
|------|-----------|
| **User** | A human sitting at the keyboard. The person playing the game. |
| **PC** (Player Character) | The character(s) directly controlled by the User via CLI. `player: "human"` in character YAML. |
| **Companion** | A party character driven by AI (Actors agent), but taking major direction from the User through natural language. `player: "companion"` in character YAML. |
| **NPC** (Non-Player Character) | Any character driven entirely by the Show Runner and plot logic. No `player` field in character YAML. |

**Character** = any entity in the fiction: PC, Companion, or NPC. The User is not a Character — they exist outside the fiction.

**Party** = all PCs and Companions together. NPCs are not party members even if they
travel with the group.

---

## Narrative Structure

| Term | Definition |
|------|-----------|
| **Session** | One continuous play session from startup to quit. |
| **Scene** | A self-contained event at a location, loaded from a scene YAML file. |
| **Beat** | A dramatic sub-unit within a scene with a specific purpose and exit condition. |
| **Turn** | One full pass through all steps in the game loop. |

A beat spans one or more turns. A scene spans one or more beats.

---

## System Components

| Component | Definition |
|-----------|-----------|
| **Orchestrator** | The Python program (`src/showrunner/orchestrator.py`) that manages the turn loop, routes data between steps, reads/writes all state files, and makes every deterministic decision. When the docs say "the orchestrator does X," that means pure Python — no LLM involved. |

The two-action vocabulary of the game loop:
- **`call_llm()`** — non-deterministic; an LLM produces the output
- **the orchestrator** — deterministic; Python produces the output

---

## Agents

| Agent | Config key | Server | Role |
|-------|-----------|--------|------|
| **Show Runner** | `show_runner` | Sardinia | GM brain: beat plans, check identification, dice rulings, resolution narrative |
| **Narrator** | `narrator` | Sardinia | GM voice: beat openers, scene prose, last-action extraction |
| **Actors** | `actors` | Sardinia | Voicing: plays NPCs and Companions |
| **Scribe** | `scribe` | Alien | Record-keeping: one-sentence session log entry per turn |

---

## Inference Nodes

Physical servers and cloud endpoints that run the models. Agents are routed to nodes
via `config/litellm.yaml`.

| Node | Model | Alias | Hosts |
|------|-------|-------|-------|
| **Sardinia** | Llama 3.1 8B Instruct (LM Studio) | `sardinia/llama-3.1-8b` | Show Runner, Narrator, Actors |
| **Alien** | Llama 3.2 3B Instruct (llama.cpp) | `alien/llama-3.2-3b` | Scribe |
| **Gemini** | Gemini 2.5 Flash (Google AI Studio API) | `gemini/gemini-2.5-flash` | *(configured, not yet assigned)* |

**Sardinia** — i9-9900k, 64 GB RAM, RTX 2070 (8 GB VRAM), Windows, LM Studio Developer Mode.
`http://192.168.1.45:1234/v1`

**Alien** — i7-6700, 16 GB RAM, GTX 960 (2 GB VRAM), Debian 12, llama.cpp server.
`http://192.168.1.144:8080/v1`

**Gemini** — Cloud API. Requires `GEMINI_API_KEY` env var.

---

## Character `player` Field Values

| Value | Character type | Who drives it |
|-------|---------------|--------------|
| `"human"` | PC | User via CLI |
| `"companion"` | Companion | Actors agent, direction from User |
| *(omitted)* | NPC | Show Runner / plot |


## Abbreviations and Acronyms

| Abbreviation | Meaning | Notes |
|-------------|---------|-------|
| **SR** | Show Runner | The GM-brain agent |
| **Orch** | Orchestrator | The Python turn-loop program; deterministic decisions |
| **CW** | Context Window | Maximum token capacity of an LLM inference call |
| **PC** | Player Character | `player: "human"` |
| **NPC** | Non-Player Character | No `player` field |
| **GM** | Game Master | The human role SR emulates |
| **FFG** | Fantasy Flight Games | Publisher of the Genesys / Star Wars RPG system |
| **LLM** | Large Language Model | The AI models running on Sardinia, Alien, and Gemini |
| **CLI** | Command Line Interface | The terminal prompt the User interacts with |
| **GLMD** | `game_loop.md` | Shorthand for the game loop source-of-truth document |
| **TDD** | Test-Driven Development | Required workflow — see CLAUDE.md |
| **YAGNI** | You Ain't Gonna Need It | Core design principle — see CLAUDE.md |

*Tom is the User in all current examples. "User" is the preferred term in code and docs.*