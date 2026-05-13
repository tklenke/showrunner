# ABOUTME: Tests for llm.py — call_llm(), build_system_prompt(), and setup_llm_logging().
# ABOUTME: Uses mocked litellm.completion to verify message assembly and logging.

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture(autouse=True)
def gemini_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")


def _mock_response(content: str):
    response = MagicMock()
    response.choices[0].message.content = content
    return response


def test_call_llm_sends_system_and_user_messages():
    from showrunner.llm import call_llm
    with patch("litellm.completion", return_value=_mock_response("output")) as mock_completion:
        call_llm("narrator", "You are the narrator.", "Describe the scene.", task="narration")
    call_args = mock_completion.call_args
    messages = call_args.kwargs.get("messages") or call_args.args[1]
    roles = [m["role"] for m in messages]
    assert roles == ["system", "user"]
    assert messages[0]["content"] == "You are the narrator."
    assert messages[1]["content"] == "Describe the scene."


def test_call_llm_returns_response_content():
    from showrunner.llm import call_llm
    with patch("litellm.completion", return_value=_mock_response("The scene unfolds.")):
        result = call_llm("narrator", "sys", "user", task="narration")
    assert result == "The scene unfolds."


def test_call_llm_passes_model_from_config():
    from showrunner.llm import call_llm
    with patch("litellm.completion", return_value=_mock_response("ok")) as mock_completion:
        call_llm("narrator", "sys", "user", task="narration")
    kwargs = mock_completion.call_args.kwargs
    assert "model" in kwargs
    assert "llama" in kwargs["model"].lower()


def test_call_llm_passes_api_base_for_local_models():
    from showrunner.llm import call_llm
    with patch("litellm.completion", return_value=_mock_response("ok")) as mock_completion:
        call_llm("narrator", "sys", "user", task="narration")
    kwargs = mock_completion.call_args.kwargs
    assert "api_base" in kwargs
    assert "192.168" in kwargs["api_base"]


def test_call_llm_gemini_disables_thinking():
    from showrunner.llm import call_llm
    with patch("litellm.completion", return_value=_mock_response("ok")) as mock_completion:
        call_llm("show_runner", "sys", "user", task="beat_plan")
    # show_runner uses sardinia (llama), not gemini — test with a gemini model directly
    # We patch load_agent_configs to inject a gemini agent
    from unittest.mock import patch as p
    gemini_params = {
        "model": "gemini/gemini-2.5-flash",
        "api_key": "test-key",
    }
    fake_configs = {
        "gemini_agent": {
            "role": "Test",
            "goal": "Test",
            "backstory": "Test",
            "litellm_params": gemini_params,
            "model_alias": "gemini/gemini-2.5-flash",
        }
    }
    with p("showrunner.llm.load_agent_configs", return_value=fake_configs):
        with patch("litellm.completion", return_value=_mock_response("ok")) as mock_completion:
            call_llm("gemini_agent", "sys", "user", task="beat_plan")
    kwargs = mock_completion.call_args.kwargs
    assert kwargs.get("thinking") == {"type": "disabled"}


def test_call_llm_non_gemini_does_not_include_thinking():
    from showrunner.llm import call_llm
    with patch("litellm.completion", return_value=_mock_response("ok")) as mock_completion:
        call_llm("narrator", "sys", "user", task="narration")
    kwargs = mock_completion.call_args.kwargs
    assert "thinking" not in kwargs


def test_setup_llm_logging_and_call_llm_writes_log(tmp_path):
    from showrunner.llm import setup_llm_logging, call_llm
    log_file = tmp_path / "prompts.log"
    setup_llm_logging(log_file)
    with patch("litellm.completion", return_value=_mock_response("The hall is silent.")):
        call_llm("narrator", "You are the narrator.", "Describe the entrance hall.", task="narration")
    content = log_file.read_text()
    assert "narrator" in content
    assert "narration" in content
    assert "p →" in content


def test_call_llm_log_line_contains_agent_and_task(tmp_path):
    from showrunner.llm import setup_llm_logging, call_llm
    log_file = tmp_path / "prompts.log"
    setup_llm_logging(log_file)
    with patch("litellm.completion", return_value=_mock_response("result")):
        call_llm("scribe", "sys", "user", task="session_log")
    line = log_file.read_text()
    assert "scribe" in line
    assert "session_log" in line


def test_build_system_prompt_contains_role():
    from showrunner.llm import build_system_prompt
    prompt = build_system_prompt("narrator")
    assert "Narrator" in prompt


def test_build_system_prompt_contains_goal():
    from showrunner.llm import build_system_prompt
    prompt = build_system_prompt("narrator")
    assert len(prompt) > 50
