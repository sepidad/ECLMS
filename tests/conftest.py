"""Shared pytest fixtures.

Tests run against a local SQLite database so they exercise the real
SQLAlchemy repositories without requiring a running PostgreSQL server.
"""


import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(scope='session')
def test_temp_roots():
  """Track fast per-test temp roots and remove them after the test session."""
  roots: list[Path] = []
  yield roots
  for root in roots:
    shutil.rmtree(root, ignore_errors=True)


@pytest.fixture
def tmp_path(test_temp_roots):
  """Provide a workspace-local temp path for deterministic Windows test runs.

  The default pytest temp root can be unusable on managed Windows machines
  when a stale directory is owned by another user. Keeping test artifacts in
  the repository workspace makes the suite independent of that global state.
  """
  base = Path.cwd() / '.pytest-temp'
  base.mkdir(parents=True, exist_ok=True)
  root = Path(tempfile.mkdtemp(prefix='pytest-', dir=base))
  test_temp_roots.append(root)
  yield root


@pytest.fixture(autouse=True)
def fresh_settings(monkeypatch, test_temp_roots):
  # Keep per-test isolation, but place SQLite files on the OS temp volume.
  # The repository may live on a slower mounted drive; SQLite schema creation
  # on that drive adds several seconds to every TestClient lifespan.
  temp_root = Path(tempfile.mkdtemp(prefix='eclms-pytest-'))
  test_temp_roots.append(temp_root)
  from backend.config import get_settings

  monkeypatch.setenv('ECLMS_DATABASE_URL', f'sqlite+aiosqlite:///{temp_root / "eclms.db"}')
  monkeypatch.setenv('ECLMS_STORAGE_ROOT', str(temp_root / 'storage'))
  get_settings.cache_clear()
  try:
    yield
  finally:
    get_settings.cache_clear()


@pytest.fixture
def authed_client():
  """A TestClient logged in as the seeded admin user.

  Returns a tuple (client, admin_headers) so tests can make authenticated
  requests against the RBAC-guarded endpoints.
  """
  from fastapi.testclient import TestClient

  from backend.main import app

  with TestClient(app) as client:
    login = client.post('/api/v1/identity/auth/login', json={'username': 'admin', 'password': 'admin'})
    assert login.json()['success'] is True
    token = login.json()['data']['access_token']
    yield client, {'Authorization': f'Bearer {token}'}
