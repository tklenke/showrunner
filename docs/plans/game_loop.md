# Game Loop

How one turn executes: what the orchestrator does, what each agent does, and what files change.

---

## Per-Turn Setup (orchestrator, before kickoff)

The orchestrator reads current state and renders it into prompt strings:

| Data | File | Used by |
|---|---|---|
| Current beat, NPC knowledge, flags | `state/scene_state.yaml` | Show Runner, Narrator, Scribe |
| HP, wounds, XP, inventory | `state/party_stats.yaml` | Referee, Scribe, Actors |
| Beat descriptions, NPC defs, location text | scene YAML (read-only) | all agents |
| Player's last action | CLI input from previous turn | Show Runner, Narrator |

Each rendered string is injected into the relevant agent's **backstory** at crew-build time.
The Show Runner also receives a context string in its **task description**.

---

## CrewAI Execution (hierarchical process)

```
Show Runner (manager)
  → delegates → Narrator    narrate the beat, describe outcomes
  → delegates → Actors      voice NPCs for this beat
  → delegates → Referee     resolve skill/combat checks
  → delegates → Scribe      record outcomes to state files
```

One `Task` object exists, nominally owned by the Narrator. The Show Runner intercepts it
and decides the actual delegation sequence.

---

## Agent Summary

| Agent | Model | Tools | State writes |
|---|---|---|---|
| Show Runner | sardinia 8B | none | none — delegates only |
| Narrator | sardinia 8B | `consult_show_runner` | none |
| Actors | sardinia 8B | `read_state`, `consult_show_runner` | none |
| Referee | alien 3B | `roll_dice`, `read_state`, `consult_show_runner` | none |
| Scribe | alien 3B | `read_state`, `write_state`, `consult_show_runner` | `scene_state.yaml`, `party_stats.yaml` |

---

## Per-Turn Teardown (orchestrator, after kickoff)

| Step | What happens |
|---|---|
| Print result | crew's final output shown to player |
| `prompt_player_action()` | CLI: "What does Z-4P0 do?" → stored as `last_action` |
| `_beat_prompt()` | CLI: stay / advance to next beat / jump to beat ID / quit |
| `advance_beat()` | if advancing: writes `current_beat` in `scene_state.yaml` |

---

---

## Target Architecture (4.9 refactor)

```
Orchestrator: initialize_scene_state() if needed
              write player's action into last_actions before kickoff

Sequential crew:
  Task 1 — Show Runner    plan this beat
  Task 2 — Narrator       narrate (sees task 1)
  Task 3 — Actors         voice NPCs (sees task 1)
  Task 4 — Referee        resolve checks (sees tasks 1–3)
  Task 5 — Scribe         write state (sees tasks 1–4)

Orchestrator: read last_actions back from scene_state for next turn
```

Dynamic context (beat, state, last_actions) lives in **Task descriptions**.
Backstories revert to static role definitions only.

---

## Known Weaknesses (current — pre-4.9)

**1. Context is stale within a turn**
Scene state is baked into agent backstories at crew-build time. If the Scribe writes state
mid-turn, the Narrator and Actors don't see it — their backstories don't update.

**2. One task for the whole beat**
There is a single Task object. The Show Runner is expected to invent delegation subtasks
on the fly (CrewAI hierarchical mode). This works well with a large capable manager model
but is fragile with a local 8B model.

**3. Scribe is the only writer and uses the weakest model**
All state persistence depends on the 3B alien model correctly calling `write_state`.
Silent failures (wrong args, schema errors) cause the beat to replay unchanged.

**4. Beat advancement is manual**
The orchestrator does not automatically advance beats — the player must press `[a]` at the
CLI prompt. The Show Runner has no mechanism to signal "this beat is done."
