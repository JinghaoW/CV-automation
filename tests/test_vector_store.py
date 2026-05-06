"""Tests for the vector store implementation (uses the InMemory fallback)."""

from src.vector_store import InMemoryVectorStore, VectorStore


def test_inmemory_upsert_and_search():
    store = InMemoryVectorStore()
    v1 = [1.0, 0.0, 0.0]
    v2 = [0.0, 1.0, 0.0]
    store.upsert([("a", v1, {"title": "A"}), ("b", v2, {"title": "B"})])
    res = store.search([1.0, 0.0, 0.0], top_k=2)
    assert res[0][0] == "a"


def test_vectorstore_embed_cache_and_batching():
    # embed_fn returns a length-3 vector of ordinals for test determinism
    def embed_fn(texts):
        out = []
        for t in texts:
            vec = [float(len(t)), float(sum(ord(c) for c in t) % 100), 0.0]
            out.append(vec)
        return out

    vs = VectorStore()
    texts = ["a", "b", "a"]
    vectors = vs.embed_texts(texts, embed_fn=embed_fn, batch_size=2)
    assert len(vectors) == 3
    assert vectors[0] == vectors[2]

