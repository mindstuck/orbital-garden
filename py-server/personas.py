"""Persona/profile definitions and selection rules.

A persona is just a named system prompt plus a short description. Selection is
explicit (`PERSONA`), with `SYSTEM_PROMPT` acting as an override. This keeps
the default assistant, a fictional character and a coding profile separable
before wake-word or tool-call switching is added.
"""
from __future__ import annotations

from dataclasses import dataclass

from config import ConfigError


@dataclass(frozen=True)
class Persona:
    name: str
    system_prompt: str
    description: str = ""


PERSONAS: dict[str, Persona] = {
    "assistant": Persona(
        name="assistant",
        system_prompt=(
            "You are a helpful, concise personal assistant. Answer clearly, "
            "avoid filler, and prefer plain sentences that sound natural when "
            "spoken aloud."
        ),
        description="Default general-purpose assistant.",
    ),
    "character": Persona(
        name="character",
        system_prompt=(
            "You are a fictional kuudere anime companion. Stay in character, "
            "keep replies concise, and speak naturally out loud."
        ),
        description="Fictional character persona for conversation.",
    ),
    "coding": Persona(
        name="coding",
        system_prompt=(
            "You are a pragmatic software engineering assistant. Be precise, "
            "prefer small correct changes, and explain trade-offs briefly."
        ),
        description="Coding partner profile.",
    ),
}


def get_persona(name: str) -> Persona:
    try:
        return PERSONAS[name]
    except KeyError as exc:
        available = ", ".join(sorted(PERSONAS))
        raise ConfigError(f"Unknown PERSONA {name!r}. Available: {available}.") from exc


def resolve_system_prompt(persona_name: str, override: str | None = None) -> str:
    """Return an explicit override if given, otherwise the persona prompt."""
    return override or get_persona(persona_name).system_prompt
