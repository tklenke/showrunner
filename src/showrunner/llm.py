# ABOUTME: LiteLLM wrapper — call_llm() assembles messages and calls litellm.completion().
# ABOUTME: Provides setup_llm_logging() to enable prompt/response logging to a file.

from pathlib import Path

import litellm

from showrunner.config import load_agent_configs

_prompt_logger = None


def setup_llm_logging(log_path: Path) -> None:
    """Enable prompt/response logging for all call_llm() calls."""
    global _prompt_logger
    from showrunner.instrumentation import _PromptLogger
    _prompt_logger = _PromptLogger(log_path)


def build_system_prompt(agent_name: str) -> str:
    """Build a system prompt from the agent's role, goal, and backstory config."""
    cfg = load_agent_configs()[agent_name]
    return f"You are {cfg['role']}.\n\n{cfg['goal']}\n\n{cfg['backstory']}"


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
        server = _prompt_logger._server_for(params["model"])
        _prompt_logger._write(server, "prompt", _prompt_logger._format_messages(messages))
        _prompt_logger._write(server, "response", content)

    return content
