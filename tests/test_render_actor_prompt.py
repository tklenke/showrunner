# ABOUTME: Tests for render_actor_prompt — verifies sort order and content of the NPC system prompt.
# ABOUTME: Exercises static-to-volatile ordering, skill descriptors, scene plan injection, and injury rendering.

import pytest

CHARACTER = {
    "identity": {
        "name": "Rix Vardan",
        "species": "Human",
        "career": "Hired Gun",
        "specialization": "Mercenary Soldier",
    },
    "characteristics": {
        "brawn": 3, "agility": 3, "intellect": 2,
        "cunning": 2, "willpower": 2, "presence": 2,
    },
    "derived": {
        "wound_threshold": 13,
        "strain_threshold": 12,
        "soak": 4,
        "defense": {"melee": 0, "ranged": 1},
    },
    "skills": [
        {"name": "Ranged (Heavy)", "characteristic": "Agility", "ranks": 2,
         "career": True, "descriptor": "you can put rounds on target in any conditions"},
    ],
    "talents": [
        {"name": "Toughened", "ranks": 2, "description": "Gain +2 wound threshold per rank."},
    ],
    "equipment": {
        "weapons": [{"name": "Blaster Rifle", "damage": 9, "critical": 3, "range": "Long"}],
        "armor": [{"name": "Laminate Armor", "soak_bonus": 1, "defense": 1}],
        "gear": [{"name": "Comlink"}],
    },
    "resources": {"credits": 750},
    "status": {"wounds": 5, "strain": 3, "critical_injuries": []},
}

PERSONA = "Rix is a no-nonsense soldier who keeps his mouth shut and his rifle clean."

SCENE_WITH_PLAN = {
    "location": "Receiving Hall",
    "character_plans": {"Rix Vardan": "Cover the exits"},
}

SCENE_WITHOUT_PLAN = {
    "location": "Receiving Hall",
}


def test_output_contains_character_name():
    from showrunner.agents.actors import render_actor_prompt
    output = render_actor_prompt(CHARACTER, PERSONA, SCENE_WITH_PLAN)
    assert "Rix Vardan" in output


def test_static_content_appears_before_dynamic():
    from showrunner.agents.actors import render_actor_prompt
    output = render_actor_prompt(CHARACTER, PERSONA, SCENE_WITH_PLAN)
    # Persona text must appear before wounds
    persona_pos = output.index("no-nonsense soldier")
    wounds_pos = output.index("Wounds:")
    assert persona_pos < wounds_pos


def test_skills_rendered_with_descriptors():
    from showrunner.agents.actors import render_actor_prompt
    output = render_actor_prompt(CHARACTER, PERSONA, SCENE_WITH_PLAN)
    assert "you can put rounds on target in any conditions" in output
    # Raw rank numbers should not appear alone — descriptor is the voice
    assert "ranks: 2" not in output


def test_active_critical_injuries_included():
    from showrunner.agents.actors import render_actor_prompt
    char = {**CHARACTER, "status": {**CHARACTER["status"],
                                    "critical_injuries": ["Blinded", "Staggered"]}}
    output = render_actor_prompt(char, PERSONA, SCENE_WITH_PLAN)
    assert "Blinded" in output
    assert "Staggered" in output


def test_no_critical_injuries_section_is_clean():
    from showrunner.agents.actors import render_actor_prompt
    # Empty list must not crash or produce malformed output
    output = render_actor_prompt(CHARACTER, PERSONA, SCENE_WITH_PLAN)
    assert output  # non-empty


def test_scene_plan_included_when_present():
    from showrunner.agents.actors import render_actor_prompt
    output = render_actor_prompt(CHARACTER, PERSONA, SCENE_WITH_PLAN)
    assert "Cover the exits" in output


def test_scene_plan_absent_when_missing():
    from showrunner.agents.actors import render_actor_prompt
    # Must not raise KeyError when scene_state has no character_plans
    output = render_actor_prompt(CHARACTER, PERSONA, SCENE_WITHOUT_PLAN)
    assert output
