# ABOUTME: Session instrumentation — prompt/response logging and log path setup.
# ABOUTME: _PromptLogger writes one summary line per LLM call; used by llm.py.

from datetime import datetime
from pathlib import Path


class _PromptLogger:
    def __init__(self, log_path: Path):
        self._log_path = log_path
        self._call_id = 0

    def log(self, agent: str, server: str, step: str, prompt_len: int, response_len: int, label: str = "") -> None:
        self._call_id += 1
        step_col = f"{step}[{label}]" if label else step
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"{self._call_id:04d}  {timestamp}  {agent}  {server}  {step_col}  {prompt_len}p → {response_len}r\n"
        with self._log_path.open("a") as f:
            f.write(line)


def setup_instrumentation(
    timestamp: str, logs_dir: Path | None = None
) -> Path:
    """Create log path, wire LLM prompt logging, return prompts_path."""
    if logs_dir is None:
        logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    prompts_path = logs_dir / f"prompts_{timestamp}.log"

    import showrunner.llm
    showrunner.llm.setup_llm_logging(prompts_path)
    return prompts_path
