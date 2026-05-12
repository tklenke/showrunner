# ABOUTME: Tests for World Runner agent — scene read-aloud and beat narration context.
# ABOUTME: Verifies render_world_runner_context returns read_aloud and beat-specific notes.

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
            "world_runner_notes": "Describe the scale of the chamber.",
            "checks": [],
        },
        {
            "id": "audience",
            "title": "The Job",
            "world_runner_notes": "Bargos speaks slowly.",
            "checks": [],
        },
    ],
}


def test_read_aloud_text_passed_to_world_runner():
    from showrunner.agents.world_runner import render_world_runner_context
    output = render_world_runner_context(SCENE, "summons")
    assert "ushered into the audience chamber" in output


def test_world_runner_notes_passed_per_beat():
    from showrunner.agents.world_runner import render_world_runner_context
    output = render_world_runner_context(SCENE, "audience")
    assert "Bargos speaks slowly" in output
