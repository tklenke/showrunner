# Game Loop

How one turn executes: what the orchestrator does, what each agent does, and what files change.

---

## Per-Turn Setup (orchestrator, before any LLM calls)

The orchestrator reads current state and renders context strings passed to each phase:

| Data | Source file | Used in |
|---|---|---|
| Current beat, ticking clocks, character plans, last_actions | `state/scene_state.yaml` | Phase 1, Phase 2 |
| Wounds, strain per character | `state/party_stats.yaml` | Phase 1, Phase 3 |
| Beat descriptions, checks, NPC defs, location text | scene YAML (read-only) | all phases |
| Player's action from previous turn | `last_actions` in scene_state | Phase 1 Show Runner context |

---

## Phase 1 — NPC Wave (`run_npc_wave()`)

```
Show Runner  →  beat plan
Narrator     →  narration (receives beat plan)
NPC_1        →  dialogue + actions (receives beat plan)
NPC_2        →  dialogue + actions (receives beat plan + NPC_1 output)
...
```

- One `call_llm()` per NPC; each receives the beat plan and all prior NPC outputs.
- Narrator text and NPC outputs printed to terminal as they arrive.
- Returns `{"_narrator": narration, npc_id: output, ...}` for use in Phase 2 and Phase 3.

---

## Player Input

```
"What do you and your companions do? > "
```

Free-form text. Direction to AI party members (e.g. "I tell Kae to cover the door")
is embedded naturally — no special syntax required.

---

## Phase 2 — AI PC Wave (`run_pc_wave()`)

```
Kae (AI PC)  →  dialogue + actions (receives NPC wave text + player action)
...
```

- One `call_llm()` per AI party member (`player: "ai"` in character YAML).
- Each call receives the full NPC wave text and player action.
- AI PC outputs printed to terminal as they arrive.

---

## Phase 3 — Resolution Pipeline

Each step is a direct `call_llm()` sequence managed by the orchestrator. Intermediate files
written between steps serve as both debug trail and inter-step context.

**Turn files** written to `logs/turn_{turn_ts}_{beat_id}_{type}.txt`. Persist forever —
one set per turn.

### Step 3a — Action summaries (`run_summary_phase()`)

| | |
|---|---|
| Agent | Actors (sardinia 8B), one call per character that acted |
| Input | One character's action text |
| Output | 1–2 sentence plain-language summary of what they did |
| Writes | `turn_{ts}_{beat}_summaries.txt` |

No rules reasoning. One focused call per actor.

### Step 3b — Check identification (`run_check_phase()`)

| | |
|---|---|
| Agent | Show Runner (sardinia 8B), single call |
| Input | All summaries + character stats from YAML (characteristic values, skill ranks) |
| Output | Formatted check list or `NO_CHECKS` |
| Writes | `turn_{ts}_{beat}_checks.txt` |

Output format (one line per check):
```
1. {actor} | {skill} | {characteristic} {value} | {skill_rank} | {difficulty} | {notes}
```
Characteristic value and skill rank are embedded so the orchestrator can build a real
dice pool without further lookups.

### Step 3c — Dice rolling + rulings (`run_ruling_phase()`)

| | |
|---|---|
| Agent | Show Runner (sardinia 8B), one call per check |
| Input | Check spec + pre-computed roll result string |
| Output | Outcome ruling: passed/failed, wounds, triumph/despair effects |
| Writes | `turn_{ts}_{beat}_results.txt` |

The **orchestrator** rolls the dice in Python (`roll_pool()`) before calling `run_ruling_phase()`.
Each ruling call receives all prior rulings as context. Skipped entirely if `NO_CHECKS`.

### Step 3d — Resolution narrative (`run_narrative_phase()`)

| | |
|---|---|
| Agent | Show Runner (sardinia 8B), single call |
| Input | All three files: summaries, checks, results |
| Output | 2–4 sentences of player-facing narrative prose |
| Prints | Directly to terminal |

### Step 3e — Last action extraction (`run_last_action_phase()`)

| | |
|---|---|
| Agent | Narrator (sardinia 8B), one call per active character |
| Input | That character's summary |
| Output | One sentence capturing that character's last action |

Orchestrator writes the collected dict to `scene_state.yaml` → `last_actions`.

---

## Per-Turn Teardown (orchestrator, after Phase 3)

| Step | What happens |
|---|---|
| Scribe call | `run_scribe_phase()` → single alien 3B call → one-sentence session log entry |
| `session_log.md` | Orchestrator appends Scribe output |
| `scene_state.yaml` `last_actions` | Written from 3e extraction results |
| `_beat_prompt()` | CLI: stay / advance / jump / quit |
| `advance_beat()` | Writes `current_beat` to `scene_state.yaml` if advancing |

---

## Agent Summary

| Agent | Model | Role in turn |
|---|---|---|
| Show Runner | sardinia 8B | Phase 1 beat plan; 3b check identification; 3c rulings; 3d narrative |
| Narrator | sardinia 8B | Phase 1 narration; 3e last-action extraction |
| Actors | sardinia 8B | Phase 1 NPC voicing; Phase 2 AI PC voicing; 3a summaries |
| Scribe | alien 3B | Session log sentence (one call, end of turn) |

The `referee` agent is configured in `config/agents.yaml` but not called by the current pipeline.

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
