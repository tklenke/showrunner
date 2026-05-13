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

A beat does not advance automatically — the User chooses stay / advance / jump at the
end of each turn. Multiple turns can execute within the same beat.

---

## Step 0 — Turn Setup (every turn)

**State loading** — the orchestrator reads current state and renders context strings:

| Data | Source file | Used in |
|---|---|---|
| Current beat, ticking clocks, character plans, last_actions | `state/scene_state.yaml` | Steps 1–3 |
| Wounds, strain per character | `state/party_stats.yaml` | Steps 3, 5–7 |
| Beat descriptions, NPC defs, location text | scene YAML (read-only) | all steps |
| Last session log entry | `state/session_log.md` | Step 0 beat opener |

**Beat initialization (first turn of each beat only):**
1. Compare `current_beat` against `_last_beat`; if different, a transition is detected
2. Look up the current beat dict from `scene["beats"]` by `id == current_beat`
3. Append `show_runner_notes` and `narrator_notes` from the beat to the `sr_ctx` and
   `narrator_ctx` strings passed into Step 3 — prefixed with `## Beat Director Notes:`
4. If `verbose`: print `\n=== {beat["title"]} ===` to terminal
5. Log the transition: `log.info(f"Beat transition: {current_beat}")`
6. Set `_last_beat = current_beat`

`_beat_notes_pending = True` is set before the turn loop starts so the first beat always
initializes correctly.

**Beat opener (first turn of each beat only):**

| | |
|---|---|
| Agent | Narrator (sardinia 8B), single call |
| Input | Beat notes (`show_runner_notes`, `narrator_notes`) + last session log entry (if any) |
| Output | 2–3 sentences of player-facing prose describing the current situation |
| Prints | Directly to terminal, before Step 1 prompt |

On subsequent turns within the same beat, the resolution narrative from the previous turn
(Step 7) provides orientation — no opener call is made.

---

## Step 1 — User Input

```
"What do you and your companions do? > "
```

Free-form text. Direction to Companions is embedded naturally — no special syntax required.

---

## Step 2 — Companion Wave (`run_companion_wave()`)

```
Kae (Companion)  →  dialogue + actions
...
```

- One `call_llm()` per Companion (`player: "companion"` in character YAML).
- Each call receives beat context (from Step 0 director notes), the user's action, and
  last turn context. Companions act before NPCs and do not see this turn's NPC outputs.
- Companion outputs printed to terminal as they arrive.

---

## Step 3 — NPC Wave (`run_npc_wave()`)

```
Show Runner  →  scene state + user action + companion outputs  →  beat plan
Narrator     →  narration of NPC reactions (receives beat plan)
NPC_1        →  dialogue + actions (receives beat plan + user action)
NPC_2        →  dialogue + actions (receives beat plan + NPC_1 output)
...
```

- Show Runner receives the full context (scene state, user action, Companion outputs) and
  produces a beat plan directing NPC behaviour in response.
- One `call_llm()` per NPC; each receives the beat plan and all prior NPC outputs.
- Narrator text and NPC outputs printed to terminal as they arrive.
- Returns `{"_narrator": narration, npc_id: output, ...}` for use in Steps 4–7.

---

## Step 4 — Action Summaries (`run_summaries()`)

| | |
|---|---|
| Agent | Actors (sardinia 8B), one call per character that acted |
| Input | One character's action text |
| Output | 1–2 sentence plain-language summary of what they did |
| Writes | `logs/turn_{ts}_{beat}_summaries.txt` |

One focused call per actor; no rules reasoning required.

---

## Step 5 — Check Identification (`run_checks()`)

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

## Step 6 — Dice + Rulings (`run_rulings()`)

| | |
|---|---|
| Agent | Show Runner (sardinia 8B), one call per check |
| Input | Check spec + pre-computed roll result string |
| Output | Outcome ruling: passed/failed, wounds, triumph/despair effects |
| Writes | `logs/turn_{ts}_{beat}_results.txt` |

The **orchestrator** rolls the dice in Python (`roll_pool()`) before calling `run_rulings()`.
Each ruling call receives all prior rulings as context. Skipped entirely if `NO_CHECKS`.

---

## Step 7 — Resolution Narrative (`run_narrative()`)

| | |
|---|---|
| Agent | Show Runner (sardinia 8B), single call |
| Input | All three log files: summaries, checks, results |
| Output | 2–4 sentences of player-facing narrative prose |
| Prints | Directly to terminal |

---

## Step 8 — Last Action Extraction (`run_last_actions()`)

| | |
|---|---|
| Agent | Narrator (sardinia 8B), one call per active character |
| Input | That character's summary |
| Output | One sentence capturing that character's last action |

Orchestrator writes the collected dict to `scene_state.yaml` → `last_actions`.

---

## Step 9 — Session Log (`run_scribe()`)

| | |
|---|---|
| Agent | Scribe (alien 3B), single call |
| Input | Scene state + full turn summary |
| Output | One-sentence narrative record of the turn |

Orchestrator appends output to `state/session_log.md`.

---

## Step 10 — Beat Advancement

```
CLI: [Enter] stay  |  [a] advance  |  [beat ID] jump  |  [q] quit
```

`advance_beat()` writes the new `current_beat` to `scene_state.yaml`. If no beats remain,
the scene ends.

---

## Ref A — Agent Summary

| Agent | Model | Steps |
|---|---|---|
| Show Runner | sardinia 8B | 3 (beat plan), 5 (check id), 6 (rulings), 7 (narrative) |
| Narrator | sardinia 8B | 0 (beat opener), 3 (narration), 8 (last-action extraction) |
| Actors | sardinia 8B | 2 (Companion voicing), 3 (NPC voicing), 4 (summaries) |
| Scribe | alien 3B | 9 (session log) |

The `referee` agent is configured in `config/agents.yaml` but not called by the current pipeline.

---

## Ref B — State Files Changed Per Turn

| File | Changed by | Step |
|---|---|---|
| `state/scene_state.yaml` `last_actions` | Orchestrator | 8 |
| `state/scene_state.yaml` `current_beat` | `advance_beat()` | Beat advancement |
| `state/session_log.md` | Orchestrator (Scribe output) | 9 |
| `state/party_stats.yaml` | Orchestrator *(not yet implemented)* | 6 |
| `logs/turn_{ts}_{beat}_summaries.txt` | Orchestrator | 4 |
| `logs/turn_{ts}_{beat}_checks.txt` | Orchestrator | 5 |
| `logs/turn_{ts}_{beat}_results.txt` | Orchestrator | 6 |
