"""Persona selection and tool-registry tests (no GPU required)."""

import time

import pytest

from config import ConfigError, Settings
from personas import PERSONAS, get_persona, resolve_system_prompt
from tools import ToolSpec, build_default_registry


def test_expected_personas_exist():
    assert set(PERSONAS) == {"assistant", "character", "coding"}


def test_unknown_persona_is_rejected():
    with pytest.raises(ConfigError, match="Available"):
        get_persona("nope")


def test_system_prompt_override_wins():
    assert resolve_system_prompt("coding", "OVERRIDE") == "OVERRIDE"
    assert resolve_system_prompt("coding") == get_persona("coding").system_prompt


def test_config_defaults_to_assistant_persona():
    assert Settings.from_env({}).persona == "assistant"


def test_default_registry_exposes_read_only_tool():
    registry = build_default_registry()
    assert registry.names() == ["current_time"]
    assert registry.specs()[0].read_only is True
    result = registry.execute("current_time")
    assert result.ok and result.output["utc"]


def test_unknown_tool_and_bad_arguments_return_errors():
    registry = build_default_registry()
    assert registry.execute("missing").ok is False
    assert registry.execute("current_time", {"unexpected": 1}).ok is False


def test_duplicate_registration_is_rejected():
    registry = build_default_registry()
    with pytest.raises(ValueError):
        registry.register(registry.specs()[0])


def test_tool_timeout_is_enforced():
    registry = build_default_registry()
    registry.register(
        ToolSpec(
            name="slow",
            description="sleeps",
            input_schema={"type": "object", "properties": {}, "additionalProperties": False},
            output_schema={},
            handler=lambda _args: time.sleep(1),
            timeout_seconds=0.01,
        )
    )
    result = registry.execute("slow")
    assert result.ok is False and "timed out" in result.error
