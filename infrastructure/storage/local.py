"""Local filesystem storage provider.

Stores document binaries on the local filesystem under a configurable
root directory.  Production deployments replace this with object storage
(S3-compatible, etc.) via the same StorageProvider contract.
"""

from __future__ import annotations

from pathlib import Path

from backend.config import get_settings
from backend.core.exceptions import StorageError
from infrastructure.storage.provider import StorageProvider


class LocalStorageProvider(StorageProvider):
  """Stores blobs as files under <root>/<key>."""

  def __init__(self, root: str | None = None) -> None:
    self._root = Path(root or get_settings().storage_root).resolve()

  def _path(self, key: str) -> Path:
    return self._root / key

  async def put(self, key: str, content: bytes, *, content_type: str | None = None) -> None:
    try:
      self._path(key).parent.mkdir(parents=True, exist_ok=True)
      self._path(key).write_bytes(content)
    except OSError as exc:
      raise StorageError(f'Failed to store blob: {key}') from exc

  async def get(self, key: str) -> bytes:
    try:
      return self._path(key).read_bytes()
    except OSError as exc:
      raise StorageError(f'Failed to read blob: {key}') from exc

  async def delete(self, key: str) -> None:
    try:
      self._path(key).unlink(missing_ok=True)
    except OSError as exc:
      raise StorageError(f'Failed to delete blob: {key}') from exc

  async def exists(self, key: str) -> bool:
    return self._path(key).is_file()
