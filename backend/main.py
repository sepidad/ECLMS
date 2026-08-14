"""ECLMS application entrypoint (uvicorn backend.main:app)."""

from backend.bootstrap.application import app

__all__ = ['app']
