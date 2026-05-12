# ABOUTME: State writer — persists agent-resolved updates to YAML/Markdown state files.
# ABOUTME: Scribe agent is the only caller; all writes go through here.

# TODO(Phase 3): Implement write functions with atomic updates (write to temp, rename).


def update_party_stats(updates: dict, path: str = "state/party_stats.yaml") -> None:
    raise NotImplementedError


def update_scene_state(updates: dict, path: str = "state/scene_state.yaml") -> None:
    raise NotImplementedError


def append_session_log(entry: str, path: str = "state/session_log.md") -> None:
    raise NotImplementedError
