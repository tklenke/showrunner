# ABOUTME: Tests for the YAML config loader — verifies agent configs and LiteLLM routing.
# ABOUTME: Checks all five agents load correctly with the right models and endpoints.

import os
import pytest


@pytest.fixture(autouse=True)
def gemini_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")


def test_load_agent_configs_returns_all_agents():
    from showrunner.config import load_agent_configs
    configs = load_agent_configs()
    assert set(configs.keys()) == {"show_runner", "narrator", "actors", "referee", "scribe"}


def test_each_agent_has_required_fields():
    from showrunner.config import load_agent_configs
    configs = load_agent_configs()
    for name, cfg in configs.items():
        for field in ("role", "goal", "backstory", "litellm_params"):
            assert field in cfg, f"{name} missing field: {field}"


def test_litellm_params_contains_model():
    from showrunner.config import load_agent_configs
    configs = load_agent_configs()
    for name, cfg in configs.items():
        assert "model" in cfg["litellm_params"], f"{name} litellm_params missing model"


def test_show_runner_uses_gemini():
    from showrunner.config import load_agent_configs
    configs = load_agent_configs()
    assert "gemini" in configs["show_runner"]["litellm_params"]["model"].lower()


def test_narrator_uses_gemini():
    from showrunner.config import load_agent_configs
    configs = load_agent_configs()
    assert "gemini" in configs["narrator"]["litellm_params"]["model"].lower()


def test_referee_uses_gemini():
    from showrunner.config import load_agent_configs
    configs = load_agent_configs()
    assert "gemini" in configs["referee"]["litellm_params"]["model"].lower()


def test_scribe_uses_gemini():
    from showrunner.config import load_agent_configs
    configs = load_agent_configs()
    assert "gemini" in configs["scribe"]["litellm_params"]["model"].lower()


def test_actors_uses_gemini():
    from showrunner.config import load_agent_configs
    configs = load_agent_configs()
    assert "gemini" in configs["actors"]["litellm_params"]["model"].lower()


def test_load_agent_configs_has_no_verbose_field():
    from showrunner.config import load_agent_configs
    configs = load_agent_configs()
    for name, cfg in configs.items():
        assert "verbose" not in cfg, f"{name} config unexpectedly has 'verbose' field"


def test_load_agent_configs_has_no_allow_delegation_field():
    from showrunner.config import load_agent_configs
    configs = load_agent_configs()
    for name, cfg in configs.items():
        assert "allow_delegation" not in cfg, f"{name} config unexpectedly has 'allow_delegation' field"


def test_apply_litellm_settings_sets_drop_params():
    import litellm
    from showrunner.config import apply_litellm_settings
    apply_litellm_settings()
    assert litellm.drop_params is True


def test_apply_litellm_settings_sets_timeout():
    import litellm
    from showrunner.config import apply_litellm_settings
    apply_litellm_settings()
    assert litellm.request_timeout == 120


def test_apply_litellm_settings_sets_retries():
    import litellm
    from showrunner.config import apply_litellm_settings
    apply_litellm_settings()
    assert litellm.num_retries == 2
