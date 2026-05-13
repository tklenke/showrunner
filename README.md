# showrunner
AI Agent Orchestration for RPG

## Concepts

Play is organised into four nested levels:

| Level | What it is |
|-------|-----------|
| **Session** | One continuous run from startup to quit |
| **Scene** | A self-contained event at a location (`state/scene_N.yaml`) |
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
python -m showrunner.main          # scene 0 (default)
python -m showrunner.main 1        # scene 1
python -m showrunner.main -v       # verbose: labels each output block by step
python -m showrunner.main 1 -v     # scene 1, verbose
```

**During a session:**

The engine runs several AI steps after each player action. Output may include narrative
prose, character dialogue, and check results — and the prose sometimes ends with a
question or a dramatic beat. **Wait for the horizontal rule (`────...`) before typing.**
That line always appears immediately before a prompt that expects your input.

At the end of each turn you are prompted for beat advancement:

```
[Enter]       stay on the current beat
a             advance to the next beat
<beat-id>     jump to a specific beat (e.g. gamorrean_rumble)
q             quit the session
```

---

## Running Tests

```bash
source venv/bin/activate
pytest
```
