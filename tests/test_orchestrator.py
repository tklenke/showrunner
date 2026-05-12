# ABOUTME: Tests for orchestrator — player turn detection and CLI prompt for human characters.
# ABOUTME: Verifies human vs AI character routing and CLI input handling.


SCENE = {
    "beats": [
        {"id": "summons"},
        {"id": "audience"},
        {"id": "mission_brief"},
    ]
}


def test_beat_prompt_enter_stays_on_current_beat(monkeypatch):
    from showrunner.orchestrator import _beat_prompt
    monkeypatch.setattr("builtins.input", lambda _: "")
    result = _beat_prompt(SCENE, "summons")
    assert result == "stay"


def test_beat_prompt_a_advances(monkeypatch):
    from showrunner.orchestrator import _beat_prompt
    monkeypatch.setattr("builtins.input", lambda _: "a")
    result = _beat_prompt(SCENE, "summons")
    assert result == "advance"


def test_beat_prompt_beat_id_returns_id(monkeypatch):
    from showrunner.orchestrator import _beat_prompt
    monkeypatch.setattr("builtins.input", lambda _: "mission_brief")
    result = _beat_prompt(SCENE, "summons")
    assert result == "mission_brief"


def test_beat_prompt_quit_returns_quit(monkeypatch):
    from showrunner.orchestrator import _beat_prompt
    monkeypatch.setattr("builtins.input", lambda _: "q")
    result = _beat_prompt(SCENE, "summons")
    assert result == "q"


def test_human_player_turn_prompts_cli(monkeypatch):
    from showrunner.orchestrator import prompt_player_action
    monkeypatch.setattr("builtins.input", lambda _: "Zee scans the exits.")
    result = prompt_player_action("Z-4P0")
    assert result == "Zee scans the exits."


def test_ai_character_detected_correctly():
    from showrunner.orchestrator import is_human_character
    assert not is_human_character({"identity": {"player": "ai"}})


def test_human_character_detected_correctly():
    from showrunner.orchestrator import is_human_character
    assert is_human_character({"identity": {"player": "human"}})
