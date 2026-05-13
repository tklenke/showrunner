# Game Loop

How one turn executes: what the orchestrator does, what each agent does, and what files change.

---

## Narrative Hierarchy

| Level | Scope | Example |
|---|---|---|
| **Session** | One continuous play session, startup to quit | An evening playing *Debts to Pay* |
| **Scene** | One location or event; loaded from a scene YAML file | The Bargos mansion visit |
| **Beat** | A dramatic sub-unit within a scene; may span many turns | `gamorrean_rumble` |
| **Turn** | One full pass through all steps below | One round of combat |

A beat does not advance automatically — the player chooses stay / advance / jump at the
end of each turn. Multiple turns can execute within the same beat.

---

## Step 0a — Beat Initialization (turn 1 of each beat only)

Fires when `current_beat` differs from the previous turn's beat. Skipped on all
subsequent turns within the same beat.

1. Look up the current beat dict in the scene YAML by `id`
2. Append `show_runner_notes` and `narrator_notes` to the context strings passed
   into Step 1, prefixed as authoritative direction:
   ```
   ## Beat Director Notes:
   {beat["show_runner_notes"]}
   ```
3. If `--verbose`: print `=== {beat["title"]} ===` to terminal
4. Log the transition regardless: `Beat transition: {beat_id}`

Purely programmatic — no LLM call. Agents in Steps 1–8 then operate within the
correctly-established beat frame.

---

## Step 0b — State Loading (every turn, before any LLM calls)

The orchestrator reads current state and renders context strings passed into each step:

| Data | Source file | Used in |
|---|---|---|
| Current beat, ticking clocks, character plans, last_actions | `state/scene_state.yaml` | Steps 1, 2 |
| Wounds, strain per character | `state/party_stats.yaml` | Steps 1, 3–5 |
| Beat descriptions, NPC defs, location text | scene YAML (read-only) | all steps |
| Player's action from previous turn | `last_actions` in scene_state | Step 1 Show Runner context |

---

## Step 1 — NPC Wave (`run_npc_wave()`)

```
Show Runner  →  beat plan
Narrator     →  narration (receives beat plan)
NPC_1        →  dialogue + actions (receives beat plan)
NPC_2        →  dialogue + actions (receives beat plan + NPC_1 output)
...
```

- One `call_llm()` per NPC; each receives the beat plan and all prior NPC outputs.
- Narrator text and NPC outputs printed to terminal as they arrive.
- Returns `{"_narrator": narration, npc_id: output, ...}` for use in Steps 2–5.

---

## Player Input

```
"What do you and your companions do? > "
```

Free-form text. Direction to AI party members is embedded naturally — no special syntax required.

---

## Step 2 — AI PC Wave (`run_pc_wave()`)

```
Kae (AI PC)  →  dialogue + actions (receives NPC wave text + player action)
...
```

- One `call_llm()` per AI party member (`player: "ai"` in character YAML).
- Each call receives the full NPC wave text and player action.
- AI PC outputs printed to terminal as they arrive.

---

## Step 3 — Action Summaries (`run_summary_phase()`)

| | |
|---|---|
| Agent | Actors (sardinia 8B), one call per character that acted |
| Input | One character's action text |
| Output | 1–2 sentence plain-language summary of what they did |
| Writes | `logs/turn_{ts}_{beat}_summaries.txt` |

One focused call per actor; no rules reasoning required.

---

## Step 4 — Check Identification (`run_check_phase()`)

| | |
|---|---|
| Agent | Show Runner (sardinia 8B), single call |
| Input | All summaries + character stats from YAML (characteristic values, skill ranks) |
| Output | Formatted check list or `NO_CHECKS` |
| Writes | `logs/turn_{ts}_{beat}_checks.txt` |

Output format (one line per check):
```
1. {actor} | {skill} | {characteristic} {value} | {skill_rank} | {difficulty} | {notes}
```
Characteristic value and skill rank are embedded so the orchestrator can build a real
dice pool without further lookups.

---

## Step 5 — Dice + Rulings (`run_ruling_phase()`)

| | |
|---|---|
| Agent | Show Runner (sardinia 8B), one call per check |
| Input | Check spec + pre-computed roll result string |
| Output | Outcome ruling: passed/failed, wounds, triumph/despair effects |
| Writes | `logs/turn_{ts}_{beat}_results.txt` |

The **orchestrator** rolls the dice in Python (`roll_pool()`) before calling `run_ruling_phase()`.
Each ruling call receives all prior rulings as context. Skipped entirely if `NO_CHECKS`.

---

## Step 6 — Resolution Narrative (`run_narrative_phase()`)

| | |
|---|---|
| Agent | Show Runner (sardinia 8B), single call |
| Input | All three log files: summaries, checks, results |
| Output | 2–4 sentences of player-facing narrative prose |
| Prints | Directly to terminal |

---

## Step 7 — Last Action Extraction (`run_last_action_phase()`)

| | |
|---|---|
| Agent | Narrator (sardinia 8B), one call per active character |
| Input | That character's summary |
| Output | One sentence capturing that character's last action |

Orchestrator writes the collected dict to `scene_state.yaml` → `last_actions`.

---

## Step 8 — Session Log (`run_scribe_phase()`)

| | |
|---|---|
| Agent | Scribe (alien 3B), single call |
| Input | Scene state + full turn summary |
| Output | One-sentence narrative record of the turn |

Orchestrator appends output to `state/session_log.md`.

---

## Beat Advancement

```
CLI: [Enter] stay  |  [a] advance  |  [beat ID] jump  |  [q] quit
```

`advance_beat()` writes the new `current_beat` to `scene_state.yaml`. If no beats remain,
the scene ends.

---

## Agent Summary

| Agent | Model | Steps |
|---|---|---|
| Show Runner | sardinia 8B | 1 (beat plan), 4 (check id), 5 (rulings), 6 (narrative) |
| Narrator | sardinia 8B | 1 (narration), 7 (last-action extraction) |
| Actors | sardinia 8B | 1 (NPC voicing), 2 (AI PC voicing), 3 (summaries) |
| Scribe | alien 3B | 8 (session log) |

The `referee` agent is configured in `config/agents.yaml` but not called by the current pipeline.

---

## State Files Changed Per Turn

| File | Changed by | Step |
|---|---|---|
| `state/scene_state.yaml` `last_actions` | Orchestrator | 7 |
| `state/scene_state.yaml` `current_beat` | `advance_beat()` | Beat advancement |
| `state/session_log.md` | Orchestrator (Scribe output) | 8 |
| `state/party_stats.yaml` | Orchestrator *(not yet implemented)* | 5 |
| `logs/turn_{ts}_{beat}_summaries.txt` | Orchestrator | 3 |
| `logs/turn_{ts}_{beat}_checks.txt` | Orchestrator | 4 |
| `logs/turn_{ts}_{beat}_results.txt` | Orchestrator | 5 |
