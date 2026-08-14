"""Tests for Prometheus metrics endpoint."""

from __future__ import annotations


def test_metrics_endpoint(authed_client):
  client, _headers = authed_client
  res = client.get('/metrics')
  assert res.status_code == 200
  text = res.text
  assert 'eclms_http_requests_total' in text
  assert 'eclms_http_errors_total' in text
  assert 'eclms_uptime_seconds' in text


def test_metrics_latency_histogram(authed_client):
  client, _headers = authed_client
  res = client.get('/metrics')
  assert res.status_code == 200
  text = res.text
  assert 'eclms_http_request_duration_seconds_bucket' in text
  assert 'eclms_http_request_duration_seconds_count' in text
  assert 'eclms_http_request_duration_seconds_sum' in text


def test_metrics_status_class_counter(authed_client):
  client, _headers = authed_client
  res = client.get('/metrics')
  assert res.status_code == 200
  text = res.text
  assert 'eclms_http_requests_by_status' in text
  assert 'status="200"' in text
