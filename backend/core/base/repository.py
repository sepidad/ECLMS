"""Base repository contract.

Repositories isolate persistence from the application and domain layers.
Modules may implement their own repositories by extending this class;
the concrete implementation lives in the module's infrastructure layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from backend.core.base.entity import Entity

TEntity = TypeVar('TEntity', bound=Entity)


class BaseRepository(ABC, Generic[TEntity]):
  """Generic repository contract for a single aggregate type."""

  @abstractmethod
  async def get_by_id(self, entity_id: str) -> TEntity | None:
    raise NotImplementedError

  @abstractmethod
  async def save(self, entity: TEntity) -> TEntity:
    raise NotImplementedError

  @abstractmethod
  async def delete(self, entity: TEntity) -> None:
    raise NotImplementedError

  @abstractmethod
  async def list_all(self, *, limit: int = 100, offset: int = 0) -> list[TEntity]:
    raise NotImplementedError
