# ABOUTME: Loads agent and LiteLLM config from YAML files.
# ABOUTME: Single source of truth for model routing — all agents call load_agent_configs().

import os
from pathlib import Path

import litellm
import yaml

_CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


def _load_yaml(filename: str) -> dict:
    with open(_CONFIG_DIR / filename) as f:
        return yaml.safe_load(f)


def _resolve_api_key(raw: str) -> str:
    """Resolve 'os.environ/VAR_NAME' references to their env values."""
    if raw and raw.startswith("os.environ/"):
        return os.environ.get(raw.split("/", 1)[1], "")
    return raw


def _build_litellm_registry() -> dict:
    """Return {model_alias: litellm_params_dict} from litellm.yaml."""
    litellm_cfg = _load_yaml("litellm.yaml")
    registry = {}
    for entry in litellm_cfg.get("model_list", []):
        alias = entry["model_name"]
        params = entry["litellm_params"]
        result: dict = {"model": params["model"]}
        if "api_base" in params:
            result["api_base"] = params["api_base"]
        result["api_key"] = _resolve_api_key(params.get("api_key", "not-required"))
        registry[alias] = result
    return registry


def load_agent_configs() -> dict:
    """Return {agent_name: config_dict} with litellm call params.

    Each config dict has: role, goal, backstory, litellm_params, model_alias,
    prompt_file, context_tier.
    role/goal/backstory are empty strings for agents with a prompt_file.
    litellm_params contains: model, and optionally api_base and api_key.
    """
    agents_yaml = _load_yaml("agents.yaml")
    litellm_registry = _build_litellm_registry()
    result = {}
    for name, cfg in agents_yaml.items():
        model_alias = cfg.get("model", "")
        litellm_params = litellm_registry.get(model_alias)
        if litellm_params is None:
            raise ValueError(f"Agent '{name}' references unknown model alias '{model_alias}'")
        result[name] = {
            "role": cfg.get("role", ""),
            "goal": (cfg.get("goal") or "").strip(),
            "backstory": (cfg.get("backstory") or "").strip(),
            "litellm_params": litellm_params,
            "model_alias": model_alias,
            "prompt_file": cfg.get("prompt_file"),
            "context_tier": cfg.get("context_tier", "medium"),
        }
    return result


def apply_litellm_settings() -> None:
    """Apply litellm_settings from litellm.yaml to litellm globals."""
    litellm_cfg = _load_yaml("litellm.yaml")
    settings = litellm_cfg.get("litellm_settings", {})
    if "drop_params" in settings:
        litellm.drop_params = settings["drop_params"]
    if "request_timeout" in settings:
        litellm.request_timeout = settings["request_timeout"]
    if "num_retries" in settings:
        litellm.num_retries = settings["num_retries"]
