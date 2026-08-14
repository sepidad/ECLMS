"""Tests for CSV export and document download routes (guard + presence).

Unauthenticated requests follow the EXEC-006 convention: HTTP 200 with an
``error.code: UNAUTHORIZED`` envelope.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app


def test_report_export_requires_auth():
  with TestClient(app) as client:
    r = client.get('/api/v1/reporting/export.csv')
    assert r.json()['error']['code'] == 'UNAUTHORIZED'


def test_document_download_requires_auth():
  with TestClient(app) as client:
    r = client.get('/api/v1/documents/00000000000000000000000000000000/download')
    assert r.json()['error']['code'] == 'UNAUTHORIZED'


def test_review_provider_query_param_routes_present():
  with TestClient(app) as client:
    for path in (
      '/api/v1/reporting/export.csv',
      '/api/v1/documents/x/download',
      '/api/v1/intelligence/review/x?provider=llm',
      '/api/v1/intelligence/review/x?provider=rules',
    ):
      r = client.get(path)
      assert r.json()['error']['code'] == 'UNAUTHORIZED'