"""API versioning (EXEC-006 section 10).

All APIs are mounted under a versioned prefix.  v1 is the stable
baseline; later versions must remain backward compatible.

The configured api_v1_prefix already contains the version segment
(default: /api/v1), so module mounts become /api/v1/{module}.
"""

from __future__ import annotations

from backend.config import get_settings


def api_prefix() -> str:
  """Return the configured versioned API prefix (e.g. /api/v1)."""
  return get_settings().api_v1_prefix
