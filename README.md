# showrunner
AI Agent Orchestration for RPG

## Concepts

Play is organised into four nested levels:

| Level | What it is |
|-------|-----------|
| **Session** | One continuous run from startup to quit |
| **Scene** | A self-contained event at a location (`skin/scenes/scene_N.yaml`) |
| **Beat** | A dramatic sub-unit within a scene — arrival, negotiation, combat, debrief |
| **Turn** | One agent cycle: player acts → companions and NPCs respond → Show Runner identifies and resolves checks → Narrator delivers the outcome |

A beat can span multiple turns. A combat beat runs one turn per round until the fight ends.
A simple arrival beat might resolve in a single turn.

---

## Setup

```bash
cd ~/projects/showrunner
python -m venv venv
source venv/bin/activate
pip install -e .
pip install -r requirements.txt
```

Set your Gemini API key:

```bash
export GEMINI_API_KEY=your_key_here
# or add it to a .env file:
echo "GEMINI_API_KEY=your_key_here" > .env
```

---

## Running a Session

```bash
source venv/bin/activate
python -m showrunner.main
```

Loads `state/scene_0.yaml` by default (Bargos mansion, Act 1).

**Options:**

```bash
python -m showrunner.main                      # scene 0 (default)
python -m showrunner.main 1                    # scene 1
python -m showrunner.main -v                   # verbose: labels each output block by step
python -m showrunner.main --dump-prompts       # write full prompt+response MD files to logs/prompts/
python -m showrunner.main --reset              # clear logs and scene state, restart from beat 1
python -m showrunner.main 1 -v --dump-prompts  # scene 1, verbose, with prompt capture
```

**`-v` / `--verbose`** adds `=== Step Name ===` headers before each major output block
(beat opener, resolution narrative) so you can see which agent produced which output.

**`--reset`** deletes `state/scene_state.yaml`, `state/session_log.md`, and everything
under `logs/` (including `logs/prompts/`), then starts from the first beat. Use this
when you want a clean run rather than resuming a prior session. `state/party_stats.yaml`
is preserved — delete it manually if you need fully clean wound/strain tracking.

**`--dump-prompts`** writes one Markdown file per LLM call to `logs/prompts/`:

```
logs/prompts/0001_narrator_run_beat_opener.md
logs/prompts/0002_actors_run_npc_wave[bargos_the_hutt].md
logs/prompts/0003_narrator_run_npc_wave[bargos_the_hutt].md
```

Each file contains the full `# System`, `# User`, and `# Response` text for that call.
The summary log at `logs/prompts_<timestamp>.log` is always written and shows a one-line
entry per call with a sequential ID, agent, model server, step, and token counts:

```
0001  14:32:01  narrator  sardinia  run_beat_opener                1842p →  312r
0002  14:32:04  actors    sardinia  run_npc_wave[bargos_the_hutt]  2103p →  445r
0003  14:32:06  narrator  sardinia  run_npc_wave[bargos_the_hutt]   198p →   61r
```

**During a session:**

The engine runs several AI steps after each player action. Output may include narrative
prose, character dialogue, and check results — and the prose sometimes ends with a
question or a dramatic beat. **Wait for the horizontal rule (`────...`) before typing.**
That line always appears immediately before a prompt that expects your input.

**Beat advancement** is decided automatically by the Show Runner after each turn. The SR
reads what happened this turn against the next beat's entry condition and outputs `ADVANCE`
or `STAY`. When it advances, NPC and Companion plans for the next turn are written with
the new beat context — so characters react to where the story actually is.

In `--verbose` mode the SR's decision is shown and you can accept it or override with a
manual choice:

```
[SR beat decision: ADVANCE]
[Enter]       accept SR decision
a             advance to the next beat
<beat-id>     jump to a specific beat (e.g. gamorrean_rumble)
stay          stay on the current beat
q             quit the session
```

In normal mode the SR's decision is applied silently and play continues.

---

## Running Tests

```bash
source venv/bin/activate
pytest
```
