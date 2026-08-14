from backend.config import get_settings
from infrastructure.storage.local import LocalStorageProvider
from infrastructure.storage.provider import StorageProvider
from infrastructure.storage.s3 import S3StorageProvider


def get_storage_provider() -> StorageProvider:
  """Return the configured storage provider (local filesystem or S3)."""
  settings = get_settings()
  if settings.storage_backend.lower() == 's3':
    return S3StorageProvider()
  return LocalStorageProvider()


__all__ = [
  'LocalStorageProvider',
  'S3StorageProvider',
  'StorageProvider',
  'get_storage_provider',
]
