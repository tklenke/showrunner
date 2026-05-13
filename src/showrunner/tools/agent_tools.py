# ABOUTME: CrewAI tool definitions for showrunner agents — dice rolling, state I/O, player input.
# ABOUTME: Wraps dice_roller, state_reader, and state_writer for use by CrewAI agents.

import json
from pathlib import Path

from crewai.tools import BaseTool, tool
from pydantic import BaseModel, field_validator, model_validator

from showrunner.tools.dice_roller import roll_pool
from showrunner.tools.state_reader import load_party_stats, load_scene_state
from showrunner.tools.state_writer import append_session_log, update_party_stats, update_scene_state

_STATE_DIR = Path("state")


def _unwrap_schema_args(data: dict) -> dict:
    """Unwrap top-level JSON Schema wrapper that 3B models pass instead of actual args.

    Models sometimes emit {'properties': {'field': 'value'}, 'additionalProperties': False}
    instead of {'field': 'value'}. Extract the inner properties dict when this is detected.
    String field values are kept; non-string values (schema sub-objects) fall back to ''.
    """
    if isinstance(data, dict) and "properties" in data:
        props = data["properties"]
        if isinstance(props, dict):
            return {k: v if isinstance(v, str) else "" for k, v in props.items()}
    return data


@tool("roll_dice")
def roll_dice(pool_json: str) -> str:
    """Roll a Genesys narrative dice pool.

    Input: JSON object with keys proficiency, ability, difficulty, challenge, boost, setback.
    Returns a plain-text summary of the roll result.
    """
    try:
        pool = json.loads(pool_json)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"pool_json must be a valid JSON object: {exc}") from exc
    result = roll_pool(pool)
    outcome = "passed" if result.passed else "failed"
    parts = [f"Roll {outcome}: net {result.net_successes:+d} successes, "
             f"{result.net_advantage:+d} advantage"]
    if result.triumphs:
        parts.append(f"{result.triumphs} Triumph(s)")
    if result.despairs:
        parts.append(f"{result.despairs} Despair(s)")
    return " | ".join(parts)


@tool("ask_player")
def ask_player(question: str) -> str:
    """Prompt Tom at the CLI for a decision or action.

    Blocks until Tom types a response. Use only for genuine player decisions,
    not for routine narration.
    """
    return input(f"\n[Player] {question}\n> ")


class _ConsultShowRunnerInput(BaseModel):
    question: str

    @model_validator(mode="before")
    @classmethod
    def unwrap_top_level(cls, data):
        return _unwrap_schema_args(data)

    @field_validator("question", mode="before")
    @classmethod
    def unwrap_field(cls, v):
        """Extract actual question when a small model passes a JSON Schema object."""
        if isinstance(v, dict) and "properties" in v:
            props = v["properties"]
            if isinstance(props, dict) and "question" in props:
                inner = props["question"]
                if isinstance(inner, str):
                    return inner
        return v


class _ConsultShowRunnerTool(BaseTool):
    name: str = "consult_show_runner"
    description: str = (
        "Escalate an ambiguous decision to the Show Runner (Gemini). "
        "Use sparingly — only for genuine plot or rules ambiguity that the local model "
        "cannot resolve confidently. Each call incurs a Gemini API request."
    )
    args_schema: type[BaseModel] = _ConsultShowRunnerInput

    def _run(self, question: str) -> str:
        return (
            "The Show Runner is not available for direct consultation at this time. "
            "Proceed with your best judgment based on the scene context provided."
        )


consult_show_runner = _ConsultShowRunnerTool()


class _ReadStateInput(BaseModel):
    filename: str

    @model_validator(mode="before")
    @classmethod
    def unwrap_top_level(cls, data):
        return _unwrap_schema_args(data)

    @field_validator("filename", mode="before")
    @classmethod
    def unwrap_field(cls, v):
        """Extract actual filename when a small model passes a JSON Schema object."""
        if isinstance(v, dict) and "properties" in v:
            props = v["properties"]
            if isinstance(props, dict) and "filename" in props:
                inner = props["filename"]
                if isinstance(inner, str):
                    return inner
        return v


class _ReadStateTool(BaseTool):
    name: str = "read_state"
    description: str = (
        "Read a state file (scene_state.yaml, party_stats.yaml, or session_log.md). "
        "Returns the file contents as a string. Available to all agents."
    )
    args_schema: type[BaseModel] = _ReadStateInput

    def _run(self, filename: str) -> str:
        if not filename:
            return "State file name not provided."
        path = _STATE_DIR / filename
        try:
            with open(path) as f:
                return f.read()
        except OSError:
            return f"State file '{filename}' not found."


read_state = _ReadStateTool()


@tool("write_state")
def write_state(file: str, updates: dict) -> str:
    """Write updates to a state file. Scribe agent only.

    file: the state filename (party_stats.yaml or scene_state.yaml).
    updates: dict of key/value changes to merge into the file.
    """
    path = str(_STATE_DIR / file)
    if "party_stats" in file:
        update_party_stats(updates, path=path)
    elif "scene_state" in file:
        safe_updates = {k: v for k, v in updates.items() if k != "current_beat"}
        if safe_updates:
            update_scene_state(safe_updates, path=path)
    elif "session_log" in file:
        entry = updates.get("entry", "")
        append_session_log(entry, path=path)
    else:
        raise ValueError(f"Unknown state file: {file}")
    return f"Updated {file}"
