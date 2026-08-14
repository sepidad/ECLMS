"""Semantic search domain: deterministic embeddings and an in-memory vector index.

Phase 4 Intelligence.  No external embedding API is assumed; text is
embedded into a fixed-dimension vector of hashed token n-grams and ranked
by cosine similarity.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from hashlib import blake2b
from itertools import pairwise

_TOKEN_RE = re.compile(r"[a-z0-9']+")

DEFAULT_DIMENSIONS = 256


def _hash(token: str, salt: str, dim: int) -> int:
  """Return a signed index in ``range(dim)`` from a token and feature salt."""
  digest = blake2b((salt + token).encode('utf-8'), digest_size=8).digest()
  value = int.from_bytes(digest, 'big')
  return (value % dim) - (dim // 2)


def tokenize(text: str) -> list[str]:
  """Lowercase word tokens (with 1- and 2-gram features appended)."""
  words = _TOKEN_RE.findall(text.lower())
  tokens = list(words)
  for a, b in pairwise(words):
    tokens.append(f'{a}_{b}')
  return tokens


def embed(text: str, *, dim: int = DEFAULT_DIMENSIONS) -> list[float]:
  """Embed text into a fixed-dimension sparse vector (feature hashing)."""
  vector = [0.0] * dim
  for token in tokenize(text):
    index = _hash(token, 'eclms-embed', dim)
    vector[index] += 1.0
  return vector


def cosine_similarity(a: list[float], b: list[float]) -> float:
  """Cosine similarity between two equal-length vectors."""
  if len(a) != len(b) or not a:
    return 0.0
  dot = sum(x * y for x, y in zip(a, b))
  norm_a = math.sqrt(sum(x * x for x in a))
  norm_b = math.sqrt(sum(y * y for y in b))
  if norm_a == 0.0 or norm_b == 0.0:
    return 0.0
  return dot / (norm_a * norm_b)


@dataclass
class IndexedDocument:
  """A document (contract version text) held in the vector index."""

  document_id: str
  contract_id: str
  title: str
  text: str
  organization_id: str
  vector: list[float]

  def to_result(self, score: float) -> dict:
    return {
      'contract_id': self.contract_id,
      'document_id': self.document_id,
      'title': self.title,
      'similarity_score': round(score, 4),
      'snippet': self.text[:300],
    }


class InMemoryVectorIndex:
  """Org-scoped in-memory vector index over embedded documents."""

  def __init__(self, *, dim: int = DEFAULT_DIMENSIONS) -> None:
    self._dim = dim
    self._documents: list[IndexedDocument] = []

  def upsert(self, document: IndexedDocument) -> None:
    existing = next(
      (i for i, d in enumerate(self._documents) if d.document_id == document.document_id),
      None,
    )
    if existing is not None:
      self._documents[existing] = document
    else:
      self._documents.append(document)

  def search(
    self,
    query: str,
    *,
    organization_id: str,
    limit: int = 10,
  ) -> list[dict]:
    query_vector = embed(query, dim=self._dim)
    scored: list[tuple[float, IndexedDocument]] = []
    for document in self._documents:
      if document.organization_id != organization_id:
        continue
      score = cosine_similarity(query_vector, document.vector)
      if score > 0.0:
        scored.append((score, document))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [document.to_result(score) for score, document in scored[:limit]]

  def clear(self, organization_id: str | None = None) -> None:
    if organization_id is None:
      self._documents.clear()
    else:
      self._documents = [d for d in self._documents if d.organization_id != organization_id]

  @property
  def size(self) -> int:
    return len(self._documents)
