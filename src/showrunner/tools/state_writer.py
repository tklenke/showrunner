# ABOUTME: State writer — persists agent-resolved updates to YAML/Markdown state files.
# ABOUTME: Scribe agent is the only caller; all writes go through here.

from pathlib import Path

import yaml


def update_party_stats(updates: dict, path: str = "state/party_stats.yaml") -> None:
    """Merge updates into party_stats.yaml. Existing keys not in updates are preserved."""
    p = Path(path)
    current: dict = {}
    if p.exists():
        with open(p) as f:
            current = yaml.safe_load(f) or {}
    current.update(updates)
    with open(p, "w") as f:
        yaml.dump(current, f, allow_unicode=True, sort_keys=False)


def update_scene_state(updates: dict, path: str = "state/scene_state.yaml") -> None:
    """Merge updates into scene_state.yaml. Existing keys not in updates are preserved."""
    p = Path(path)
    current: dict = {}
    if p.exists():
        with open(p) as f:
            current = yaml.safe_load(f) or {}
    current.update(updates)
    with open(p, "w") as f:
        yaml.dump(current, f, allow_unicode=True, sort_keys=False)


def append_session_log(entry: str, path: str = "state/session_log.md") -> None:
    """Append an entry to session_log.md, creating the file if it does not exist."""
    with open(path, "a") as f:
        f.write(entry + "\n")
