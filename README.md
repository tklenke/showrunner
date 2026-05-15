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

Beat advancement is decided automatically by the Show Runner after each turn. The SR
reads what happened against the next beat's entry condition and outputs `ADVANCE` or `STAY`.
When it advances, NPC and companion plans for the next turn are written with the new beat
context so characters react to where the story actually is.

---

## Setup

```bash
git clone git@github.com:tklenke/showrunner.git
cd showrunner
python3.11 -m venv venv
source venv/bin/activate
pip install -e .
pip install -r requirements.txt
```

Set your Gemini API key:

```bash
# Either export it:
export GEMINI_API_KEY=your_key_here

# Or add it to a .env file (loaded automatically on startup):
echo "GEMINI_API_KEY=your_key_here" > .env
```

---

## Web App

The primary interface. Start the server:

```bash
source venv/bin/activate
uvicorn showrunner.web.app:create_server_app --factory --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000` in a browser.

**During a session:**

- Narrative prose streams in and renders as markdown
- When a skill check is needed, the dice pool is displayed — enter a result (e.g. `S2A1T1`) or leave the field blank and click **Auto-roll**
- When it's your turn, type your action and press Enter or **Send**
- Type `q` to end the session

Single-session: opening a second tab cancels the first connection.

**Scene selection:** set `APP_SCENE=1` (etc.) to load a different scene:

```bash
APP_SCENE=1 uvicorn showrunner.web.app:create_server_app --factory --host 0.0.0.0 --port 8000
```

---

## CLI

The terminal interface — useful for dev and debugging:

```bash
source venv/bin/activate
python -m showrunner.main           # scene 0 (default)
python -m showrunner.main 1        # scene 1
python -m showrunner.main --reset  # clear state and restart from beat 1
python -m showrunner.main --dump-prompts  # write full LLM calls to logs/prompts/
```

**`--reset`** deletes `state/scene_state.yaml`, `state/session_log.md`, and everything
under `logs/`. `state/party_stats.yaml` is preserved — delete it manually for fully
clean wound/strain tracking.

**`--dump-prompts`** writes one Markdown file per LLM call to `logs/prompts/`:

```
logs/prompts/0001_narrator_run_beat_opener.md
logs/prompts/0002_actors_run_npc_wave[bargos_the_hutt].md
```

Each file contains the full `# System`, `# User`, and `# Response` text. A summary log
is always written to `logs/prompts_<timestamp>.log`:

```
0001  14:32:01  narrator  sardinia  run_beat_opener                1842p →  312r
0002  14:32:04  actors    sardinia  run_npc_wave[bargos_the_hutt]  2103p →  445r
```

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
sudo -u showrunner git clone git@github.com:tklenke/showrunner.git /opt/showrunner
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
# Edit the file: replace 'your.domain.here' with your actual domain
sudo ln -s /etc/nginx/sites-available/showrunner /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# 7. Provision TLS (requires DNS pointing at the instance)
sudo certbot --nginx -d your.domain.here
```

State files live at `/opt/showrunner/state/`. Back up `party_stats.yaml` and
`scene_state.yaml` before deploying updates.

To load a scene other than scene 0, add `Environment=APP_SCENE=1` to the
`[Service]` section of the systemd unit.
