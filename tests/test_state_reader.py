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


def test_load_adventure_scene_returns_dict():
    from showrunner.tools.state_reader import load_adventure_scene
    result = load_adventure_scene(0, state_dir=str(FIXTURES))
    assert isinstance(result, dict)


def test_load_adventure_scene_has_required_keys():
    from showrunner.tools.state_reader import load_adventure_scene
    result = load_adventure_scene(0, state_dir=str(FIXTURES))
    for key in ("scene_id", "title", "location", "beats", "exit"):
        assert key in result, f"missing key: {key}"


def test_load_adventure_scene_missing_file_raises():
    from showrunner.tools.state_reader import load_adventure_scene
    with pytest.raises(FileNotFoundError):
        load_adventure_scene(99, state_dir=str(FIXTURES))


def test_load_adventure_scene_default_reads_skin_scenes(tmp_path, monkeypatch):
    import yaml
    from showrunner.tools.state_reader import load_adventure_scene
    monkeypatch.chdir(tmp_path)
    scenes_dir = tmp_path / "skin" / "scenes"
    scenes_dir.mkdir(parents=True)
    (scenes_dir / "scene_0.yaml").write_text(yaml.dump({"scene_id": "test_scene"}))
    result = load_adventure_scene(0)
    assert result["scene_id"] == "test_scene"


def test_load_character_default_reads_skin_characters(tmp_path, monkeypatch):
    import yaml
    from showrunner.tools.state_reader import load_character
    monkeypatch.chdir(tmp_path)
    chars_dir = tmp_path / "skin" / "characters"
    chars_dir.mkdir(parents=True)
    (chars_dir / "test_char.yaml").write_text(yaml.dump({"identity": {"name": "Test"}}))
    result = load_character("test_char")
    assert result["identity"]["name"] == "Test"
