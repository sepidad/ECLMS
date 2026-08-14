"""Storage abstraction (integration/06_Document_Integration.md).

Documents are first-class business assets.  The storage provider
contract isolates the document module from the concrete file backend.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class StorageProvider(ABC):
  """Contract for binary object storage."""

  @abstractmethod
  async def put(self, key: str, content: bytes, *, content_type: str | None = None) -> None:
    raise NotImplementedError

  @abstractmethod
  async def get(self, key: str) -> bytes:
    raise NotImplementedError

  @abstractmethod
  async def delete(self, key: str) -> None:
    raise NotImplementedError

  @abstractmethod
  async def exists(self, key: str) -> bool:
    raise NotImplementedError
