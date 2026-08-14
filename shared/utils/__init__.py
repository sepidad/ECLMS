"""Shared, dependency-free utility helpers.

Kept intentionally tiny: anything with a module-specific purpose belongs
inside the owning module.
"""

from __future__ import annotations

from typing import Any


def snake_to_camel(name: str) -> str:
  """Convert snake_case to camelCase for API boundary mapping."""
  parts = name.split('_')
  return parts[0] + ''.join(p.capitalize() for p in parts[1:])


def camel_to_snake(name: str) -> str:
  """Convert camelCase to snake_case for internal identifiers."""
  chars: list[str] = []
  for char in name:
    if char.isupper():
      chars.append('_')
      chars.append(char.lower())
    else:
      chars.append(char)
  return ''.join(chars).lstrip('_')


def clean_none(payload: dict[str, Any]) -> dict[str, Any]:
  """Return a copy of a dictionary with None values removed."""
  return {k: v for k, v in payload.items() if v is not None}
