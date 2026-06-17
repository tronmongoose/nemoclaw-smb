"""
base.py — Skill abstraction and registry for NeMo Agent Toolkit integration.

Exports:
    Skill            — dataclass wrapping a callable skill with schema metadata
    register         — decorator-compatible registry insertion
    get              — retrieve a Skill by name
    all_skills       — list all registered Skill objects
    all_skills_names — list registered skill name strings
    run_skill        — dispatch name + args dict through the registry
    to_nat_function  — export a Skill as a NeMo Agent Toolkit function-config fragment
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class Skill:
    """Named, schema-annotated callable unit for NeMo Agent Toolkit dispatch."""

    name: str
    description: str
    input_schema: dict
    run: Callable[[dict], dict]


_REGISTRY: dict[str, Skill] = {}


def register(skill: Skill) -> Skill:
    """Insert a Skill into the global registry; returns the skill for decorator use."""
    _REGISTRY[skill.name] = skill
    return skill


def get(name: str) -> Skill:
    """Return the Skill for name; raises KeyError when not found."""
    if name not in _REGISTRY:
        raise KeyError(f"No skill registered: {name!r}")
    return _REGISTRY[name]


def all_skills() -> list[Skill]:
    """Return all registered Skill objects in insertion order."""
    return list(_REGISTRY.values())


def all_skills_names() -> list[str]:
    """Return all registered skill names in insertion order."""
    return list(_REGISTRY.keys())


def run_skill(name: str, args: dict) -> dict:
    """Dispatch args through the named skill; raises KeyError on unknown name."""
    return get(name).run(args)


def to_nat_function(skill: Skill) -> dict:
    """Export a Skill as a NeMo Agent Toolkit function-config fragment.

    The returned dict is a documented bridge to nvidia-nat conventions.
    nvidia-nat is NOT imported here; this is a serializable config fragment only.
    """
    return {
        "name": skill.name,
        "description": skill.description,
        "input_schema": skill.input_schema,
    }
