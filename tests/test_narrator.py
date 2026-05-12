# ABOUTME: Tests for render_narrator_context — verifies cache-aware ordering of the Narrator's context.
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
            "narrator_notes": "C3-P9 escorts the party in.",
            "world_runner_notes": "Describe the chamber.",
            "checks": [],
        },
        {
            "id": "audience",
            "title": "The Job",
            "trigger": "After PCs are acknowledged.",
            "narrator_notes": "Bargos explains the mine.",
            "world_runner_notes": "Bargos speaks slowly.",
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
    from showrunner.agents.narrator import render_narrator_context
    output = render_narrator_context(SCENE, SCENE_STATE, PARTY_STATS, "Zee examines the room.")
    # Location (static) must appear before party wounds (dynamic)
    location_pos = output.index("Bargos's Estate")
    wounds_pos = output.index("wounds")
    assert location_pos < wounds_pos


def test_current_beat_included():
    from showrunner.agents.narrator import render_narrator_context
    output = render_narrator_context(SCENE, SCENE_STATE, PARTY_STATS, "Zee examines the room.")
    assert "audience" in output


def test_last_action_at_end():
    from showrunner.agents.narrator import render_narrator_context
    last_action = "Zee carefully inspects the exits."
    output = render_narrator_context(SCENE, SCENE_STATE, PARTY_STATS, last_action)
    assert output.endswith(last_action) or output.rindex(last_action) > len(output) // 2


def test_ticking_clock_included_when_present():
    from showrunner.agents.narrator import render_narrator_context
    output = render_narrator_context(SCENE, SCENE_STATE_WITH_CLOCK, PARTY_STATS, "")
    assert "storm_barriers" in output or "Storm Barrier" in output


def test_ticking_clock_absent_when_empty():
    from showrunner.agents.narrator import render_narrator_context
    output = render_narrator_context(SCENE, SCENE_STATE, PARTY_STATS, "")
    assert "ticking" not in output.lower() or "[]" not in output
