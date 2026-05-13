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


def initialize_scene_state(scene: dict, state_dir: str = "state") -> None:
    """Write a fresh scene_state.yaml for the given scene, unless that scene is already loaded."""
    path = Path(state_dir) / "scene_state.yaml"
    scene_id = scene["scene_id"]
    if path.exists():
        with open(path) as f:
            existing = yaml.safe_load(f) or {}
        if existing.get("scene_id") == scene_id:
            return
    state = {
        "scene_id": scene_id,
        "current_beat": scene["beats"][0]["id"],
        "npc_knowledge": {},
        "flags": {},
        "last_actions": {},
        "ticking_clocks": [],
        "character_plans": {},
    }
    with open(path, "w") as f:
        yaml.dump(state, f, allow_unicode=True, sort_keys=False)


def advance_beat(beat_id: str, state_dir: str = "state") -> None:
    """Update current_beat in scene_state.yaml, preserving all other fields."""
    update_scene_state({"current_beat": beat_id}, path=str(Path(state_dir) / "scene_state.yaml"))
