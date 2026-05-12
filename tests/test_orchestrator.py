# ABOUTME: Tests for orchestrator — player turn detection and CLI prompt for human characters.
# ABOUTME: Verifies human vs AI character routing and CLI input handling.


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
