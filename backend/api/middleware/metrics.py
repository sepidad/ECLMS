"""Prometheus-compatible metrics middleware and exporter.

Tracks request counts (per method/route), error counts, and a latency
histogram with fixed buckets.  Rendered by ``render_metrics`` in the
Prometheus text exposition format.
"""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

_REQUEST_COUNT = 0
_ERROR_COUNT = 0
_START_TIME = time.time()

#: Latency histogram buckets (seconds).
_LATENCY_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
_LATENCY_COUNTS: dict[int, int] = defaultdict(int)
_LATENCY_TOTAL: float = 0.0

#: Per-HTTP-status-class counters (2xx/3xx/4xx/5xx).
_STATUS_COUNTS: dict[int, int] = defaultdict(int)


class MetricsMiddleware(BaseHTTPMiddleware):
  async def dispatch(self, request: Request, call_next) -> Response:
    global _REQUEST_COUNT, _ERROR_COUNT, _LATENCY_TOTAL
    _REQUEST_COUNT += 1
    started = time.perf_counter()
    try:
      response = await call_next(request)
      if response.status_code >= 400:
        _ERROR_COUNT += 1
      return response
    except Exception:
      _ERROR_COUNT += 1
      _STATUS_COUNTS[500] += 1
      raise
    finally:
      elapsed = time.perf_counter() - started
      _LATENCY_TOTAL += elapsed
      _LATENCY_COUNTS[_bucket(elapsed)] += 1
      status = response.status_code if 'response' in locals() else 500
      _STATUS_COUNTS[status // 100 * 100] += 1


def _bucket(seconds: float) -> int:
  for upper in _LATENCY_BUCKETS:
    if seconds <= upper:
      return int(upper * 1000)
  return int(_LATENCY_BUCKETS[-1] * 1000) + 1


def _bucket_label(ms: int) -> str:
  return f'le="{ms / 1000:.3f}"'


def render_metrics() -> str:
  uptime = time.time() - _START_TIME
  lines = [
    '# HELP eclms_uptime_seconds Total uptime in seconds.',
    '# TYPE eclms_uptime_seconds gauge',
    f'eclms_uptime_seconds {uptime:.2f}',
    '',
    '# HELP eclms_http_requests_total Total HTTP requests processed.',
    '# TYPE eclms_http_requests_total counter',
    f'eclms_http_requests_total {_REQUEST_COUNT}',
    '',
    '# HELP eclms_http_errors_total Total HTTP requests resulting in 4xx/5xx.',
    '# TYPE eclms_http_errors_total counter',
    f'eclms_http_errors_total {_ERROR_COUNT}',
    '',
    '# HELP eclms_http_requests_by_status Total HTTP requests by status class.',
    '# TYPE eclms_http_requests_by_status counter',
  ]
  for status_class in sorted(_STATUS_COUNTS):
    lines.append(f'eclms_http_requests_by_status{{status="{status_class}"}} {_STATUS_COUNTS[status_class]}')
  lines += [
    '',
    '# HELP eclms_http_request_duration_seconds HTTP request latency histogram.',
    '# TYPE eclms_http_request_duration_seconds histogram',
  ]
  cumulative = 0
  for upper in _LATENCY_BUCKETS:
    cumulative += _LATENCY_COUNTS.get(int(upper * 1000), 0)
    lines.append(f'eclms_http_request_duration_seconds_bucket{{le="{upper:.3f}"}} {cumulative}')
  total_bucket = cumulative + _LATENCY_COUNTS.get(int(_LATENCY_BUCKETS[-1] * 1000) + 1, 0)
  lines.append(f'eclms_http_request_duration_seconds_bucket{{le="+Inf"}} {total_bucket}')
  lines.append(f'eclms_http_request_duration_seconds_sum {_LATENCY_TOTAL:.6f}')
  lines.append(f'eclms_http_request_duration_seconds_count {_REQUEST_COUNT}')
  return '\n'.join(lines)
