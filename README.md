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
python -m showrunner.main                  # scene 0 (default)
python -m showrunner.main 1               # scene 1
python -m showrunner.main --dump-prompts  # write full prompt+response MD files to logs/prompts/
python -m showrunner.main --reset         # clear logs and scene state, restart from beat 1
```

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
the new beat context — so characters react to where the story actually is. The SR's
decision is applied silently and play continues.

---

## Web App

Start the browser-based interface:

```bash
source venv/bin/activate
uvicorn showrunner.web.app:app --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000` in a browser. The app streams narrative events via SSE;
player input is posted back to `/play/input`. Single-session: opening a second tab cancels
the first.

---

## Running Tests

```bash
source venv/bin/activate
pytest
```

---

## Deployment (AWS t4g.small)

Provision an Ubuntu 24.04 ARM instance. Then:

```bash
# 1. Install system packages
sudo apt update
sudo apt install -y python3.11 python3.11-venv nginx certbot python3-certbot-nginx

# 2. Create app user and directory
sudo useradd -r -s /bin/false showrunner
sudo mkdir -p /opt/showrunner
sudo chown showrunner:showrunner /opt/showrunner

# 3. Deploy code
sudo -u showrunner git clone <repo-url> /opt/showrunner
cd /opt/showrunner
sudo -u showrunner python3.11 -m venv venv
sudo -u showrunner venv/bin/pip install -e . -r requirements.txt

# 4. Add API key
echo "GEMINI_API_KEY=your_key_here" | sudo -u showrunner tee /opt/showrunner/.env

# 5. Install and start the systemd unit
sudo cp deploy/showrunner.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now showrunner

# 6. Configure nginx
sudo cp deploy/nginx.conf /etc/nginx/sites-available/showrunner
# Edit /etc/nginx/sites-available/showrunner: replace 'your.domain.here' with your domain
sudo ln -s /etc/nginx/sites-available/showrunner /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# 7. Provision TLS (requires DNS pointing at the instance)
sudo certbot --nginx -d your.domain.here
```

State files live at `/opt/showrunner/state/`. Back up `party_stats.yaml` and
`scene_state.yaml` before deploying updates.
