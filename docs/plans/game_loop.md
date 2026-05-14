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
| Last session log entry (Step 7 narrative from prior turn) | `state/session_log.md` | Step 0 beat opener |

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
8. Reset `_turn_num = 1`

`_beat_notes_pending = True` and `_turn_num = 1` are set before the turn loop starts.
`_turn_num` increments at the end of each turn and resets on beat transition.

**Log file naming:** `{scene:02d}_{beat:02d}_{beat_id}_{turn:04d}_{type}.txt`
Zero-padded numbers ensure correct sort order by scene → beat → turn.

**Beat opener — `run_beat_opener()` (first turn of each beat only):**

| | |
|---|---|
| Agent | Narrator, single call |
| Input | Beat notes (`show_runner_notes`, `narrator_notes`) + last session log entry (if any) |
| Output | 2–3 sentences of player-facing prose describing the current situation |
| Prints | Directly to terminal, before Step 1 prompt |

- One `call_llm()` — first turn of each beat only.
- On subsequent turns the resolution narrative from Step 7 provides orientation.

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
  `logs/{scene:02d}_{beat:02d}_{beat_id}_{turn:04d}_summaries.txt` (for use in Steps 5, 8, 9).
- Total: 2N `call_llm()` calls for N NPCs in this step.
- Full NPC outputs printed to terminal as they arrive; summaries are pipeline-internal.
- Returns `{npc_id: output, ...}` for use in Steps 5–7.

---

## Step 4 — Party Action Summaries (`run_summaries()`)

| | |
|---|---|
| Agent | Narrator, one call per party member that acted |
| Input | One character's action text (User action or Companion output) |
| Output | 1–2 sentence plain-language summary of what they did |
| Writes | `logs/{scene:02d}_{beat:02d}_{beat_id}_{turn:04d}_summaries.txt` (appended; NPC summaries already written in Step 3) |

- One `call_llm()` per party member that acted (User + any Companions).
- NPC summaries are generated inline during Step 3; this step covers the party only.
- Same Narrator agent and same log file as Step 3 for a consistent pipeline.

---

## Step 5 — Check Identification (`run_checks()`)

| | |
|---|---|
| Agent | Show Runner, one call per character that acted |
| Input | That character's summary + their stats (characteristic values, skill ranks) |
| Output | Check spec(s) for that character, or `NO_CHECKS` |
| Writes | `logs/{scene:02d}_{beat:02d}_{beat_id}_{turn:04d}_checks.txt` |

- One `call_llm()` per character — focused on one actor at a time rather than the full
  batch, keeping the context window manageable.
- Orchestrator collects all outputs and writes them to the checks log.

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
| Agent | Show Runner, one call per check |
| Input | Check spec + pre-computed roll result string |
| Output | Outcome ruling: passed/failed, wounds, triumph/despair effects |
| Writes | `logs/{scene:02d}_{beat:02d}_{beat_id}_{turn:04d}_results.txt` |

- The orchestrator parses the checks log, builds each dice pool, and calls `roll_pool()` — deterministic.
- One `call_llm()` per check; the LLM receives the pre-computed roll result and rules on it.
- Each `call_llm()` receives current `party_stats` (updated after each ruling) as context,
  not the prior ruling text — avoids CW blowout in large combats.
- Ruling output is parsed by the orchestrator using the **Structured Output Chain** (see Ref C).
- Orchestrator updates `party_stats.yaml` after each successful parse. Skipped entirely if `NO_CHECKS`.

---

## Step 7 — Resolution Narrative (`run_narrative()`)

| | |
|---|---|
| Agent | Show Runner, single call |
| Input | All three log files: summaries, checks, results |
| Output | 2–4 sentences of player-facing narrative prose |
| Prints | Directly to terminal |

- One `call_llm()`.
- Orchestrator appends output to `state/session_log.md` (deterministic write, no extra call).

---

## Step 8 — Last Action Extraction (`run_last_actions()`)

| | |
|---|---|
| Agent | Narrator, one call per active character |
| Input | That character's summary |
| Output | One sentence capturing that character's last action |

- One `call_llm()` per active character (NPCs + Companions + PC).
- Orchestrator writes the collected dict to `scene_state.yaml` → `last_actions`.

---

## Step 9 — Plan Update (`run_plan_update()`)

SR reviews the full turn and updates each character's plan for next turn.

**Call sequence:**

```
1 call:  SR  →  full context (summaries, results, last actions)  →  overall plan
N calls: SR  →  overall plan + that character's situation         →  individual plan
```

- One `call_llm()` for the overall plan.
- One `call_llm()` per character (NPC and Companion, same code path) for individual plans.
- Total: 1 + N `call_llm()` calls for N characters.
- The overall plan is SR's private coordination notes — logged for debugging but never
  shared with characters.
- Orchestrator writes updated plans to `scene_state.yaml` → `character_plans`.

---

## Step 10 — Beat Advancement

```
CLI: [Enter] stay  |  [a] advance  |  [beat ID] jump  |  [q] quit
```

`advance_beat()` writes the new `current_beat` to `scene_state.yaml`. If no beats remain,
the scene ends.

---

## Ref A — Agent Assignment Per Step

| Step | Runner function | LLM calls | Agent | Output type | Notes |
|---|---|---|---|---|---|
| 0 beat opener | `run_beat_opener` | 1 | Narrator | Player-facing prose | First turn of each beat only |
| 2 companion wave | `run_companion_wave` | 1 per Companion | Actors | Screenplay | — |
| 2 companion summary | `run_companion_wave` | 1 per Companion | Scribe | 1–2 sentence summary | Pipeline-internal |
| 3 NPC voicing | `run_npc_wave` | 1 per NPC | Actors | Screenplay | — |
| 3 NPC summary | `run_npc_wave` | 1 per NPC | Scribe | 1–2 sentence summary | Pipeline-internal; fed to next NPC |
| 4 party summaries | `run_summaries` | 1 per party member | Scribe | 1–2 sentence summary | PC + Companions only; NPCs done in Step 3 |
| 5 check identification | `run_checks` | 1 per character | Referee | Structured pipe-delimited | Parsed by `_parse_ruling_specs`; repair chain applied |
| 6 dice + rulings | `run_rulings` | 1 per check | Show Runner | Prose ruling + embedded numbers | `_extract_stat_changes` parses wounds/strain |
| 7 resolution narrative | `run_narrative` | 1 | Narrator | Player-facing prose | — |
| 8 last-action extraction | `run_last_actions` | 1 per active character | Scribe | 1 sentence | Written to `scene_state.yaml` → `last_actions` |
| 9 overall plan | `run_plan_update` | 1 | Show Runner | Prose (internal) | SR coordination notes; not shared with characters |
| 9 individual plans | `run_plan_update` | 1 per NPC + Companion | Scribe | Prose plan | Written to `scene_state.yaml` → `character_plans` |

Agent models are configured in `config/agents.yaml`. The `referee` and `scribe` agents are
defined there but not called by the current pipeline.

---

## Ref B — State File Changes Per Turn

| Step | File | Changed by |
|---|---|---|
| 0 (beat init), 9 | `state/scene_state.yaml` `character_plans` | Orchestrator |
| 4 | `logs/{scene:02d}_{beat:02d}_{beat_id}_{turn:04d}_summaries.txt` | Orchestrator |
| 5 | `logs/{scene:02d}_{beat:02d}_{beat_id}_{turn:04d}_checks.txt` | Orchestrator |
| 6 | `logs/{scene:02d}_{beat:02d}_{beat_id}_{turn:04d}_results.txt` | Orchestrator |
| 6 | `state/party_stats.yaml` | Orchestrator |
| 7 | `state/session_log.md` | Orchestrator |
| 8 | `state/scene_state.yaml` `last_actions` | Orchestrator |
| 9 | `logs/{scene:02d}_{beat:02d}_{beat_id}_{turn:04d}_sr_plan.txt` | Orchestrator |
| 10 | `state/scene_state.yaml` `current_beat` | `advance_beat()` |

---

## Ref C — Structured Output Chain

Used wherever the orchestrator must extract structured data from LLM or User output.
Any step that parses LLM output should reference this pattern rather than define its own.

The orchestrator never parses free-form text cold — it always leads with a programmatic
best-guess (regex, keyword extraction) and hands that to an LLM to confirm or correct.

```
Orch parses structured output
  ├── success  →  proceed
  └── fail     →  Orch makes programmatic best-guess (regex / keyword extraction)
                    → call_llm() Narrator: raw output + best-guess → corrected structured output
                      → Orch parses
                        ├── success  →  proceed, log recovery
                        └── fail     →  Orch makes new best-guess
                                          → call_llm() SR: raw + best-guess → structured output
                                            → Orch parses
                                              ├── success  →  proceed, log escalation
                                              └── fail     →  prompt User (free-form text)
                                                                → Orch makes best-guess from User input
                                                                  → call_llm() Narrator: User input + best-guess → structured
                                                                    → Orch parses
                                                                      ├── success  →  proceed, log
                                                                      └── fail     →  re-prompt User (max 2 attempts)
                                                                                      → zero fallback + loud log warning
```

**Zero fallback** is only reached if the User explicitly skips or all attempts fail — the
User has been informed and made an active choice to accept the gap.

**Logging** — every recovery and escalation is written to the session log so the User can
review what was auto-corrected or guessed after the session.

**call_llm() cost** — worst case: 2 extra calls per parse failure (Narrator + SR), plus
up to 2 calls per User re-prompt. In practice the chain should rarely go past level 1.
