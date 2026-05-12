# ABOUTME: State reader — loads YAML/Markdown state files from state/ into Python objects.
# ABOUTME: Read-only; all agents may call this. Write access is Scribe-only.

# TODO(Phase 3): Implement load functions for scene_state.yaml, party_stats.yaml, session_log.md.


def load_scene_state(path: str = "state/scene_state.yaml") -> dict:
    raise NotImplementedError


def load_party_stats(path: str = "state/party_stats.yaml") -> dict:
    raise NotImplementedError


def load_character(name: str, characters_dir: str = "characters") -> dict:
    raise NotImplementedError
