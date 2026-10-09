"""A small tool registry with explicit schemas, timeouts and read-only first.

Tools are an extension point, not yet wired into the chat loop: generated text
and memory remain separate from tool execution. Handlers run off the event
loop with a per-tool timeout.
"""
from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    handler: Callable[[dict[str, Any]], Any]
    timeout_seconds: float = 5.0
    read_only: bool = True


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    output: Any = None
    error: str | None = None


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}
        self._pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=4, thread_name_prefix="tool"
        )

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            raise ValueError(f"Tool already registered: {spec.name!r}")
        self._tools[spec.name] = spec

    def names(self) -> list[str]:
        return sorted(self._tools)

    def specs(self) -> list[ToolSpec]:
        return [self._tools[name] for name in self.names()]

    def execute(self, name: str, arguments: dict[str, Any] | None = None) -> ToolResult:
        spec = self._tools.get(name)
        if spec is None:
            return ToolResult(ok=False, error=f"Unknown tool: {name!r}")

        arguments = arguments or {}
        try:
            _validate_arguments(spec, arguments)
        except ValueError as exc:
            return ToolResult(ok=False, error=str(exc))

        future = self._pool.submit(spec.handler, arguments)
        try:
            return ToolResult(ok=True, output=future.result(timeout=spec.timeout_seconds))
        except concurrent.futures.TimeoutError:
            future.cancel()
            return ToolResult(
                ok=False, error=f"Tool {name!r} timed out after {spec.timeout_seconds}s"
            )
        except Exception as exc:  # noqa: BLE001 - surfaced as a typed result
            return ToolResult(ok=False, error=str(exc))


def _validate_arguments(spec: ToolSpec, arguments: dict[str, Any]) -> None:
    schema = spec.input_schema
    properties = schema.get("properties", {})
    missing = [key for key in schema.get("required", []) if key not in arguments]
    if missing:
        raise ValueError(f"Missing required tool arguments: {', '.join(missing)}")
    if schema.get("additionalProperties") is False:
        unexpected = [key for key in arguments if key not in properties]
        if unexpected:
            raise ValueError(f"Unexpected tool arguments: {', '.join(unexpected)}")


def _current_time(_arguments: dict[str, Any]) -> dict[str, str]:
    return {"utc": datetime.now(timezone.utc).isoformat()}


CURRENT_TIME = ToolSpec(
    name="current_time",
    description="Return the current time in UTC as an ISO-8601 string.",
    input_schema={"type": "object", "properties": {}, "additionalProperties": False},
    output_schema={
        "type": "object",
        "properties": {"utc": {"type": "string"}},
        "required": ["utc"],
        "additionalProperties": False,
    },
    handler=_current_time,
    timeout_seconds=2.0,
    read_only=True,
)


def build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(CURRENT_TIME)
    return registry
