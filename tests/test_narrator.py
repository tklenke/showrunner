# ABOUTME: Tests for Narrator agent — scene read-aloud and beat narration context.
# ABOUTME: Verifies render_narrator_context returns read_aloud and beat-specific notes.

SCENE = {
    "location": {
        "name": "Bargos's Estate",
        "atmosphere": "Nervous money.",
        "read_aloud": "You are ushered into the audience chamber.",
    },
    "beats": [
        {
            "id": "summons",
            "title": "The Summons",
            "narrator_notes": "Describe the scale of the chamber.",
            "checks": [],
        },
        {
            "id": "audience",
            "title": "The Job",
            "narrator_notes": "Bargos speaks slowly.",
            "checks": [],
        },
    ],
}


def test_read_aloud_text_passed_to_narrator():
    from showrunner.agents.narrator import render_narrator_context
    output = render_narrator_context(SCENE, "summons")
    assert "ushered into the audience chamber" in output


def test_narrator_notes_passed_per_beat():
    from showrunner.agents.narrator import render_narrator_context
    output = render_narrator_context(SCENE, "audience")
    assert "Bargos speaks slowly" in output


def test_narrator_backstory_includes_injected_context(monkeypatch):
    import os
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    from showrunner.agents.narrator import create_narrator
    context = "### Current Beat: The Summons\nDescribe the scale of the chamber."
    agent = create_narrator(context=context)
    assert "Current Beat" in agent.backstory
    assert "scale of the chamber" in agent.backstory


def test_narrator_backstory_unchanged_without_context(monkeypatch):
    import os
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    from showrunner.agents.narrator import create_narrator
    agent_no_ctx = create_narrator()
    agent_with_ctx = create_narrator(context="extra info")
    assert agent_no_ctx.backstory in agent_with_ctx.backstory
