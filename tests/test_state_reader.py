# ABOUTME: Tests for state_reader — loading character, scene state, and party stats YAML files.
# ABOUTME: Uses fixture files in tests/fixtures/ to avoid depending on live state/ or characters/.

import pytest
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_character_returns_dict():
    from showrunner.tools.state_reader import load_character
    result = load_character("character_test", characters_dir=str(FIXTURES))
    assert isinstance(result, dict)


def test_load_character_has_required_keys():
    from showrunner.tools.state_reader import load_character
    result = load_character("character_test", characters_dir=str(FIXTURES))
    for key in ("identity", "characteristics", "skills", "status"):
        assert key in result, f"missing key: {key}"


def test_load_scene_state():
    from showrunner.tools.state_reader import load_scene_state
    result = load_scene_state(str(FIXTURES / "scene_state_test.yaml"))
    assert isinstance(result, dict)
    assert "location" in result


def test_load_party_stats():
    from showrunner.tools.state_reader import load_party_stats
    result = load_party_stats(str(FIXTURES / "party_stats_test.yaml"))
    assert isinstance(result, dict)
    assert "characters" in result


def test_load_missing_file_raises():
    from showrunner.tools.state_reader import load_character
    with pytest.raises(FileNotFoundError):
        load_character("nonexistent_character", characters_dir=str(FIXTURES))
