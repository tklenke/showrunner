# ABOUTME: CrewAI tool definitions for showrunner agents — dice rolling, state I/O, player input.
# ABOUTME: Wraps dice_roller, state_reader, and state_writer for use by CrewAI agents.

import json
from pathlib import Path

from crewai.tools import BaseTool, tool
from pydantic import BaseModel, field_validator

from showrunner.tools.dice_roller import roll_pool
from showrunner.tools.state_reader import load_party_stats, load_scene_state
from showrunner.tools.state_writer import append_session_log, update_party_stats, update_scene_state

_STATE_DIR = Path("state")


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


class _ConsultNarratorInput(BaseModel):
    question: str

    @field_validator("question", mode="before")
    @classmethod
    def unwrap_schema(cls, v):
        """Extract actual question when a small model passes a JSON Schema object."""
        if isinstance(v, dict) and "properties" in v:
            props = v["properties"]
            if isinstance(props, dict) and "question" in props:
                inner = props["question"]
                if isinstance(inner, str):
                    return inner
        return v


class _ConsultNarratorTool(BaseTool):
    name: str = "consult_narrator"
    description: str = (
        "Escalate an ambiguous decision to the Narrator (Gemini). "
        "Use sparingly — only for genuine plot or rules ambiguity that the local model "
        "cannot resolve confidently. Each call incurs a Gemini API request."
    )
    args_schema: type[BaseModel] = _ConsultNarratorInput

    def _run(self, question: str) -> str:
        return (
            "The Narrator is not available for direct consultation at this time. "
            "Proceed with your best judgment based on the scene context provided."
        )


consult_narrator = _ConsultNarratorTool()


class _ReadStateInput(BaseModel):
    filename: str

    @field_validator("filename", mode="before")
    @classmethod
    def unwrap_schema(cls, v):
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
        path = _STATE_DIR / filename
        try:
            with open(path) as f:
                return f.read()
        except FileNotFoundError:
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
        update_scene_state(updates, path=path)
    elif "session_log" in file:
        entry = updates.get("entry", "")
        append_session_log(entry, path=path)
    else:
        raise ValueError(f"Unknown state file: {file}")
    return f"Updated {file}"
