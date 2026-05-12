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
