# ABOUTME: LiteLLM wrapper — call_llm() and call_llm_async() assemble messages and call litellm.
# ABOUTME: Provides setup_llm_logging() to enable per-call summary logging to a file.

import asyncio
import inspect
import logging
import time
from pathlib import Path

import litellm
import yaml

_log = logging.getLogger(__name__)

from showrunner.config import load_agent_configs

_prompt_logger = None
_PROMPTS_DIR = Path(__file__).parent.parent.parent / "config" / "prompts"
_CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
_WORLD_YAML = Path(__file__).parent.parent.parent / "skin" / "world.yaml"


def setup_llm_logging(log_path: Path, dump_dir: Path | None = None) -> None:
    """Enable prompt/response logging for all call_llm() calls."""
    global _prompt_logger
    from showrunner.instrumentation import _PromptLogger
    _prompt_logger = _PromptLogger(log_path, dump_dir=dump_dir)


def load_task_prompt(name: str) -> str:
    """Load a task prompt template from config/prompts/task_{name}.md."""
    return (_PROMPTS_DIR / f"task_{name}.md").read_text()


def load_yaml_task_prompt(name: str, **kwargs) -> str:
    """Load a YAML task prompt template and format with kwargs.

    The YAML file must have a `user_template` key with Python str.format() placeholders.
    """
    data = yaml.safe_load((_PROMPTS_DIR / f"task_{name}.yaml").read_text())
    return data["user_template"].format(**kwargs)


def _load_world_yaml() -> dict:
    """Load skin/world.yaml and return the parsed dict."""
    with open(_WORLD_YAML) as f:
        return yaml.safe_load(f)


def _load_world_description(tier: str) -> str:
    """Return the world description for the given model tier (large/medium/small)."""
    data = _load_world_yaml()
    descriptions = data["world"]["description"]
    return descriptions.get(tier) or descriptions.get("medium", "")


def build_system_prompt(agent_name: str) -> str:
    """Build a system prompt: world context prefix + agent role definition."""
    cfg = load_agent_configs()[agent_name]
    tier = cfg.get("context_tier") or "medium"
    world = _load_world_description(tier)

    prompt_file = cfg.get("prompt_file")
    if prompt_file:
        agent = (_CONFIG_DIR / prompt_file).read_text()
    else:
        agent = f"You are {cfg['role']}.\n\n{cfg['goal']}\n\n{cfg['backstory']}"

    return f"{world}\n\n{agent}"


def call_llm(agent_name: str, system_prompt: str, user_message: str, label: str = "") -> str:
    """Call litellm with the given agent's model params; return the response content."""
    cfg = load_agent_configs()[agent_name]
    params = cfg["litellm_params"]
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    kwargs: dict = {
        "model": params["model"],
        "messages": messages,
    }
    if "api_base" in params:
        kwargs["api_base"] = params["api_base"]
    if "api_key" in params:
        kwargs["api_key"] = params["api_key"]
    kwargs["temperature"] = cfg.get("temperature", 0.7)
    # Gemini 2.5 thinking mode disabled — we want direct answers, not chain-of-thought
    if "gemini-2.5" in params["model"]:
        kwargs["thinking"] = {"type": "disabled"}

    max_ctx = cfg.get("max_context_tokens")
    if max_ctx:
        estimated = (len(system_prompt) + len(user_message)) // 4
        if estimated > max_ctx:
            _log.warning(
                "Context pre-flight: agent=%s estimated=%d tokens exceeds max_context_tokens=%d",
                agent_name, estimated, max_ctx,
            )

    _MAX_RETRIES = 5
    _BACKOFF_BASE = 2  # seconds; doubles each attempt: 2, 4, 8, 16, 32
    for attempt in range(_MAX_RETRIES + 1):
        try:
            response = litellm.completion(**kwargs)
            break
        except litellm.exceptions.ServiceUnavailableError as exc:
            if attempt == _MAX_RETRIES:
                raise
            wait = _BACKOFF_BASE ** attempt
            print(f"[showrunner] Gemini unavailable (503) — retrying in {wait}s (attempt {attempt + 1}/{_MAX_RETRIES})...")
            time.sleep(wait)

    content = response.choices[0].message.content

    if _prompt_logger is not None:
        server = cfg["model_alias"].split("/")[0]
        step = inspect.currentframe().f_back.f_code.co_name
        _prompt_logger.log(
            agent_name, server, step,
            len(system_prompt) + len(user_message), len(content),
            label=label, system_prompt=system_prompt, user_message=user_message, response=content,
        )

    return content


async def call_llm_async(agent_name: str, system_prompt: str, user_message: str, label: str = "") -> str:
    """Async version of call_llm; uses litellm.acompletion(). Same interface and logging."""
    cfg = load_agent_configs()[agent_name]
    params = cfg["litellm_params"]
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    kwargs: dict = {
        "model": params["model"],
        "messages": messages,
    }
    if "api_base" in params:
        kwargs["api_base"] = params["api_base"]
    if "api_key" in params:
        kwargs["api_key"] = params["api_key"]
    kwargs["temperature"] = cfg.get("temperature", 0.7)
    if "gemini-2.5" in params["model"]:
        kwargs["thinking"] = {"type": "disabled"}

    max_ctx = cfg.get("max_context_tokens")
    if max_ctx:
        estimated = (len(system_prompt) + len(user_message)) // 4
        if estimated > max_ctx:
            _log.warning(
                "Context pre-flight: agent=%s estimated=%d tokens exceeds max_context_tokens=%d",
                agent_name, estimated, max_ctx,
            )

    _MAX_RETRIES = 5
    _BACKOFF_BASE = 2
    for attempt in range(_MAX_RETRIES + 1):
        try:
            response = await litellm.acompletion(**kwargs)
            break
        except litellm.exceptions.ServiceUnavailableError as exc:
            if attempt == _MAX_RETRIES:
                raise
            wait = _BACKOFF_BASE ** attempt
            print(f"[showrunner] Gemini unavailable (503) — retrying in {wait}s (attempt {attempt + 1}/{_MAX_RETRIES})...")
            await asyncio.sleep(wait)

    content = response.choices[0].message.content

    if _prompt_logger is not None:
        server = cfg["model_alias"].split("/")[0]
        step = inspect.currentframe().f_back.f_code.co_name
        _prompt_logger.log(
            agent_name, server, step,
            len(system_prompt) + len(user_message), len(content),
            label=label, system_prompt=system_prompt, user_message=user_message, response=content,
        )

    return content
