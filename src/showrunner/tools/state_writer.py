# ABOUTME: State writer — persists agent-resolved updates to YAML/Markdown state files.
# ABOUTME: Scribe agent is the only caller; all writes go through here.

from pathlib import Path

import yaml


def _deep_merge(base: dict, update: dict) -> dict:
    """Recursively merge update into base. Nested dicts are merged, not replaced."""
    result = dict(base)
    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def update_party_stats(updates: dict, path: str = "state/party_stats.yaml") -> None:
    """Deep-merge updates into party_stats.yaml. Existing keys not in updates are preserved."""
    p = Path(path)
    current: dict = {}
    if p.exists():
        with open(p) as f:
            current = yaml.safe_load(f) or {}
    current = _deep_merge(current, updates)
    with open(p, "w") as f:
        yaml.dump(current, f, allow_unicode=True, sort_keys=False)


def update_scene_state(updates: dict, path: str = "state/scene_state.yaml") -> None:
    """Deep-merge updates into scene_state.yaml. Existing keys not in updates are preserved."""
    p = Path(path)
    current: dict = {}
    if p.exists():
        with open(p) as f:
            current = yaml.safe_load(f) or {}
    current = _deep_merge(current, updates)
    with open(p, "w") as f:
        yaml.dump(current, f, allow_unicode=True, sort_keys=False)


def append_session_log(entry: str, path: str = "state/session_log.md") -> None:
    """Append an entry to session_log.md, creating the file if it does not exist."""
    with open(path, "a") as f:
        f.write(entry + "\n")


def initialize_scene_state(n: int, first_beat_id: str, state_dir: str = "state") -> None:
    """Write a fresh scene_state.yaml for the start of scene n."""
    state = {
        "current_scene": n,
        "current_beat": first_beat_id,
        "ticking_clocks": [],
        "character_plans": {},
    }
    path = Path(state_dir) / "scene_state.yaml"
    with open(path, "w") as f:
        yaml.dump(state, f, allow_unicode=True, sort_keys=False)


def advance_beat(beat_id: str, state_dir: str = "state") -> None:
    """Update current_beat in scene_state.yaml, preserving all other fields."""
    update_scene_state({"current_beat": beat_id}, path=str(Path(state_dir) / "scene_state.yaml"))
