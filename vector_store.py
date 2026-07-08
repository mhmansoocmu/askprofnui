"""Chroma vector store for text-chat RAG (replaces TF-IDF)."""

from __future__ import annotations

import os
from pathlib import Path

import chromadb
from chromadb.config import Settings
from fastembed import TextEmbedding

CHROMA_DIR = Path(os.getenv("CHROMA_DIR", "chroma_db"))
COLLECTION_NAME = "askprofnui"
EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")

_embedder: TextEmbedding | None = None
_client: chromadb.ClientAPI | None = None


def _get_embedder() -> TextEmbedding:
    global _embedder
    if _embedder is None:
        _embedder = TextEmbedding(model_name=EMBED_MODEL)
    return _embedder


def _embed_texts(texts: list[str]) -> list[list[float]]:
    return [vector.tolist() for vector in _get_embedder().embed(texts)]


def _get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
    return _client


def get_collection():
    return _get_client().get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def collection_is_ready() -> bool:
    if not CHROMA_DIR.exists():
        return False
    try:
        collection = get_collection()
        return collection.count() > 0
    except Exception:
        return False


def reset_collection() -> None:
    global _client
    if _client is not None:
        try:
            _client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
    _client = None
    get_collection()


def index_chunks(chunks: list[dict]) -> int:
    """Upsert all chunks into Chroma. Returns number indexed."""
    if not chunks:
        return 0

    reset_collection()
    collection = get_collection()

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict] = []

    for chunk in chunks:
        source = chunk["source"]
        index = chunk["chunk_index"]
        chunk_id = f"{source}:{index}"
        ids.append(chunk_id)
        documents.append(chunk["text"])
        metadatas.append({
            "source": source,
            "chunk_index": index,
            "topic": _topic_for_source(source),
        })

    embeddings = _embed_texts(documents)
    batch_size = 64
    for start in range(0, len(ids), batch_size):
        end = start + batch_size
        collection.add(
            ids=ids[start:end],
            documents=documents[start:end],
            metadatas=metadatas[start:end],
            embeddings=embeddings[start:end],
        )

    return len(ids)


def _topic_for_source(source: str) -> str:
    name = source.lower()
    if "assignment" in name or name.startswith("d01") or name.startswith("d02"):
        return "assignments"
    if "theory" in name or "cultural" in name or name.startswith("d10"):
        return "cultural_theory"
    if "adoption" in name or name.startswith("d11"):
        return "it_adoption"
    if "virtual" in name or "influencer" in name or name.startswith("d12"):
        return "virtual_influencers"
    if "persona" in name or name.startswith("d09"):
        return "persona"
    if "chapter" in name or name.startswith("d0"):
        return "course_content"
    return "general"


def vector_search(query: str, top_k: int = 10) -> list[dict]:
    """Return chunks sorted by relevance (highest score first)."""
    if not collection_is_ready():
        from ingest import main as ingest_main
        ingest_main()

    collection = get_collection()
    query_embedding = _embed_texts([query])[0]
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, max(collection.count(), 1)),
        include=["documents", "metadatas", "distances"],
    )

    chunks: list[dict] = []
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for text, meta, distance in zip(documents, metadatas, distances):
        if not text or not meta:
            continue
        # Chroma cosine distance: 0 = identical, 2 = opposite. Convert to similarity.
        similarity = 1.0 - (distance / 2.0)
        chunks.append({
            "text": text,
            "source": meta.get("source", ""),
            "chunk_index": meta.get("chunk_index", 0),
            "score": similarity,
        })

    chunks.sort(key=lambda c: c["score"], reverse=True)
    return chunks
