# ABOUTME: Tests for the YAML config loader — verifies agent configs and LLM routing.
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
        for field in ("role", "goal", "backstory", "llm", "verbose", "allow_delegation"):
            assert field in cfg, f"{name} missing field: {field}"


def test_show_runner_uses_sardinia():
    from showrunner.config import load_agent_configs
    configs = load_agent_configs()
    assert "llama-3.1-8b" in configs["show_runner"]["llm"].model.lower()


def test_show_runner_disables_delegation():
    from showrunner.config import load_agent_configs
    configs = load_agent_configs()
    assert configs["show_runner"]["allow_delegation"] is False


def test_narrator_uses_sardinia_endpoint():
    from showrunner.config import load_agent_configs
    configs = load_agent_configs()
    assert "192.168.1.45" in (configs["narrator"]["llm"].base_url or "")


def test_referee_uses_alien_endpoint():
    from showrunner.config import load_agent_configs
    configs = load_agent_configs()
    assert "192.168.1.144" in (configs["referee"]["llm"].base_url or "")


def test_scribe_uses_alien_endpoint():
    from showrunner.config import load_agent_configs
    configs = load_agent_configs()
    assert "192.168.1.144" in (configs["scribe"]["llm"].base_url or "")


def test_actors_uses_sardinia_endpoint():
    from showrunner.config import load_agent_configs
    configs = load_agent_configs()
    assert "192.168.1.45" in (configs["actors"]["llm"].base_url or "")
