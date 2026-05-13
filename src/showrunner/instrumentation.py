# ABOUTME: Session instrumentation — prompt/response logging and log path setup.
# ABOUTME: _PromptLogger is used by llm.py to write prompt/response pairs to a log file.

from datetime import datetime
from pathlib import Path


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


def setup_instrumentation(
    timestamp: str, logs_dir: Path | None = None, config_path: Path | None = None
) -> tuple[Path, Path]:
    """Create log paths, wire LLM prompt logging, return (verbose_path, prompts_path)."""
    if logs_dir is None:
        logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    verbose_path = logs_dir / f"verbose_{timestamp}.log"
    prompts_path = logs_dir / f"prompts_{timestamp}.log"

    import showrunner.llm
    showrunner.llm.setup_llm_logging(prompts_path)
    return verbose_path, prompts_path
