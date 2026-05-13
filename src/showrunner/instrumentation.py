# ABOUTME: Session instrumentation — CrewAI event bus prompt/response logging and verbose stdout capture.
# ABOUTME: Subscribes to LLMCallCompletedEvent on CrewAI's event bus; provides a context manager for stdout redirection.

import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from crewai.events.event_bus import crewai_event_bus
from crewai.events.types.llm_events import LLMCallCompletedEvent


def _build_server_map(config_path: Path) -> dict[str, str]:
    """Build a reverse map from litellm_params.model → the server prefix of model_name."""
    import yaml
    config = yaml.safe_load(config_path.read_text())
    result = {}
    for entry in config.get("model_list", []):
        model_name = entry.get("model_name", "")
        prefix = model_name.split("/")[0]
        litellm_model = entry.get("litellm_params", {}).get("model", "")
        if litellm_model:
            result[litellm_model] = prefix
    return result


class _PromptLogger:
    def __init__(self, log_path: Path, server_map: dict[str, str] | None = None):
        self._log_path = log_path
        self._server_map = server_map or {}

    def _server_for(self, model: str) -> str:
        """Resolve model to a human-readable server label via map, then prefix fallback."""
        if model in self._server_map:
            return self._server_map[model]
        return model.split("/")[0] if model and "/" in model else (model or "unknown")

    def _format_messages(self, messages) -> str:
        if isinstance(messages, str):
            return messages
        if not isinstance(messages, list):
            return str(messages)
        parts = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            parts.append(f"[{role}]\n{content}")
        return "\n\n".join(parts)

    def _write(self, server: str, type: str, text: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        separator = "=" * 80
        block = f"{timestamp} | {server} | {type}\n{separator}\n{text}\n{separator}\n\n"
        with self._log_path.open("a") as f:
            f.write(block)

    def _on_completed(self, source, event: LLMCallCompletedEvent) -> None:
        server = self._server_for(event.model or "")
        prompt_text = self._format_messages(event.messages or [])
        self._write(server, "prompt", prompt_text)
        response_text = event.response if isinstance(event.response, str) else str(event.response)
        self._write(server, "response", response_text)


@contextmanager
def verbose_to_file(log_path: Path):
    """Redirect stdout to log_path for the duration of the block, then restore."""
    real_stdout = sys.stdout
    log_path.parent.mkdir(parents=True, exist_ok=True)
    f = log_path.open("w")
    sys.stdout = f
    try:
        yield
    finally:
        sys.stdout = real_stdout
        f.close()


def setup_instrumentation(
    timestamp: str, logs_dir: Path | None = None, config_path: Path | None = None
) -> tuple[Path, Path, "_PromptLogger"]:
    """Create log paths, subscribe prompt logger to CrewAI event bus, return (verbose_path, prompts_path, logger)."""
    if logs_dir is None:
        logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    verbose_path = logs_dir / f"verbose_{timestamp}.log"
    prompts_path = logs_dir / f"prompts_{timestamp}.log"

    server_map = _build_server_map(config_path) if config_path and config_path.exists() else {}
    logger = _PromptLogger(prompts_path, server_map=server_map)
    crewai_event_bus.on(LLMCallCompletedEvent)(logger._on_completed)
    return verbose_path, prompts_path, logger
