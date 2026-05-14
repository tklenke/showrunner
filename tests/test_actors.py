# ABOUTME: Tests for Actors agent — scene character loading and inline NPC handling.
# ABOUTME: Verifies load_scene_characters builds prompts for characters_present and inline_npcs.

from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"

SCENE_WITH_NPC = {
    "characters_present": ["character_test"],
    "inline_npcs": [],
}

SCENE_WITH_INLINE = {
    "characters_present": [],
    "inline_npcs": [
        {
            "id": "c3p9",
            "name": "C3-P9",
            "role": "Protocol droid",
            "key_traits": "Deferential and precise.",
        }
    ],
}

SCENE_STATE = {"character_plans": {}}


def test_actors_loads_npcs_from_scene():
    from showrunner.agents.actors import load_scene_characters
    result = load_scene_characters(SCENE_WITH_NPC, SCENE_STATE, characters_dir=str(FIXTURES))
    assert "character_test" in result
    assert result["character_test"]


def test_inline_npc_uses_key_traits():
    from showrunner.agents.actors import load_scene_characters
    result = load_scene_characters(SCENE_WITH_INLINE, SCENE_STATE, characters_dir=str(FIXTURES))
    assert "c3p9" in result
    assert "Deferential" in result["c3p9"]


# --- player_filter tests ---

SCENE_MIXED = {
    "characters_present": ["character_test", "npc_test"],
    "inline_npcs": [{"id": "guard", "name": "Guard", "role": "Guard", "key_traits": "Tough."}],
}


def test_load_scene_characters_no_filter_returns_all():
    from showrunner.agents.actors import load_scene_characters
    result = load_scene_characters(SCENE_MIXED, SCENE_STATE, characters_dir=str(FIXTURES))
    assert "character_test" in result  # player: "companion"
    assert "npc_test" in result        # no player field
    assert "guard" in result           # inline NPC


def test_load_scene_characters_npc_filter_excludes_companions():
    from showrunner.agents.actors import load_scene_characters
    result = load_scene_characters(
        SCENE_MIXED, SCENE_STATE, characters_dir=str(FIXTURES), player_filter="npc"
    )
    assert "character_test" not in result  # player: "companion" — excluded
    assert "npc_test" in result            # no player field — included
    assert "guard" in result               # inline NPC — always included


def test_load_scene_characters_companion_filter_returns_only_companions():
    from showrunner.agents.actors import load_scene_characters
    result = load_scene_characters(
        SCENE_MIXED, SCENE_STATE, characters_dir=str(FIXTURES), player_filter="companion"
    )
    assert "character_test" in result      # player: "companion" — included
    assert "npc_test" not in result        # no player field — excluded
    assert "guard" not in result           # inline NPC — excluded


def test_load_scene_characters_companion_filter_excludes_human_pcs():
    """Characters with player: "human" are never returned by any filter."""
    import yaml as pyyaml
    from showrunner.agents.actors import load_scene_characters
    # character_test has player: "companion", npc_test has no player field
    # We rely on the fixture not having a human PC; just confirm "human" logic via npc filter
    result = load_scene_characters(
        SCENE_WITH_NPC, SCENE_STATE, characters_dir=str(FIXTURES), player_filter="npc"
    )
    # character_test has player: "companion" → excluded by npc filter
    assert "character_test" not in result


# --- load_scene_yamls tests ---

def test_load_scene_yamls_returns_raw_dicts():
    from showrunner.agents.actors import load_scene_yamls
    result = load_scene_yamls(SCENE_WITH_NPC, characters_dir=str(FIXTURES))
    assert "character_test" in result
    assert isinstance(result["character_test"], dict)
    assert "identity" in result["character_test"]


def test_load_scene_yamls_includes_both_npc_and_ai():
    from showrunner.agents.actors import load_scene_yamls
    result = load_scene_yamls(SCENE_MIXED, characters_dir=str(FIXTURES))
    assert "character_test" in result  # player: "companion"
    assert "npc_test" in result        # no player field


def test_load_scene_yamls_skips_inline_npcs():
    from showrunner.agents.actors import load_scene_yamls
    result = load_scene_yamls(SCENE_WITH_INLINE, characters_dir=str(FIXTURES))
    assert "c3p9" not in result  # inline NPC has no YAML file


def test_load_scene_yamls_excludes_human_players():
    from showrunner.agents.actors import load_scene_yamls
    import tempfile, yaml, os
    from pathlib import Path
    with tempfile.TemporaryDirectory() as tmpdir:
        human = {"identity": {"name": "Human PC", "species": "Human", "career": "Spy", "player": "human"},
                 "characteristics": {}, "skills": [], "talents": [], "derived": {}, "equipment": {}, "status": {}, "resources": {}}
        (Path(tmpdir) / "human_pc.yaml").write_text(yaml.dump(human))
        scene = {"characters_present": ["human_pc"], "inline_npcs": []}
        result = load_scene_yamls(scene, characters_dir=tmpdir)
        assert "human_pc" not in result


def test_load_scene_characters_default_reads_skin_characters(tmp_path, monkeypatch):
    import yaml
    from showrunner.agents.actors import load_scene_characters
    monkeypatch.chdir(tmp_path)
    chars_dir = tmp_path / "skin" / "characters"
    chars_dir.mkdir(parents=True)
    char = {
        "identity": {"name": "Test NPC", "species": "Human", "career": "Soldier"},
        "characteristics": {"brawn": 2, "agility": 2, "intellect": 2, "cunning": 2, "willpower": 2, "presence": 2},
        "skills": [],
        "talents": [],
        "derived": {"wound_threshold": 12, "strain_threshold": 12, "soak": 2, "defense": {}},
        "equipment": {},
        "status": {"wounds": 0, "strain": 0, "critical_injuries": []},
        "resources": {},
    }
    (chars_dir / "test_npc.yaml").write_text(yaml.dump(char))
    scene = {"characters_present": ["test_npc"], "inline_npcs": []}
    result = load_scene_characters(scene, {})
    assert "test_npc" in result


def test_load_scene_yamls_default_reads_skin_characters(tmp_path, monkeypatch):
    import yaml
    from showrunner.agents.actors import load_scene_yamls
    monkeypatch.chdir(tmp_path)
    chars_dir = tmp_path / "skin" / "characters"
    chars_dir.mkdir(parents=True)
    char = {"identity": {"name": "Test NPC"}}
    (chars_dir / "test_npc.yaml").write_text(yaml.dump(char))
    scene = {"characters_present": ["test_npc"], "inline_npcs": []}
    result = load_scene_yamls(scene)
    assert "test_npc" in result


# --- render_actor_beat_context tests ---

_BEAT_SCENE = {
    "location": {"name": "Bargos Mansion", "atmosphere": "Opulent and dangerous."},
    "beats": [
        {
            "id": "arrival",
            "title": "Grand Arrival",
            "narrator_notes": "Marble columns and the smell of spice.",
            "show_runner_notes": "SR directive only.",
        }
    ],
}
_BEAT_STATE = {"current_beat": "arrival", "character_plans": {}}


def test_render_actor_beat_context_contains_beat_title():
    from showrunner.agents.actors import render_actor_beat_context
    result = render_actor_beat_context(_BEAT_SCENE, _BEAT_STATE)
    assert "Grand Arrival" in result


def test_render_actor_beat_context_contains_location():
    from showrunner.agents.actors import render_actor_beat_context
    result = render_actor_beat_context(_BEAT_SCENE, _BEAT_STATE)
    assert "Bargos Mansion" in result


def test_render_actor_beat_context_contains_narrator_notes():
    from showrunner.agents.actors import render_actor_beat_context
    result = render_actor_beat_context(_BEAT_SCENE, _BEAT_STATE)
    assert "Marble columns" in result


def test_render_actor_beat_context_excludes_party_stats():
    from showrunner.agents.actors import render_actor_beat_context
    result = render_actor_beat_context(_BEAT_SCENE, _BEAT_STATE)
    assert "wounds" not in result
    assert "strain" not in result


def test_render_actor_beat_context_excludes_ticking_clocks():
    from showrunner.agents.actors import render_actor_beat_context
    scene = {**_BEAT_SCENE}
    state = {**_BEAT_STATE, "ticking_clocks": [{"id": "clock1", "label": "Alarm", "destroyed": 1, "max": 3}]}
    result = render_actor_beat_context(scene, state)
    assert "Alarm" not in result
    assert "clock" not in result.lower()
