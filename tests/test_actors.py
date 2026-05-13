# ABOUTME: Tests for Actors agent — scene character loading and inline NPC handling.
# ABOUTME: Verifies load_scene_characters builds prompts for npcs_present and inline_npcs.

from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"

SCENE_WITH_NPC = {
    "npcs_present": ["character_test"],
    "inline_npcs": [],
}

SCENE_WITH_INLINE = {
    "npcs_present": [],
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


def test_create_actors_includes_context_in_backstory():
    import os
    os.environ.setdefault("GEMINI_API_KEY", "test-key")
    from showrunner.agents.actors import create_actors
    actor = create_actors(context="## Rix Vardan\nHired Gun, species Human.")
    assert "Rix Vardan" in actor.backstory


def test_create_actors_no_context_uses_base_backstory():
    import os
    os.environ.setdefault("GEMINI_API_KEY", "test-key")
    from showrunner.agents.actors import create_actors
    actor = create_actors()
    assert actor.backstory  # has some backstory even with no context
