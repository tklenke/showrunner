# ABOUTME: Tests for render_show_runner_context — verifies cache-aware ordering of the Show Runner's context.
# ABOUTME: Static scene content must precede dynamic runtime state in the assembled string.

SCENE = {
    "scene_id": "bargos_audience",
    "title": "Audience with Bargos the Hutt",
    "location": {
        "name": "Bargos's Estate, Sleheyron",
        "atmosphere": "Opulent but slightly nervous money.",
        "read_aloud": "You are ushered into the audience chamber.",
    },
    "npcs_present": ["bargos_the_hutt", "kaelen_sunara"],
    "inline_npcs": [
        {
            "id": "c3p9",
            "name": "C3-P9",
            "role": "Protocol droid",
            "key_traits": "Deferential and precise.",
        }
    ],
    "minion_groups": [
        {
            "id": "gamorrean_guards",
            "name": "Renegade Gamorrean Guards",
            "count": 6,
            "soak": 4,
            "wound_threshold": 5,
            "weapons": [
                {"name": "Vibro-Axe", "skill": "Melee", "damage": 5,
                 "critical": 3, "range": "Engaged", "special": "Vicious 2"},
            ],
        }
    ],
    "beats": [
        {
            "id": "summons",
            "title": "The Summons",
            "trigger": "Scene entry.",
            "show_runner_notes": "C3-P9 escorts the party in.",
            "narrator_notes": "Describe the chamber.",
            "checks": [],
        },
        {
            "id": "audience",
            "title": "The Job",
            "trigger": "After PCs are acknowledged.",
            "show_runner_notes": "Bargos explains the mine.",
            "narrator_notes": "Bargos speaks slowly.",
            "checks": [],
        },
    ],
    "exit": {"condition": "PCs have coordinates.", "next_scene": None},
}

SCENE_STATE = {
    "current_scene": 0,
    "current_beat": "audience",
    "ticking_clocks": [],
    "character_plans": {"bargos_the_hutt": "Secure a deal and project strength."},
}

SCENE_STATE_WITH_CLOCK = {
    "current_scene": 0,
    "current_beat": "audience",
    "ticking_clocks": [
        {"id": "storm_barriers", "label": "Storm Barrier Generators", "max": 8, "destroyed": 1}
    ],
    "character_plans": {},
}

PARTY_STATS = {
    "characters": {
        "z_4p0": {"wounds": 3, "strain": 1, "credits": 50},
        "kaelen": {"wounds": 0, "strain": 0, "credits": 500},
    }
}


def test_static_content_precedes_dynamic():
    from showrunner.agents.show_runner import render_show_runner_context
    output = render_show_runner_context(SCENE, SCENE_STATE, PARTY_STATS, {"Z-4P0": "examines the room."})
    location_pos = output.index("Bargos's Estate")
    wounds_pos = output.index("wounds")
    assert location_pos < wounds_pos


def test_current_beat_included():
    from showrunner.agents.show_runner import render_show_runner_context
    output = render_show_runner_context(SCENE, SCENE_STATE, PARTY_STATS, {"Z-4P0": "examines the room."})
    assert "audience" in output


def test_last_actions_included():
    from showrunner.agents.show_runner import render_show_runner_context
    last_actions = {"Z-4P0": "carefully inspects the exits.", "Bargos": "watches silently."}
    output = render_show_runner_context(SCENE, SCENE_STATE, PARTY_STATS, last_actions)
    assert "Z-4P0" in output
    assert "carefully inspects the exits." in output
    assert "Bargos" in output


def test_ticking_clock_included_when_present():
    from showrunner.agents.show_runner import render_show_runner_context
    output = render_show_runner_context(SCENE, SCENE_STATE_WITH_CLOCK, PARTY_STATS, "")
    assert "storm_barriers" in output or "Storm Barrier" in output


def test_ticking_clock_absent_when_empty():
    from showrunner.agents.show_runner import render_show_runner_context
    output = render_show_runner_context(SCENE, SCENE_STATE, PARTY_STATS, "")
    assert "ticking" not in output.lower() or "[]" not in output
