"""Request-scoped context (trace_id propagation).

Uses a contextvar so the trace id flows through async handlers,
services and logging without passing it as a parameter everywhere.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar, Token

trace_id_var: ContextVar[str] = ContextVar('trace_id', default='')


def get_trace_id() -> str:
  return trace_id_var.get()


def set_trace_id(trace_id: str | None = None) -> Token:
  value = trace_id or uuid.uuid4().hex
  return trace_id_var.set(value)


def reset_trace_id(token: Token) -> None:
  trace_id_var.reset(token)
