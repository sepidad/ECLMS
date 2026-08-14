"""Migration smoke tests for the complete schema chain."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path


def test_alembic_upgrade_head_creates_integration_history_tables():
  """A fresh deployment must create every table used by integrations."""
  database_url = os.environ['ECLMS_DATABASE_URL']
  prefix = 'sqlite+aiosqlite:///'
  assert database_url.startswith(prefix)
  database_path = Path(database_url[len(prefix):])

  result = subprocess.run(
    [sys.executable, '-m', 'alembic', 'upgrade', 'head'],
    cwd=Path(__file__).resolve().parents[1],
    env=os.environ.copy(),
    capture_output=True,
    text=True,
    timeout=60,
    check=False,
  )
  assert result.returncode == 0, result.stderr or result.stdout

  with sqlite3.connect(database_path) as connection:
    tables = {
      row[0]
      for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }

  assert {'email_deliveries', 'sms_deliveries', 'connector_syncs'} <= tables
