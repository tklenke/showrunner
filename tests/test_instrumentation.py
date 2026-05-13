# ABOUTME: Tests for session instrumentation — CrewAI event bus prompt logging and stdout capture.
# ABOUTME: Covers prompt/response formatting, file writing, verbose redirect, and event bus integration.

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


def test_verbose_redirect_swaps_rich_console(tmp_path):
    from crewai.events.event_listener import event_listener
    from showrunner.instrumentation import verbose_to_file
    log_file = tmp_path / "verbose.log"
    original_console = event_listener.formatter.console
    with verbose_to_file(log_file):
        assert event_listener.formatter.console is not original_console
    assert event_listener.formatter.console is original_console


def test_verbose_redirect_restores_rich_console_on_exception(tmp_path):
    from crewai.events.event_listener import event_listener
    from showrunner.instrumentation import verbose_to_file
    log_file = tmp_path / "verbose.log"
    original_console = event_listener.formatter.console
    try:
        with verbose_to_file(log_file):
            raise ValueError("test error")
    except ValueError:
        pass
    assert event_listener.formatter.console is original_console


def test_setup_instrumentation_maps_server_names_from_config(tmp_path, config_path):
    """When config_path given, litellm model IDs are resolved to server names."""
    from crewai.events.event_bus import crewai_event_bus
    from crewai.events.types.llm_events import LLMCallCompletedEvent, LLMCallStartedEvent, LLMCallType
    from showrunner.instrumentation import setup_instrumentation

    _, prompts_path, logger = setup_instrumentation("test_ts2", logs_dir=tmp_path, config_path=config_path)

    try:
        crewai_event_bus.emit(None, event=LLMCallStartedEvent(
            model="openai/meta-llama-3.1-8b-instruct",
            call_id="map-test-1",
        ))
        future = crewai_event_bus.emit(None, event=LLMCallCompletedEvent(
            model="openai/meta-llama-3.1-8b-instruct",
            call_id="map-test-1",
            messages=[],
            response="sardinia response",
            call_type=LLMCallType.LLM_CALL,
        ))
        if future is not None:
            future.result(timeout=5.0)

        content = prompts_path.read_text()
        assert "sardinia" in content
        assert "openai" not in content
    finally:
        crewai_event_bus.off(LLMCallCompletedEvent, logger._on_completed)


def test_prompts_written_via_crewai_event_bus(tmp_path, config_path):
    """Prompts file is written when CrewAI emits LLMCallCompletedEvent on its event bus."""
    from crewai.events.event_bus import crewai_event_bus
    from crewai.events.types.llm_events import LLMCallCompletedEvent, LLMCallStartedEvent, LLMCallType
    from showrunner.instrumentation import setup_instrumentation

    _, prompts_path, logger = setup_instrumentation("test_ts", logs_dir=tmp_path)

    try:
        crewai_event_bus.emit(
            None,
            event=LLMCallStartedEvent(
                model="sardinia/llama-3.1-8b",
                call_id="test-call-1",
                messages=[{"role": "user", "content": "hello"}],
            ),
        )
        future = crewai_event_bus.emit(
            None,
            event=LLMCallCompletedEvent(
                model="sardinia/llama-3.1-8b",
                call_id="test-call-1",
                messages=[{"role": "user", "content": "hello"}],
                response="The scene is atmospheric.",
                call_type=LLMCallType.LLM_CALL,
            ),
        )
        if future is not None:
            future.result(timeout=5.0)

        assert prompts_path.exists(), "prompts file not created"
        content = prompts_path.read_text()
        assert "sardinia" in content
        assert "The scene is atmospheric." in content
    finally:
        crewai_event_bus.off(LLMCallCompletedEvent, logger._on_completed)
