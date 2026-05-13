# ABOUTME: Tests for Referee agent — Phase 4 inline rules system prompt.
# ABOUTME: Verifies the backstory string contains the rules the Referee needs for the Bargos scene.


def test_referee_system_prompt_contains_pool_construction_rule():
    from showrunner.agents.referee import build_referee_backstory
    backstory = build_referee_backstory()
    assert "max" in backstory and "min" in backstory


def test_referee_system_prompt_contains_soak_rule():
    from showrunner.agents.referee import build_referee_backstory
    backstory = build_referee_backstory()
    assert "soak" in backstory.lower()


def test_referee_system_prompt_contains_minion_wound_rule():
    from showrunner.agents.referee import build_referee_backstory
    backstory = build_referee_backstory()
    assert "minion" in backstory.lower() or "wound threshold" in backstory.lower()


SCENE = {
    "minion_groups": [
        {
            "name": "Renegade Gamorrean Guards",
            "count": 6,
            "soak": 4,
            "wound_threshold": 5,
            "characteristics": {"brawn": 3, "agility": 2},
            "skills": {"melee": 1, "brawl": 1},
            "weapons": [
                {
                    "name": "Vibro-Axe",
                    "damage": 5,
                    "critical": 3,
                    "range": "Engaged",
                    "special": "Vicious 2",
                }
            ],
        }
    ],
    "beats": [
        {
            "id": "audience",
            "title": "The Job",
            "checks": [
                {
                    "skill": "Negotiation",
                    "characteristic": "Presence",
                    "difficulty": 2,
                    "opposed_skill": "Cool",
                    "notes": "PCs may attempt to negotiate better terms.",
                }
            ],
        },
        {
            "id": "no_checks",
            "title": "Empty Beat",
            "checks": [],
        },
    ],
}


def test_referee_context_includes_beat_checks():
    from showrunner.agents.referee import render_referee_context
    output = render_referee_context(SCENE, "audience")
    assert "Negotiation" in output
    assert "Presence" in output


def test_referee_context_includes_check_notes():
    from showrunner.agents.referee import render_referee_context
    output = render_referee_context(SCENE, "audience")
    assert "negotiate better terms" in output


def test_referee_context_empty_checks_renders_cleanly():
    from showrunner.agents.referee import render_referee_context
    output = render_referee_context(SCENE, "no_checks")
    assert "Checks This Beat" in output


def test_referee_context_includes_minion_group_stats():
    from showrunner.agents.referee import render_referee_context
    output = render_referee_context(SCENE, "audience")
    assert "Renegade Gamorrean Guards" in output
    assert "count: 6" in output
    assert "soak: 4" in output


def test_referee_context_includes_minion_weapons():
    from showrunner.agents.referee import render_referee_context
    output = render_referee_context(SCENE, "audience")
    assert "Vibro-Axe" in output
    assert "damage 5" in output


def test_referee_context_no_minion_groups_renders_cleanly():
    from showrunner.agents.referee import render_referee_context
    scene_no_minions = {"minion_groups": [], "beats": SCENE["beats"]}
    output = render_referee_context(scene_no_minions, "audience")
    assert "Minion Groups" in output
