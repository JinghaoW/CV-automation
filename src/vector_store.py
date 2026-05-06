"""Vector store integration with Qdrant and an in-memory fallback.

This module provides:
- QdrantStore: minimal Qdrant client wrapper for upsert/search
- InMemoryVectorStore: deterministic, test-friendly fallback
- embed_texts helper with simple caching and batching (embed_fn must be provided)

Design goals:
- Caller supplies an embedding function `embed_fn(texts: list[str]) -> list[list[float]]`.
- Storage APIs accept vectors (so embedding generation can be swapped easily).
- Batch upserts and searches supported.
- A small in-memory cache reduces repeated embedding calls.
"""
from __future__ import annotations

import math
import os
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple
from functools import lru_cache

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import PointStruct, Filter
except Exception:  # pragma: no cover - optional dependency
    QdrantClient = None
    PointStruct = None
    Filter = None


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b:
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0 or nb == 0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


class InMemoryVectorStore:
    """Simple in-memory store used for tests or when Qdrant is unavailable."""

    def __init__(self, dim: Optional[int] = None) -> None:
        self.dim = dim
        self._points: Dict[str, Tuple[List[float], Dict[str, Any]]] = {}

    def upsert(self, items: Iterable[Tuple[str, List[float], Dict[str, Any]]]) -> None:
        for _id, vector, payload in items:
            if self.dim is None:
                self.dim = len(vector)
            self._points[_id] = (vector, payload or {})

    def search(self, vector: List[float], top_k: int = 10) -> List[Tuple[str, float, Dict[str, Any]]]:
        results: List[Tuple[str, float, Dict[str, Any]]] = []
        for _id, (vec, payload) in self._points.items():
            score = _cosine(vector, vec)
            results.append((_id, score, payload))
        results.sort(key=lambda t: t[1], reverse=True)
        return results[:top_k]

    def get(self, _id: str) -> Optional[Tuple[List[float], Dict[str, Any]]]:
        return self._points.get(_id)


class QdrantStore:
    """Minimal Qdrant-backed vector store wrapper.

    Note: this wrapper expects a Qdrant instance; if the `qdrant-client` library
    is not installed, an ImportError will be raised at instantiation time.
    """

    def __init__(self, url: str, api_key: Optional[str], collection_name: str, dim: int) -> None:
        if QdrantClient is None:
            raise RuntimeError("qdrant-client is not installed")
        self.client = QdrantClient(url=url, api_key=api_key) if api_key else QdrantClient(url=url)
        self.collection = collection_name
        self.dim = dim
        # ensure collection exists
        try:
            if not self.client.get_collection(self.collection):
                self.client.recreate_collection(collection_name=self.collection, vector_size=self.dim)
        except Exception:
            # attempt to create
            try:
                self.client.recreate_collection(collection_name=self.collection, vector_size=self.dim)
            except Exception as exc:
                raise

    def upsert(self, items: Iterable[Tuple[str, List[float], Dict[str, Any]]]) -> None:
        batch: List[PointStruct] = []
        for _id, vector, payload in items:
            batch.append(PointStruct(id=_id, vector=vector, payload=payload))
            if len(batch) >= 64:
                self.client.upsert(collection_name=self.collection, points=batch)
                batch = []
        if batch:
            self.client.upsert(collection_name=self.collection, points=batch)

    def search(self, vector: List[float], top_k: int = 10) -> List[Tuple[str, float, Dict[str, Any]]]:
        res = self.client.search(collection_name=self.collection, query_vector=vector, limit=top_k)
        out: List[Tuple[str, float, Dict[str, Any]]] = []
        for hit in res:
            out.append((str(hit.id), float(hit.score), hit.payload or {}))
        return out

    def get(self, _id: str) -> Optional[Tuple[List[float], Dict[str, Any]]]:
        try:
            result = self.client.retrieve(collection_name=self.collection, ids=[_id])
            if not result or not getattr(result, "result", None):
                return None
            p = result.result[0]
            return (p.vector, p.payload or {})
        except Exception:
            return None


class VectorStore:
    """Facade that picks QdrantStore when available or InMemoryVectorStore.

    The caller should provide an `embed_fn(texts: list[str]) -> list[list[float]]` for
    embedding generation; `embed_texts` provides a cached wrapper.
    """

    def __init__(
        self,
        collection: str = "cv_jobs",
        dim: Optional[int] = None,
        qdrant_url: Optional[str] = None,
        qdrant_api_key: Optional[str] = None,
    ) -> None:
        self.collection = collection
        self.dim = dim
        self.qdrant_url = qdrant_url or os.environ.get("QDRANT_URL")
        self.qdrant_api_key = qdrant_api_key or os.environ.get("QDRANT_API_KEY")
        if self.qdrant_url and QdrantClient is not None and self.dim is not None:
            try:
                self._impl = QdrantStore(self.qdrant_url, self.qdrant_api_key, collection, self.dim)
            except Exception:
                self._impl = InMemoryVectorStore(dim=self.dim)
        else:
            self._impl = InMemoryVectorStore(dim=self.dim)
        # small in-memory cache for embeddings
        self._embed_cache: Dict[str, Tuple[float, ...]] = {}

    def upsert_batch(self, items: Iterable[Tuple[str, List[float], Dict[str, Any]]], batch_size: int = 64) -> None:
        # delegate to implementation; implementation handles batching where supported
        self._impl.upsert(items)

    def search_similar(self, vector: List[float], top_k: int = 10) -> List[Tuple[str, float, Dict[str, Any]]]:
        return self._impl.search(vector, top_k=top_k)

    def get(self, _id: str) -> Optional[Tuple[List[float], Dict[str, Any]]]:
        return self._impl.get(_id)

    def embed_texts(self, texts: Sequence[str], embed_fn: Callable[[List[str]], List[List[float]]], batch_size: int = 32) -> List[List[float]]:
        """Generate embeddings for texts using embed_fn with a small cache and batching.

        embed_fn should be a callable that accepts a list of strings and returns a list of vectors.
        """
        out: List[List[float]] = []
        pending: List[str] = []
        pending_idx: List[int] = []

        for i, t in enumerate(texts):
            key = t
            if key in self._embed_cache:
                out.append(list(self._embed_cache[key]))
                continue
            pending.append(t)
            pending_idx.append(i)
            # emit batch when large enough or last
            if len(pending) >= batch_size:
                vectors = embed_fn(pending)
                for txt, vec in zip(pending, vectors):
                    self._embed_cache[txt] = tuple(vec)
                    out.append(list(vec))
                pending = []
                pending_idx = []
        if pending:
            vectors = embed_fn(pending)
            for txt, vec in zip(pending, vectors):
                self._embed_cache[txt] = tuple(vec)
                out.append(list(vec))
        return out


__all__ = ["VectorStore", "InMemoryVectorStore", "QdrantStore", "_cosine"]

