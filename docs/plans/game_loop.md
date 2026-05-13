# Game Loop

How one turn executes: what the orchestrator does, what each agent does, and what files change.

**[REVISED 2026-05-13]** Updated to reflect the three-phase sequential architecture
(implemented in 4.13) and the five-step resolution pipeline (designed in 4.14, not yet
implemented). The old hierarchical crew design and 4.9 target architecture are retired.

---

## Per-Turn Setup (orchestrator, before any kickoff)

The orchestrator reads current state and renders context strings for agents:

| Data | Source file | Used in |
|---|---|---|
| Current beat, ticking clocks, character plans, last_actions | `state/scene_state.yaml` | Phase 1, Phase 2 |
| Wounds, strain per character | `state/party_stats.yaml` | Phase 1, Phase 3 |
| Beat descriptions, checks, NPC defs, location text | scene YAML (read-only) | all phases |
| Player's action from previous turn | `last_actions` in scene_state | Phase 1 Show Runner context |

Dynamic context lives in **Task descriptions**. Backstories are static role definitions only.

---

## Phase 1 — NPC Wave (one `Crew.kickoff()`)

```
Show Runner  →  beat plan
Narrator     →  narration (sees Show Runner)
NPC_1        →  dialogue + actions (sees Show Runner + beat plan)
NPC_2        →  dialogue + actions (sees Show Runner + NPC_1)
...
```

- One task per NPC; each chained to all prior NPC tasks so characters react to each other.
- After kickoff: Narrator text and NPC outputs printed to terminal.
- `npc_outputs: dict[str, str]` collected for Phase 2 and Phase 3.

---

## Player Input

```
"What do you and your companions do? > "
```

Free-form text. Direction to AI party members (e.g. "I tell Kae to cover the door")
is embedded naturally — no special syntax required.

---

## Phase 2 — AI PC Wave (one `Crew.kickoff()`)

```
Kae (AI PC)  →  dialogue + actions (sees NPC outputs + player action)
...
```

- One task per AI party member (`player: "ai"` in character YAML).
- Each AI PC task description contains the full NPC wave text and player action.
- After kickoff: AI PC outputs printed to terminal.

**Note:** Phase 2 previously ended with a Show Runner review task that identified checks.
This is removed in 4.14 — check identification moves to Phase 3b.

---

## Phase 3 — Resolution Pipeline

### Current (pre-4.14): single `build_resolution_crew()` kickoff

Show Runner review (end of Phase 2) parses a CHECKS block → one Referee task per check,
chained → Scribe. Referee has `tools=[roll_dice, ...]` on alien 3B. **This crashes** —
see architect_todo.md "Small models cannot use tools in ReAct loop."

---

### Target (4.14): five-step file-mediated pipeline

Each step is a separate `Crew.kickoff()`. The orchestrator manages data flow by writing
intermediate files between steps.

**Turn files** written to `logs/turn_{turn_ts}_{beat_id}_{type}.txt`. Persist forever —
one set per turn.

#### Step 3a — Action summaries

| | |
|---|---|
| Agent | Actors (alien 3B), one task per character that acted |
| Input | One character's action text |
| Output | 1–2 sentence plain-language summary of what they did |
| Writes | `turn_{ts}_{beat}_summaries.txt` |

No tools. No rules reasoning. Alien 3B handles simple summarisation reliably.

#### Step 3b — Check identification

| | |
|---|---|
| Agent | Show Runner (sardinia 8B), single task |
| Input | All summaries + character stats from YAML (characteristic values, skill ranks) |
| Output | Formatted check list or `NO_CHECKS` |
| Writes | `turn_{ts}_{beat}_checks.txt` |

Output format (one line per check):
```
1. {actor} | {skill} | {characteristic} {value} | {skill_rank} | {difficulty} | {notes}
```
Characteristic value and skill rank are embedded so the orchestrator can build a real
dice pool without further lookups.

#### Step 3c — Dice rolling + rulings

| | |
|---|---|
| Agent | Show Runner (sardinia 8B), one task per check |
| Input | Check spec + pre-computed roll result string |
| Output | Outcome ruling: passed/failed, wounds, triumph/despair effects |
| Writes | `turn_{ts}_{beat}_results.txt` |

The **orchestrator** rolls the dice in Python (`roll_pool()`) between reading the checks
file and building this crew. Sardinia receives the result string and interprets it — no
tools required. Tasks chain so each ruling sees prior rulings.

Skipped entirely if `NO_CHECKS`.

#### Step 3d — Resolution narrative

| | |
|---|---|
| Agent | Show Runner (sardinia 8B now / Gemini eventually), single task |
| Input | All three files: summaries, checks, results |
| Output | 2–4 sentences of player-facing narrative prose |
| Prints | Directly to terminal |

#### Step 3e — Last action extraction

| | |
|---|---|
| Agent | Show Runner (sardinia 8B), one task per active character |
| Input | All three files + character name |
| Output | One sentence capturing that character's last action |
| Writes | `scene_state.yaml` → `last_actions` dict |

Replaces the raw action-text `last_actions` currently assembled from `output.raw` strings.

---

## Per-Turn Teardown (orchestrator, after Phase 3)

| Step | What happens |
|---|---|
| Scribe crew | Single alien 3B task: one-sentence session log entry |
| `session_log.md` | Orchestrator appends Scribe output |
| `scene_state.yaml` `last_actions` | Written by 3e extraction |
| `_beat_prompt()` | CLI: stay / advance / jump / quit |
| `advance_beat()` | Writes `current_beat` to `scene_state.yaml` if advancing |

---

## Agent Summary

| Agent | Model | Tools | Role in turn |
|---|---|---|---|
| Show Runner | sardinia 8B | none | Phase 1 beat plan; 3b check id; 3c rulings; 3d narrative; 3e last actions |
| Narrator | sardinia 8B | none | Phase 1 narration |
| Actors | sardinia 8B | none | Phase 1 NPC voicing; Phase 2 AI PC voicing; 3a summaries |
| Referee | alien 3B | none | **Retired in 4.14.** Rulings moved to Show Runner (3c). |
| Scribe | alien 3B | none | Session log sentence (one task, end of turn) |

---

## State Files Changed Per Turn

| File | Changed by | When |
|---|---|---|
| `state/scene_state.yaml` `last_actions` | Orchestrator (3e) | After Phase 3 |
| `state/scene_state.yaml` `current_beat` | `advance_beat()` | After beat prompt |
| `state/session_log.md` | Orchestrator (Scribe output) | End of turn |
| `state/party_stats.yaml` | Orchestrator *(not yet implemented)* | After wounds resolved |
| `logs/turn_{ts}_{beat}_summaries.txt` | Orchestrator (3a) | Phase 3a |
| `logs/turn_{ts}_{beat}_checks.txt` | Orchestrator (3b) | Phase 3b |
| `logs/turn_{ts}_{beat}_results.txt` | Orchestrator (3c) | Phase 3c |
