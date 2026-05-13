# ABOUTME: Session instrumentation — LiteLLM prompt/response logging and verbose stdout capture.
# ABOUTME: Registers a CustomLogger callback and provides a context manager for stdout redirection.

import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import litellm
import yaml
from litellm import CustomLogger


def _build_server_map(config_path: Path) -> dict[str, str]:
    """Build a reverse map from litellm_params.model → the server prefix of model_name."""
    config = yaml.safe_load(config_path.read_text())
    result = {}
    for entry in config.get("model_list", []):
        model_name = entry.get("model_name", "")
        prefix = model_name.split("/")[0]
        litellm_model = entry.get("litellm_params", {}).get("model", "")
        if litellm_model:
            result[litellm_model] = prefix
    return result


class _PromptLogger(CustomLogger):
    def __init__(self, server_map: dict, log_path: Path | None):
        super().__init__()
        self._server_map = server_map
        self._log_path = log_path

    def _server_for(self, model: str) -> str:
        return self._server_map.get(model, model)

    def _format_messages(self, messages: list) -> str:
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

    def log_pre_api_call(self, model, messages, kwargs):
        server = self._server_for(model)
        text = self._format_messages(messages)
        self._write(server, "prompt", text)

    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        model = kwargs.get("model", "")
        server = self._server_for(model)
        try:
            text = response_obj.choices[0].message.content
        except (AttributeError, IndexError):
            text = str(response_obj)
        self._write(server, "response", text)


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


def setup_instrumentation(timestamp: str) -> tuple[Path, Path]:
    """Register LiteLLM prompt logger and return (verbose_path, prompts_path)."""
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    verbose_path = logs_dir / f"verbose_{timestamp}.log"
    prompts_path = logs_dir / f"prompts_{timestamp}.log"

    config_path = Path("config/litellm.yaml")
    server_map = _build_server_map(config_path)

    litellm.callbacks = [_PromptLogger(server_map, prompts_path)]

    return verbose_path, prompts_path
