# ABOUTME: State reader — loads YAML/Markdown state files from state/ into Python objects.
# ABOUTME: Read-only; all agents may call this. Write access is Scribe-only.

from pathlib import Path

import yaml


def load_character(name: str, characters_dir: str = "characters") -> dict:
    """Load a character YAML file by name (without .yaml extension)."""
    path = Path(characters_dir) / f"{name}.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


def load_scene_state(path: str = "state/scene_state.yaml") -> dict:
    """Load the current scene state YAML."""
    with open(path) as f:
        return yaml.safe_load(f)


def load_party_stats(path: str = "state/party_stats.yaml") -> dict:
    """Load the party stats YAML."""
    with open(path) as f:
        return yaml.safe_load(f)
