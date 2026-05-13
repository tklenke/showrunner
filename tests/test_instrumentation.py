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
    monkeypatch.setattr(showrunner.llm, "setup_llm_logging", lambda path, **kw: called_with.append(path))
    from showrunner.instrumentation import setup_instrumentation
    prompts_path = setup_instrumentation("ts_wire", logs_dir=tmp_path)
    assert len(called_with) == 1
    assert called_with[0] == prompts_path


def test_log_line_starts_with_4digit_id(tmp_path):
    from showrunner.instrumentation import _PromptLogger
    log_file = tmp_path / "prompts.log"
    logger = _PromptLogger(log_file)
    logger.log("narrator", "sardinia", "narration", 100, 50)
    line = log_file.read_text().strip()
    first_col = line.split()[0]
    assert first_col.isdigit() and len(first_col) == 4


def test_log_id_increments_per_call(tmp_path):
    from showrunner.instrumentation import _PromptLogger
    log_file = tmp_path / "prompts.log"
    logger = _PromptLogger(log_file)
    logger.log("narrator", "sardinia", "step", 10, 5)
    logger.log("narrator", "sardinia", "step", 10, 5)
    lines = [l for l in log_file.read_text().splitlines() if l.strip()]
    id1 = int(lines[0].split()[0])
    id2 = int(lines[1].split()[0])
    assert id2 == id1 + 1


def test_log_step_includes_label_in_brackets(tmp_path):
    from showrunner.instrumentation import _PromptLogger
    log_file = tmp_path / "prompts.log"
    logger = _PromptLogger(log_file)
    logger.log("actors", "sardinia", "run_npc_wave", 100, 50, label="bargos_the_hutt")
    line = log_file.read_text()
    assert "run_npc_wave[bargos_the_hutt]" in line


def test_log_step_no_brackets_when_no_label(tmp_path):
    from showrunner.instrumentation import _PromptLogger
    log_file = tmp_path / "prompts.log"
    logger = _PromptLogger(log_file)
    logger.log("narrator", "sardinia", "run_beat_opener", 100, 50)
    line = log_file.read_text()
    assert "run_beat_opener[" not in line
    assert "run_beat_opener" in line


def test_dump_dir_none_writes_no_md_files(tmp_path):
    from showrunner.instrumentation import _PromptLogger
    log_file = tmp_path / "prompts.log"
    logger = _PromptLogger(log_file)
    logger.log("narrator", "sardinia", "run_beat_opener", 100, 50,
               system_prompt="sys", user_message="user", response="resp")
    md_files = list(tmp_path.glob("*.md"))
    assert md_files == []


def test_dump_dir_set_writes_md_file(tmp_path):
    from showrunner.instrumentation import _PromptLogger
    log_file = tmp_path / "prompts.log"
    dump_dir = tmp_path / "prompts"
    dump_dir.mkdir()
    logger = _PromptLogger(log_file, dump_dir=dump_dir)
    logger.log("narrator", "sardinia", "run_beat_opener", 100, 50,
               system_prompt="SYS CONTENT", user_message="USER CONTENT", response="RESP CONTENT")
    md_files = list(dump_dir.glob("*.md"))
    assert len(md_files) == 1


def test_dump_md_file_named_by_id_agent_step(tmp_path):
    from showrunner.instrumentation import _PromptLogger
    log_file = tmp_path / "prompts.log"
    dump_dir = tmp_path / "prompts"
    dump_dir.mkdir()
    logger = _PromptLogger(log_file, dump_dir=dump_dir)
    logger.log("narrator", "sardinia", "run_beat_opener", 10, 5,
               system_prompt="s", user_message="u", response="r")
    md_files = list(dump_dir.glob("*.md"))
    assert md_files[0].name == "0001_narrator_run_beat_opener.md"


def test_dump_md_file_name_includes_label(tmp_path):
    from showrunner.instrumentation import _PromptLogger
    log_file = tmp_path / "prompts.log"
    dump_dir = tmp_path / "prompts"
    dump_dir.mkdir()
    logger = _PromptLogger(log_file, dump_dir=dump_dir)
    logger.log("actors", "sardinia", "run_npc_wave", 10, 5, label="bargos",
               system_prompt="s", user_message="u", response="r")
    md_files = list(dump_dir.glob("*.md"))
    assert md_files[0].name == "0001_actors_run_npc_wave[bargos].md"


def test_dump_md_file_contains_system_user_response_sections(tmp_path):
    from showrunner.instrumentation import _PromptLogger
    log_file = tmp_path / "prompts.log"
    dump_dir = tmp_path / "prompts"
    dump_dir.mkdir()
    logger = _PromptLogger(log_file, dump_dir=dump_dir)
    logger.log("narrator", "sardinia", "step", 10, 5,
               system_prompt="THE SYSTEM", user_message="THE USER", response="THE RESPONSE")
    content = list(dump_dir.glob("*.md"))[0].read_text()
    assert "# System\nTHE SYSTEM" in content
    assert "# User\nTHE USER" in content
    assert "# Response\nTHE RESPONSE" in content


def test_setup_instrumentation_dump_prompts_creates_subdir(tmp_path, monkeypatch):
    import showrunner.llm
    monkeypatch.setattr(showrunner.llm, "setup_llm_logging", lambda *a, **kw: None)
    from showrunner.instrumentation import setup_instrumentation
    setup_instrumentation("ts", logs_dir=tmp_path, dump_prompts=True)
    assert (tmp_path / "prompts").is_dir()
