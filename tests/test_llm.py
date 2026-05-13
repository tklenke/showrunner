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
        call_llm("narrator", "You are the narrator.", "Describe the scene.")
    call_args = mock_completion.call_args
    messages = call_args.kwargs.get("messages") or call_args.args[1]
    roles = [m["role"] for m in messages]
    assert roles == ["system", "user"]
    assert messages[0]["content"] == "You are the narrator."
    assert messages[1]["content"] == "Describe the scene."


def test_call_llm_returns_response_content():
    from showrunner.llm import call_llm
    with patch("litellm.completion", return_value=_mock_response("The scene unfolds.")):
        result = call_llm("narrator", "sys", "user")
    assert result == "The scene unfolds."


def test_call_llm_passes_model_from_config():
    from showrunner.llm import call_llm
    with patch("litellm.completion", return_value=_mock_response("ok")) as mock_completion:
        call_llm("narrator", "sys", "user")
    kwargs = mock_completion.call_args.kwargs
    assert "model" in kwargs
    assert "llama" in kwargs["model"].lower()


def test_call_llm_passes_api_base_for_local_models():
    from showrunner.llm import call_llm
    with patch("litellm.completion", return_value=_mock_response("ok")) as mock_completion:
        call_llm("narrator", "sys", "user")
    kwargs = mock_completion.call_args.kwargs
    assert "api_base" in kwargs
    assert "192.168" in kwargs["api_base"]


def test_call_llm_gemini_disables_thinking():
    from showrunner.llm import call_llm
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
    from unittest.mock import patch as p
    with p("showrunner.llm.load_agent_configs", return_value=fake_configs):
        with patch("litellm.completion", return_value=_mock_response("ok")) as mock_completion:
            call_llm("gemini_agent", "sys", "user")
    kwargs = mock_completion.call_args.kwargs
    assert kwargs.get("thinking") == {"type": "disabled"}


def test_call_llm_non_gemini_does_not_include_thinking():
    from showrunner.llm import call_llm
    with patch("litellm.completion", return_value=_mock_response("ok")) as mock_completion:
        call_llm("narrator", "sys", "user")
    kwargs = mock_completion.call_args.kwargs
    assert "thinking" not in kwargs


def test_setup_llm_logging_and_call_llm_writes_log(tmp_path):
    from showrunner.llm import setup_llm_logging, call_llm
    log_file = tmp_path / "prompts.log"
    setup_llm_logging(log_file)
    with patch("litellm.completion", return_value=_mock_response("The hall is silent.")):
        call_llm("narrator", "You are the narrator.", "Describe the entrance hall.")
    content = log_file.read_text()
    assert "narrator" in content
    assert "p →" in content


def test_call_llm_log_line_contains_caller_function_name(tmp_path):
    from showrunner.llm import setup_llm_logging, call_llm
    log_file = tmp_path / "prompts.log"
    setup_llm_logging(log_file)

    def my_known_runner():
        return call_llm("narrator", "sys", "user")

    with patch("litellm.completion", return_value=_mock_response("result")):
        my_known_runner()
    line = log_file.read_text()
    assert "narrator" in line
    assert "my_known_runner" in line


def test_call_llm_label_appears_in_log(tmp_path):
    from showrunner.llm import setup_llm_logging, call_llm
    log_file = tmp_path / "prompts.log"
    setup_llm_logging(log_file)
    with patch("litellm.completion", return_value=_mock_response("ok")):
        call_llm("narrator", "sys", "user", label="bargos_the_hutt")
    assert "bargos_the_hutt" in log_file.read_text()


def test_build_system_prompt_contains_role():
    from showrunner.llm import build_system_prompt
    prompt = build_system_prompt("narrator")
    assert "Narrator" in prompt


def test_build_system_prompt_contains_goal():
    from showrunner.llm import build_system_prompt
    prompt = build_system_prompt("narrator")
    assert len(prompt) > 50


def test_load_task_prompt_returns_non_empty_string():
    from showrunner.llm import load_task_prompt
    result = load_task_prompt("run_checks")
    assert isinstance(result, str)
    assert len(result) > 0


def test_load_task_prompt_all_task_files_exist():
    from showrunner.llm import load_task_prompt
    tasks = [
        "run_checks", "run_rulings", "run_narrative", "run_summaries",
        "run_last_actions", "run_plan_update", "run_beat_opener",
    ]
    for task in tasks:
        result = load_task_prompt(task)
        assert len(result) > 0, f"task_{task}.md is empty"


def test_build_system_prompt_uses_prompt_file_when_present(tmp_path, monkeypatch):
    from showrunner.llm import build_system_prompt
    fake_configs = {
        "narrator": {
            "role": "Narrator",
            "goal": "Tell stories.",
            "backstory": "A storyteller.",
            "prompt_file": None,
            "litellm_params": {"model": "test/model"},
            "model_alias": "test",
        }
    }
    with patch("showrunner.llm.load_agent_configs", return_value=fake_configs):
        prompt = build_system_prompt("narrator")
    assert "Narrator" in prompt or "Tell stories" in prompt


def test_build_system_prompt_includes_world_context():
    from showrunner.llm import build_system_prompt
    prompt = build_system_prompt("narrator")
    assert "Star Wars" in prompt or "Edge of the Empire" in prompt


def test_build_system_prompt_uses_context_tier():
    from showrunner.llm import build_system_prompt
    fake_world = {
        "world": {
            "name": "TestWorld",
            "description": {
                "large": "LARGE world description here.",
                "medium": "MEDIUM world description here.",
                "small": "SMALL world description here.",
            }
        }
    }
    fake_configs_large = {
        "narrator": {
            "role": "Narrator",
            "goal": "Tell stories.",
            "backstory": "A storyteller.",
            "prompt_file": None,
            "context_tier": "large",
            "litellm_params": {"model": "test/model"},
            "model_alias": "test",
        }
    }
    with patch("showrunner.llm.load_agent_configs", return_value=fake_configs_large), \
         patch("showrunner.llm._load_world_yaml", return_value=fake_world):
        prompt = build_system_prompt("narrator")
    assert "LARGE world description" in prompt
    assert "MEDIUM world description" not in prompt


def test_build_system_prompt_missing_tier_falls_back_to_medium():
    from showrunner.llm import build_system_prompt
    fake_world = {
        "world": {
            "name": "TestWorld",
            "description": {
                "large": "LARGE world description here.",
                "medium": "MEDIUM world description here.",
                "small": "SMALL world description here.",
            }
        }
    }
    fake_configs = {
        "narrator": {
            "role": "Narrator",
            "goal": "Tell stories.",
            "backstory": "A storyteller.",
            "prompt_file": None,
            "context_tier": None,
            "litellm_params": {"model": "test/model"},
            "model_alias": "test",
        }
    }
    with patch("showrunner.llm.load_agent_configs", return_value=fake_configs), \
         patch("showrunner.llm._load_world_yaml", return_value=fake_world):
        prompt = build_system_prompt("narrator")
    assert "MEDIUM world description" in prompt
