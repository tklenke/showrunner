# ABOUTME: Tests for session instrumentation — prompt/response logging and LLM logging setup.
# ABOUTME: Covers prompt/response formatting, file writing, and setup_instrumentation wiring.

import sys
import pytest


@pytest.fixture
def config_path(tmp_path):
    p = tmp_path / "litellm.yaml"
    p.write_text("""
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
""")
    return p


def test_server_for_prefix_extracted():
    from showrunner.instrumentation import _PromptLogger
    logger = _PromptLogger(None)
    assert logger._server_for("sardinia/llama-3.1-8b") == "sardinia"
    assert logger._server_for("gemini/gemini-2.5-flash") == "gemini"
    assert logger._server_for("alien/llama-3.2-3b") == "alien"


def test_server_for_no_slash_returns_model():
    from showrunner.instrumentation import _PromptLogger
    logger = _PromptLogger(None)
    assert logger._server_for("unknown") == "unknown"


def test_server_for_uses_map_over_prefix():
    from showrunner.instrumentation import _PromptLogger
    server_map = {"openai/meta-llama-3.1-8b-instruct": "sardinia"}
    logger = _PromptLogger(None, server_map=server_map)
    assert logger._server_for("openai/meta-llama-3.1-8b-instruct") == "sardinia"


def test_server_for_falls_back_to_prefix_when_not_in_map():
    from showrunner.instrumentation import _PromptLogger
    server_map = {"openai/meta-llama-3.1-8b-instruct": "sardinia"}
    logger = _PromptLogger(None, server_map=server_map)
    assert logger._server_for("gemini-2.5-flash") == "gemini-2.5-flash"
    assert logger._server_for("other/model") == "other"


def test_format_messages_single():
    from showrunner.instrumentation import _PromptLogger
    logger = _PromptLogger(None)
    messages = [{"role": "system", "content": "You are the Show Runner."}]
    output = logger._format_messages(messages)
    assert "[system]" in output
    assert "You are the Show Runner." in output


def test_format_messages_multiple_roles():
    from showrunner.instrumentation import _PromptLogger
    logger = _PromptLogger(None)
    messages = [
        {"role": "system", "content": "You are the Show Runner."},
        {"role": "user", "content": "Run a single scene beat."},
    ]
    output = logger._format_messages(messages)
    assert "[system]" in output
    assert "[user]" in output
    assert "You are the Show Runner." in output
    assert "Run a single scene beat." in output


def test_format_messages_string_passthrough():
    from showrunner.instrumentation import _PromptLogger
    logger = _PromptLogger(None)
    assert logger._format_messages("already a string") == "already a string"


def test_write_creates_file(tmp_path):
    from showrunner.instrumentation import _PromptLogger
    log_file = tmp_path / "prompts.log"
    logger = _PromptLogger(log_file)
    logger._write("gemini", "prompt", "hello world")
    assert log_file.exists()


def test_write_format_contains_header_fields(tmp_path):
    from showrunner.instrumentation import _PromptLogger
    log_file = tmp_path / "prompts.log"
    logger = _PromptLogger(log_file)
    logger._write("gemini", "prompt", "hello world")
    content = log_file.read_text()
    assert "gemini" in content
    assert "prompt" in content
    assert "hello world" in content


def test_write_appends_on_multiple_calls(tmp_path):
    from showrunner.instrumentation import _PromptLogger
    log_file = tmp_path / "prompts.log"
    logger = _PromptLogger(log_file)
    logger._write("gemini", "prompt", "first entry")
    logger._write("alien", "response", "second entry")
    content = log_file.read_text()
    assert "first entry" in content
    assert "second entry" in content


def test_setup_instrumentation_returns_two_paths(tmp_path):
    from showrunner.instrumentation import setup_instrumentation
    import showrunner.llm
    result = setup_instrumentation("ts_test", logs_dir=tmp_path)
    assert len(result) == 2
    verbose_path, prompts_path = result
    assert "verbose" in verbose_path.name
    assert "prompts" in prompts_path.name


def test_setup_instrumentation_calls_setup_llm_logging(tmp_path, monkeypatch):
    import showrunner.llm
    called_with = []
    monkeypatch.setattr(showrunner.llm, "setup_llm_logging", lambda path: called_with.append(path))
    from showrunner.instrumentation import setup_instrumentation
    verbose_path, prompts_path = setup_instrumentation("ts_wire", logs_dir=tmp_path)
    assert len(called_with) == 1
    assert called_with[0] == prompts_path
