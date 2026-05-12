# showrunner
AI Agent Orchestration for RPG

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

## Running a Session

```bash
source venv/bin/activate
python -m showrunner.main
```

Loads `state/scene_0.yaml` by default (Bargos mansion, Act 1). To start on a different scene:

```bash
python -m showrunner.main 1   # scene_1.yaml
```

## Running Tests

```bash
source venv/bin/activate
pytest
```
