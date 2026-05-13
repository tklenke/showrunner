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
