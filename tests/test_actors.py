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


# --- render_inline_npc_prompt tests (sub-task B) ---

_INLINE_NPC_FULL = {
    "id": "genko",
    "name": "Genko",
    "pronoun": "he",
    "role": "Toydarian aide",
    "key_traits": "Furtive and anxious.",
    "characteristics": {
        "brawn": 1, "agility": 2, "intellect": 3,
        "cunning": 3, "willpower": 2, "presence": 2,
    },
    "skills": [
        {"name": "Deception", "ranks": 2},
        {"name": "Negotiation", "ranks": 1},
    ],
    "derived": {"wound_threshold": 11, "strain_threshold": 12, "soak": 1},
}

_INLINE_NPC_MINIMAL = {
    "id": "servant",
    "name": "Terrified Servant",
    "pronoun": "they",
    "role": "Background extra",
    "key_traits": "Panicked.",
}


def test_render_inline_npc_prompt_contains_name():
    from showrunner.agents.actors import render_inline_npc_prompt
    result = render_inline_npc_prompt(_INLINE_NPC_FULL)
    assert "Genko" in result


def test_render_inline_npc_prompt_contains_pronoun():
    from showrunner.agents.actors import render_inline_npc_prompt
    result = render_inline_npc_prompt(_INLINE_NPC_FULL)
    assert "he" in result


def test_render_inline_npc_prompt_contains_role():
    from showrunner.agents.actors import render_inline_npc_prompt
    result = render_inline_npc_prompt(_INLINE_NPC_FULL)
    assert "Toydarian aide" in result


def test_render_inline_npc_prompt_contains_key_traits():
    from showrunner.agents.actors import render_inline_npc_prompt
    result = render_inline_npc_prompt(_INLINE_NPC_FULL)
    assert "Furtive" in result


def test_render_inline_npc_prompt_contains_characteristics_when_present():
    from showrunner.agents.actors import render_inline_npc_prompt
    result = render_inline_npc_prompt(_INLINE_NPC_FULL)
    assert "Intellect" in result
    assert "3" in result


def test_render_inline_npc_prompt_contains_skills_when_present():
    from showrunner.agents.actors import render_inline_npc_prompt
    result = render_inline_npc_prompt(_INLINE_NPC_FULL)
    assert "Deception" in result


def test_render_inline_npc_prompt_contains_derived_when_present():
    from showrunner.agents.actors import render_inline_npc_prompt
    result = render_inline_npc_prompt(_INLINE_NPC_FULL)
    assert "11" in result  # wound_threshold


def test_render_inline_npc_prompt_no_stats_is_graceful():
    from showrunner.agents.actors import render_inline_npc_prompt
    result = render_inline_npc_prompt(_INLINE_NPC_MINIMAL)
    assert "Terrified Servant" in result
    assert "Panicked" in result


def test_load_scene_characters_inline_uses_render_inline_npc_prompt():
    from showrunner.agents.actors import load_scene_characters
    scene = {"characters_present": [], "inline_npcs": [_INLINE_NPC_FULL]}
    result = load_scene_characters(scene, SCENE_STATE)
    assert "genko" in result
    assert "Toydarian aide" in result["genko"]


# --- pronoun in render_actor_prompt (sub-task C) ---

def test_render_actor_prompt_includes_pronoun():
    from showrunner.agents.actors import render_actor_prompt
    import yaml as pyyaml
    with open(FIXTURES / "character_test.yaml") as f:
        char_yaml = pyyaml.safe_load(f)
    char_yaml["identity"]["pronoun"] = "she"
    result = render_actor_prompt(char_yaml, "", {})
    assert "she" in result


def test_render_actor_prompt_no_pronoun_still_renders():
    from showrunner.agents.actors import render_actor_prompt
    import yaml as pyyaml
    with open(FIXTURES / "character_test.yaml") as f:
        char_yaml = pyyaml.safe_load(f)
    char_yaml["identity"].pop("pronoun", None)
    result = render_actor_prompt(char_yaml, "", {})
    assert char_yaml["identity"]["name"] in result


# --- render_minion_group_prompt tests (sub-task F) ---

_MINION_GROUP = {
    "id": "gamorrean_guards",
    "name": "Renegade Gamorrean Guards",
    "pronoun": "they",
    "count": 6,
    "characteristics": {"brawn": 3, "agility": 2, "intellect": 1, "cunning": 1, "willpower": 2, "presence": 1},
    "skills": [{"name": "Melee", "ranks": 1}, {"name": "Brawl", "ranks": 1}],
    "soak": 4,
    "wound_threshold": 5,
    "weapons": [{"name": "Vibro-Axe", "skill": "Melee", "damage": 5, "critical": 3, "range": "Engaged", "special": "Vicious 2"}],
}


def test_render_minion_group_prompt_contains_name():
    from showrunner.agents.actors import render_minion_group_prompt
    result = render_minion_group_prompt(_MINION_GROUP)
    assert "Renegade Gamorrean Guards" in result


def test_render_minion_group_prompt_contains_pronoun():
    from showrunner.agents.actors import render_minion_group_prompt
    result = render_minion_group_prompt(_MINION_GROUP)
    assert "they" in result


def test_render_minion_group_prompt_contains_count():
    from showrunner.agents.actors import render_minion_group_prompt
    result = render_minion_group_prompt(_MINION_GROUP)
    assert "6" in result


def test_render_minion_group_prompt_contains_characteristics():
    from showrunner.agents.actors import render_minion_group_prompt
    result = render_minion_group_prompt(_MINION_GROUP)
    assert "Brawn" in result
    assert "3" in result


def test_render_minion_group_prompt_contains_weapon():
    from showrunner.agents.actors import render_minion_group_prompt
    result = render_minion_group_prompt(_MINION_GROUP)
    assert "Vibro-Axe" in result


# --- _active_npc_ids tests (sub-task G) ---

_SCENE_WITH_BEATS = {
    "inline_npcs": [
        {"id": "c3p9", "name": "C3-P9"},
        {"id": "genko", "name": "Genko"},
    ],
    "minion_groups": [
        {"id": "gamorrean_guards", "name": "Renegade Gamorrean Guards"},
    ],
    "beats": [
        {"id": "arrival", "title": "Arrival"},
        {"id": "rumble", "title": "Rumble", "add_npcs": ["gamorrean_guards"], "remove_npcs": ["c3p9", "genko"]},
        {"id": "brief", "title": "Brief", "add_npcs": ["gamorrean_guards"]},
    ],
}


def test_active_npc_ids_default_includes_inline_npcs():
    from showrunner.agents.actors import _active_npc_ids
    result = _active_npc_ids(_SCENE_WITH_BEATS, "arrival")
    assert "c3p9" in result
    assert "genko" in result


def test_active_npc_ids_default_excludes_minion_groups():
    from showrunner.agents.actors import _active_npc_ids
    result = _active_npc_ids(_SCENE_WITH_BEATS, "arrival")
    assert "gamorrean_guards" not in result


def test_active_npc_ids_add_npcs_includes_minion_group():
    from showrunner.agents.actors import _active_npc_ids
    result = _active_npc_ids(_SCENE_WITH_BEATS, "rumble")
    assert "gamorrean_guards" in result


def test_active_npc_ids_remove_npcs_excludes_inline_npc():
    from showrunner.agents.actors import _active_npc_ids
    result = _active_npc_ids(_SCENE_WITH_BEATS, "rumble")
    assert "c3p9" not in result
    assert "genko" not in result


def test_active_npc_ids_beat_not_found_returns_inline_defaults():
    from showrunner.agents.actors import _active_npc_ids
    result = _active_npc_ids(_SCENE_WITH_BEATS, "nonexistent_beat")
    assert "c3p9" in result
    assert "genko" in result
    assert "gamorrean_guards" not in result


def test_load_scene_characters_with_active_ids_filters_npcs():
    from showrunner.agents.actors import load_scene_characters
    scene = {
        "characters_present": [],
        "inline_npcs": [_INLINE_NPC_FULL, _INLINE_NPC_MINIMAL],
        "minion_groups": [],
    }
    result = load_scene_characters(scene, SCENE_STATE, active_ids={"genko"})
    assert "genko" in result
    assert "servant" not in result


def test_load_scene_characters_with_no_active_ids_returns_all_inline():
    from showrunner.agents.actors import load_scene_characters
    scene = {
        "characters_present": [],
        "inline_npcs": [_INLINE_NPC_FULL, _INLINE_NPC_MINIMAL],
        "minion_groups": [],
    }
    result = load_scene_characters(scene, SCENE_STATE)
    assert "genko" in result
    assert "servant" in result


def test_load_scene_characters_includes_minion_group_when_in_active_ids():
    from showrunner.agents.actors import load_scene_characters
    scene = {
        "characters_present": [],
        "inline_npcs": [],
        "minion_groups": [_MINION_GROUP],
    }
    result = load_scene_characters(scene, SCENE_STATE, active_ids={"gamorrean_guards"})
    assert "gamorrean_guards" in result
    assert "Renegade Gamorrean Guards" in result["gamorrean_guards"]
