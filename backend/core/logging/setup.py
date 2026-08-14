"""Structured logging foundation (operations/02_Logging_Model.md).

All application logs are emitted as structured JSON with a correlation
id so that logs, metrics and traces can be joined.  Sensitive data must
never be logged.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

_LOG_FORMAT = '%(asctime)s %(levelname)s %(name)s %(message)s'
_LEVELS = {
  'CRITICAL': logging.CRITICAL,
  'ERROR': logging.ERROR,
  'WARNING': logging.WARNING,
  'WARN': logging.WARNING,
  'INFO': logging.INFO,
  'DEBUG': logging.DEBUG,
  'TRACE': logging.DEBUG,
}


class JsonFormatter(logging.Formatter):
  """Emit each record as a single line of JSON."""

  def format(self, record: logging.LogRecord) -> str:
    payload: dict[str, Any] = {
      'timestamp': datetime.now(UTC).isoformat(),
      'level': record.levelname,
      'logger': record.name,
      'message': record.getMessage(),
    }
    trace_id = getattr(record, 'trace_id', None)
    if trace_id:
      payload['trace_id'] = trace_id
    for key in ('event_type', 'module', 'user_id', 'correlation_id'):
      value = getattr(record, key, None)
      if value is not None:
        payload[key] = value
    if record.exc_info:
      payload['exc_info'] = self.formatException(record.exc_info)
    return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = 'INFO', *, json_output: bool = True) -> None:
  """Configure the root logger.

  Args:
    level: One of DEBUG, INFO, WARNING, ERROR, CRITICAL.
    json_output: Emit structured JSON when True (production default),
      human-readable otherwise.
  """
  handler = logging.StreamHandler(sys.stdout)
  if json_output:
    handler.setFormatter(JsonFormatter())
  else:
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))

  root = logging.getLogger()
  root.handlers = [handler]
  root.setLevel(_LEVELS.get(level.upper(), logging.INFO))


def get_logger(name: str) -> logging.Logger:
  return logging.getLogger(name)


class TraceIdFilter(logging.Filter):
  """Attach the current request trace id to every log record."""

  def __init__(self, trace_provider) -> None:
    super().__init__()
    self._trace_provider = trace_provider

  def filter(self, record: logging.LogRecord) -> bool:
    trace_id = self._trace_provider()
    if trace_id:
      record.trace_id = trace_id
    return True
