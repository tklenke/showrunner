# ABOUTME: Tests for session instrumentation — LiteLLM prompt logging and stdout capture.
# ABOUTME: Covers server map building, prompt/response formatting, and verbose log redirect.

import sys
import pytest


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
