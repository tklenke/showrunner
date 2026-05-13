# ABOUTME: Tests for session instrumentation — prompt/response logging and LLM logging setup.
# ABOUTME: Covers summary log line format, file writing, and setup_instrumentation wiring.

import pytest


def test_log_creates_file(tmp_path):
    from showrunner.instrumentation import _PromptLogger
    log_file = tmp_path / "prompts.log"
    logger = _PromptLogger(log_file)
    logger.log("narrator", "sardinia", "narration", 100, 50)
    assert log_file.exists()


def test_log_writes_one_line_per_call(tmp_path):
    from showrunner.instrumentation import _PromptLogger
    log_file = tmp_path / "prompts.log"
    logger = _PromptLogger(log_file)
    logger.log("narrator", "sardinia", "narration", 100, 50)
    lines = [l for l in log_file.read_text().splitlines() if l.strip()]
    assert len(lines) == 1


def test_log_line_contains_agent_server_task_and_sizes(tmp_path):
    from showrunner.instrumentation import _PromptLogger
    log_file = tmp_path / "prompts.log"
    logger = _PromptLogger(log_file)
    logger.log("show_runner", "sardinia", "beat_plan", 1247, 342)
    line = log_file.read_text()
    assert "show_runner" in line
    assert "sardinia" in line
    assert "beat_plan" in line
    assert "1247p" in line
    assert "342r" in line


def test_log_appends_on_multiple_calls(tmp_path):
    from showrunner.instrumentation import _PromptLogger
    log_file = tmp_path / "prompts.log"
    logger = _PromptLogger(log_file)
    logger.log("narrator", "sardinia", "narration", 100, 50)
    logger.log("scribe", "alien", "session_log", 200, 30)
    lines = [l for l in log_file.read_text().splitlines() if l.strip()]
    assert len(lines) == 2
    assert "narrator" in lines[0]
    assert "scribe" in lines[1]


def test_setup_instrumentation_returns_prompts_path(tmp_path):
    from showrunner.instrumentation import setup_instrumentation
    import showrunner.llm
    result = setup_instrumentation("ts_test", logs_dir=tmp_path)
    assert isinstance(result, type(tmp_path))
    assert "prompts" in result.name


def test_setup_instrumentation_calls_setup_llm_logging(tmp_path, monkeypatch):
    import showrunner.llm
    called_with = []
    monkeypatch.setattr(showrunner.llm, "setup_llm_logging", lambda path: called_with.append(path))
    from showrunner.instrumentation import setup_instrumentation
    prompts_path = setup_instrumentation("ts_wire", logs_dir=tmp_path)
    assert len(called_with) == 1
    assert called_with[0] == prompts_path
