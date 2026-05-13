# ABOUTME: Tests for session instrumentation — LiteLLM prompt logging and stdout capture.
# ABOUTME: Covers server map building, prompt/response formatting, and verbose log redirect.

import sys
import pytest
import litellm
from unittest.mock import MagicMock, patch


FIXTURE_CONFIG = """
model_list:
  - model_name: alien/llama-3.2-3b
    litellm_params:
      model: openai/Llama-3.2-3B-Instruct-Q6_K.gguf
      api_base: http://192.168.1.144:8080/v1
      api_key: not-required
  - model_name: sardinia/llama-3.1-8b
    litellm_params:
      model: openai/meta-llama-3.1-8b-instruct
      api_base: http://192.168.1.45:1234/v1
      api_key: not-required
  - model_name: gemini/gemini-2.5-flash
    litellm_params:
      model: gemini/gemini-2.5-flash
      api_key: os.environ/GEMINI_API_KEY
"""


@pytest.fixture
def config_path(tmp_path):
    p = tmp_path / "litellm.yaml"
    p.write_text(FIXTURE_CONFIG)
    return p


def test_server_map_alien(config_path):
    from showrunner.instrumentation import _build_server_map
    m = _build_server_map(config_path)
    assert m["openai/Llama-3.2-3B-Instruct-Q6_K.gguf"] == "alien"


def test_server_map_sardinia(config_path):
    from showrunner.instrumentation import _build_server_map
    m = _build_server_map(config_path)
    assert m["openai/meta-llama-3.1-8b-instruct"] == "sardinia"


def test_server_map_gemini(config_path):
    from showrunner.instrumentation import _build_server_map
    m = _build_server_map(config_path)
    assert m["gemini/gemini-2.5-flash"] == "gemini"


def test_server_for_known_model():
    from showrunner.instrumentation import _PromptLogger
    logger = _PromptLogger({"gemini/gemini-2.5-flash": "gemini"}, None)
    assert logger._server_for("gemini/gemini-2.5-flash") == "gemini"


def test_server_for_unknown_model_returns_model():
    from showrunner.instrumentation import _PromptLogger
    logger = _PromptLogger({}, None)
    assert logger._server_for("some/unknown-model") == "some/unknown-model"


def test_format_messages_single():
    from showrunner.instrumentation import _PromptLogger
    logger = _PromptLogger({}, None)
    messages = [{"role": "system", "content": "You are the Show Runner."}]
    output = logger._format_messages(messages)
    assert "[system]" in output
    assert "You are the Show Runner." in output


def test_format_messages_multiple_roles():
    from showrunner.instrumentation import _PromptLogger
    logger = _PromptLogger({}, None)
    messages = [
        {"role": "system", "content": "You are the Show Runner."},
        {"role": "user", "content": "Run a single scene beat."},
    ]
    output = logger._format_messages(messages)
    assert "[system]" in output
    assert "[user]" in output
    assert "You are the Show Runner." in output
    assert "Run a single scene beat." in output


def test_write_creates_file(tmp_path):
    from showrunner.instrumentation import _PromptLogger
    log_file = tmp_path / "prompts.log"
    logger = _PromptLogger({}, log_file)
    logger._write("gemini", "prompt", "hello world")
    assert log_file.exists()


def test_write_format_contains_header_fields(tmp_path):
    from showrunner.instrumentation import _PromptLogger
    log_file = tmp_path / "prompts.log"
    logger = _PromptLogger({}, log_file)
    logger._write("gemini", "prompt", "hello world")
    content = log_file.read_text()
    assert "gemini" in content
    assert "prompt" in content
    assert "hello world" in content


def test_write_appends_on_multiple_calls(tmp_path):
    from showrunner.instrumentation import _PromptLogger
    log_file = tmp_path / "prompts.log"
    logger = _PromptLogger({}, log_file)
    logger._write("gemini", "prompt", "first entry")
    logger._write("alien", "response", "second entry")
    content = log_file.read_text()
    assert "first entry" in content
    assert "second entry" in content


def test_verbose_redirect_captures_stdout(tmp_path):
    from showrunner.instrumentation import verbose_to_file
    log_file = tmp_path / "verbose.log"
    with verbose_to_file(log_file):
        print("test output")
    assert "test output" in log_file.read_text()


def test_verbose_redirect_restores_stdout(tmp_path):
    from showrunner.instrumentation import verbose_to_file
    log_file = tmp_path / "verbose.log"
    real_stdout = sys.stdout
    with verbose_to_file(log_file):
        pass
    assert sys.stdout is real_stdout


def test_verbose_redirect_restores_stdout_on_exception(tmp_path):
    from showrunner.instrumentation import verbose_to_file
    log_file = tmp_path / "verbose.log"
    real_stdout = sys.stdout
    try:
        with verbose_to_file(log_file):
            raise ValueError("test error")
    except ValueError:
        pass
    assert sys.stdout is real_stdout


def _make_mock_litellm_response():
    msg = MagicMock()
    msg.content = "hello"
    msg.role = "assistant"
    msg.function_call = None
    msg.tool_calls = None
    choice = MagicMock()
    choice.message = msg
    choice.finish_reason = "stop"
    choice.index = 0
    resp = MagicMock()
    resp.choices = [choice]
    resp.usage = MagicMock(prompt_tokens=5, completion_tokens=5, total_tokens=10)
    resp.id = "test-id"
    resp.created = 1234567890
    resp.object = "chat.completion"
    resp.model = "openai/test"
    return resp


def test_prompt_logger_fires_after_crewai_callback_reset(tmp_path, config_path):
    """Prompts file is written even after CrewAI resets litellm.callbacks during agent creation."""
    from showrunner.instrumentation import setup_instrumentation

    original_callbacks = list(litellm.callbacks)
    try:
        verbose_path, prompts_path, logger = setup_instrumentation("test_ts", logs_dir=tmp_path)

        # Simulate CrewAI resetting callbacks during LLM._init_litellm()
        litellm.callbacks = []

        # Orchestrator re-registers after build_crew()
        litellm.callbacks = [logger]

        with patch(
            "litellm.main.openai_chat_completions.completion",
            return_value=_make_mock_litellm_response(),
        ):
            litellm.completion(
                model="openai/test",
                messages=[{"role": "user", "content": "hi"}],
                api_key="x",
                api_base="http://localhost:9",
            )

        assert prompts_path.exists(), "prompts file not created"
        content = prompts_path.read_text()
        assert "response" in content
        assert "hello" in content
    finally:
        litellm.callbacks = original_callbacks
