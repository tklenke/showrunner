# ABOUTME: Tests for Scribe agent — context rendering for state-aware updates.
# ABOUTME: Verifies render_scribe_context produces correct starting-state snapshot for the Scribe.

SCENE_STATE = {
    "current_beat": "audience",
    "ticking_clocks": [{"name": "Escape window", "progress": 2, "max": 6}],
    "character_plans": {},
}

SCENE_STATE_NO_CLOCKS = {
    "current_beat": "summons",
    "ticking_clocks": [],
    "character_plans": {},
}

PARTY_STATS = {
    "characters": {
        "kaelen_sunara": {"wounds": 2, "strain": 1},
        "z_4p0": {"wounds": 0, "strain": 0},
    }
}


def test_scribe_context_includes_character_wounds():
    from showrunner.agents.scribe import render_scribe_context
    output = render_scribe_context(SCENE_STATE, PARTY_STATS)
    assert "kaelen_sunara" in output
    assert "wounds 2" in output
    assert "strain 1" in output


def test_scribe_context_includes_current_beat():
    from showrunner.agents.scribe import render_scribe_context
    output = render_scribe_context(SCENE_STATE, PARTY_STATS)
    assert "audience" in output


def test_scribe_context_warns_against_changing_beat():
    from showrunner.agents.scribe import render_scribe_context
    output = render_scribe_context(SCENE_STATE, PARTY_STATS)
    assert "DO NOT CHANGE" in output


def test_scribe_context_includes_ticking_clocks_when_present():
    from showrunner.agents.scribe import render_scribe_context
    output = render_scribe_context(SCENE_STATE, PARTY_STATS)
    assert "Escape window" in output


def test_scribe_context_no_clocks_renders_cleanly():
    from showrunner.agents.scribe import render_scribe_context
    output = render_scribe_context(SCENE_STATE_NO_CLOCKS, PARTY_STATS)
    assert "Ticking clocks" in output
    assert "none" in output.lower()


def test_scribe_context_includes_log_format():
    from showrunner.agents.scribe import render_scribe_context
    output = render_scribe_context(SCENE_STATE, PARTY_STATS)
    assert "YYYY-MM-DD" in output


def test_scribe_has_no_tools():
    import os
    os.environ.setdefault("GEMINI_API_KEY", "test-key")
    from showrunner.agents.scribe import create_scribe
    scribe = create_scribe()
    assert not scribe.tools
