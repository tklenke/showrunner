# ABOUTME: Loads agent and LiteLLM config from YAML files and resolves CrewAI LLM objects.
# ABOUTME: Single source of truth for model routing — all agents call load_agent_configs().

import os
from pathlib import Path

import yaml
from crewai import LLM

_CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


def _load_yaml(filename: str) -> dict:
    with open(_CONFIG_DIR / filename) as f:
        return yaml.safe_load(f)


def _resolve_api_key(raw: str) -> str:
    """Resolve 'os.environ/VAR_NAME' references to their env values."""
    if raw and raw.startswith("os.environ/"):
        return os.environ.get(raw.split("/", 1)[1], "")
    return raw


def _build_llm_registry() -> dict:
    """Return {model_alias: LLM instance} from litellm.yaml."""
    litellm_cfg = _load_yaml("litellm.yaml")
    registry = {}
    for entry in litellm_cfg.get("model_list", []):
        alias = entry["model_name"]
        params = entry["litellm_params"]
        kwargs = {"model": params["model"]}
        if "api_base" in params:
            kwargs["base_url"] = params["api_base"]
        kwargs["api_key"] = _resolve_api_key(params.get("api_key", "not-required"))
        # Gemini 2.5 thinking mode is disabled — we want direct answers, not chain-of-thought
        if "gemini-2.5" in params["model"]:
            kwargs["thinking"] = {"type": "disabled"}
        registry[alias] = LLM(**kwargs)
    return registry


def load_agent_configs() -> dict:
    """Return {agent_name: config_dict} with resolved LLM objects.

    Each config dict has: role, goal, backstory, llm, verbose, allow_delegation.
    """
    agents_yaml = _load_yaml("agents.yaml")
    llm_registry = _build_llm_registry()
    result = {}
    for name, cfg in agents_yaml.items():
        model_alias = cfg.get("model", "")
        llm = llm_registry.get(model_alias)
        if llm is None:
            raise ValueError(f"Agent '{name}' references unknown model alias '{model_alias}'")
        result[name] = {
            "role": cfg["role"],
            "goal": cfg["goal"].strip(),
            "backstory": cfg["backstory"].strip(),
            "llm": llm,
            "verbose": cfg.get("verbose", False),
            "allow_delegation": cfg.get("allow_delegation", False),
        }
    return result
