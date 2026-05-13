# ABOUTME: LiteLLM wrapper — call_llm() assembles messages and calls litellm.completion().
# ABOUTME: Provides setup_llm_logging() to enable per-call summary logging to a file.

import inspect
from pathlib import Path

import litellm
import yaml

from showrunner.config import load_agent_configs

_prompt_logger = None
_PROMPTS_DIR = Path(__file__).parent.parent.parent / "config" / "prompts"
_CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
_WORLD_YAML = Path(__file__).parent.parent.parent / "skin" / "world.yaml"


def setup_llm_logging(log_path: Path) -> None:
    """Enable prompt/response logging for all call_llm() calls."""
    global _prompt_logger
    from showrunner.instrumentation import _PromptLogger
    _prompt_logger = _PromptLogger(log_path)


def load_task_prompt(name: str) -> str:
    """Load a task prompt template from config/prompts/task_{name}.md."""
    return (_PROMPTS_DIR / f"task_{name}.md").read_text()


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


def call_llm(agent_name: str, system_prompt: str, user_message: str) -> str:
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
    # Gemini 2.5 thinking mode disabled — we want direct answers, not chain-of-thought
    if "gemini-2.5" in params["model"]:
        kwargs["thinking"] = {"type": "disabled"}

    response = litellm.completion(**kwargs)
    content = response.choices[0].message.content

    if _prompt_logger is not None:
        server = cfg["model_alias"].split("/")[0]
        step = inspect.currentframe().f_back.f_code.co_name
        _prompt_logger.log(agent_name, server, step, len(system_prompt) + len(user_message), len(content))

    return content
