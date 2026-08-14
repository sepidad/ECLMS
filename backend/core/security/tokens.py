"""Security primitives.

Phase 0 ships a minimal, standards-aligned password hashing and token
utility.  Full authentication flows (OAuth/JWT/external IdP) are built
on top of these in the identity module (Phase 1).
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

import jwt


def generate_token(size: int = 32) -> str:
  """Generate a cryptographically random token string."""
  return secrets.token_urlsafe(size)


def sha256_hex(value: str) -> str:
  """Return a hex SHA-256 digest of the given value."""
  return hashlib.sha256(value.encode('utf-8')).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
  """Compare two strings in constant time to avoid timing attacks."""
  return hmac.compare_digest(a, b)


def create_jwt(payload: dict, secret: str, algorithm: str = 'HS256') -> str:
  """Create a signed JWT token."""
  return jwt.encode(payload, secret, algorithm=algorithm)


def decode_jwt(token: str, secret: str, algorithms: tuple[str, ...] = ('HS256',)) -> dict:
  """Decode and verify a JWT token, raising jwt.InvalidTokenError on failure."""
  return jwt.decode(token, secret, algorithms=list(algorithms))
