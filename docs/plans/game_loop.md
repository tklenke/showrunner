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
3. Load initial `character_plans` from the beat's `character_plans` field in the scene YAML
   and write them to `scene_state.yaml`
4. Append `show_runner_notes` and `narrator_notes` from the beat to the `sr_ctx` and
   `narrator_ctx` strings — prefixed with `## Beat Director Notes:`
5. If `verbose`: print `\n=== {beat["title"]} ===` to terminal
6. Log the transition: `log.info(f"Beat transition: {current_beat}")`
7. Set `_last_beat = current_beat`

`_beat_notes_pending = True` is set before the turn loop starts so the first beat always
initializes correctly.

**Beat opener — `run_beat_opener()` (first turn of each beat only):**

| | |
|---|---|
| Agent | Narrator (sardinia 8B), single call |
| Input | Beat notes (`show_runner_notes`, `narrator_notes`) + last session log entry (if any) |
| Output | 2–3 sentences of player-facing prose describing the current situation |
| Prints | Directly to terminal, before Step 1 prompt |

On subsequent turns the resolution narrative from Step 7 provides orientation.

---

## Step 1 — User Input

```
"What do you and your companions do? > "
```

Free-form text. Direction to Companions is embedded naturally — no special syntax required.

---

## Step 2 — Companion Wave (`run_companion_wave()`)

```
Kae (Companion)  →  plan + beat context + user action  →  dialogue + actions
...
```

- One `call_llm()` per Companion (`player: "companion"` in character YAML).
- Each Companion receives their current plan from `character_plans`, beat context, and the
  user action. Companions act before NPCs and do not see this turn's NPC outputs.
- Companion outputs printed to terminal as they arrive.

---

## Step 3 — NPC Wave (`run_npc_wave()`)

```
NPC_1   →  plan + beat context + user action + companion outputs  →  full output (printed)
Narrator →  NPC_1 full output  →  compact summary  →  written to summaries log
NPC_2   →  plan + beat context + user action + companion outputs + NPC_1 SUMMARY  →  full output (printed)
Narrator →  NPC_2 full output  →  compact summary  →  written to summaries log
...
```

- One `call_llm()` per NPC; each receives their plan, beat context, user action, Companion
  outputs, and compact Narrator summaries of all prior NPCs (not the full outputs).
- One `call_llm()` (Narrator) immediately after each NPC; produces a 1–2 sentence summary.
  The summary is passed to the next NPC (CW management) and appended to
  `logs/turn_{ts}_{beat}_summaries.txt` (for use in Steps 5, 8, 9).
- Total: 2N `call_llm()` calls for N NPCs in this step.
- Full NPC outputs printed to terminal as they arrive; summaries are pipeline-internal.
- Returns `{npc_id: output, ...}` for use in Steps 5–7.

---

## Step 4 — Party Action Summaries (`run_summaries()`)

| | |
|---|---|
| Agent | Narrator (sardinia 8B), one call per non-NPC character that acted |
| Input | One character's action text (User action, Companion outputs) |
| Output | 1–2 sentence plain-language summary of what they did |
| Writes | `logs/turn_{ts}_{beat}_summaries.txt` (appended; NPC summaries already written in Step 3) |

NPC summaries are generated inline during Step 3. This step covers the User action and
any Companions. Uses the same Narrator agent and same log file for a consistent pipeline.

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

## Step 9 — Plan Update (`run_plan_update()`)

SR reviews the full turn and updates each character's plan for next turn.

**Call sequence:**

```
1 call:  SR  →  full context (summaries, results, last actions)  →  overall plan
N calls: SR  →  overall plan + that character's situation         →  individual plan
```

- The overall plan is SR's private coordination notes — logged for debugging but never
  shared with characters.
- One individual plan call per NPC and Companion (same code path for both).
- Orchestrator writes updated plans to `scene_state.yaml` → `character_plans`.

---

## Step 10 — Session Log (`run_scribe()`)

| | |
|---|---|
| Agent | Scribe (alien 3B), single call |
| Input | Scene state + full turn summary |
| Output | One-sentence narrative record of the turn |

Orchestrator appends output to `state/session_log.md`.

---

## Step 11 — Beat Advancement

```
CLI: [Enter] stay  |  [a] advance  |  [beat ID] jump  |  [q] quit
```

`advance_beat()` writes the new `current_beat` to `scene_state.yaml`. If no beats remain,
the scene ends.

---

## Ref A — Agent Summary

| Agent | Model | Steps |
|---|---|---|
| Show Runner | sardinia 8B | 5 (check id), 6 (rulings), 7 (narrative), 9 (plan update) |
| Narrator | sardinia 8B | 0 (beat opener), 3 (NPC summaries), 4 (User/Companion summaries), 8 (last-action extraction) |
| Actors | sardinia 8B | 2 (Companion voicing), 3 (NPC voicing) |
| Scribe | alien 3B | 10 (session log) |

The `referee` agent is configured in `config/agents.yaml` but not called by the current pipeline.

---

## Ref B — State Files Changed Per Turn

| File | Changed by | Step |
|---|---|---|
| `state/scene_state.yaml` `character_plans` | Orchestrator | 0 (beat init), 9 |
| `state/scene_state.yaml` `last_actions` | Orchestrator | 8 |
| `state/scene_state.yaml` `current_beat` | `advance_beat()` | Beat advancement |
| `state/session_log.md` | Orchestrator (Scribe output) | 10 |
| `state/party_stats.yaml` | Orchestrator *(not yet implemented)* | 6 |
| `logs/turn_{ts}_{beat}_summaries.txt` | Orchestrator | 4 |
| `logs/turn_{ts}_{beat}_checks.txt` | Orchestrator | 5 |
| `logs/turn_{ts}_{beat}_results.txt` | Orchestrator | 6 |
| `logs/turn_{ts}_{beat}_sr_plan.txt` | Orchestrator | 9 |
