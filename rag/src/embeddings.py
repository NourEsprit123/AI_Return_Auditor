from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

import chromadb
import numpy as np

if TYPE_CHECKING:
    from FlagEmbedding import BGEM3FlagModel


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = BASE_DIR / "data" / "knowledge_base" / "processed" / "PDFoutput2.json"
VECTOR_DB_PATH = BASE_DIR / ".chroma"
COLLECTION_NAME = "policy_chunks_bge_m3"

with DATA_PATH.open("r", encoding="utf-8") as f:
    chunkedJSON = json.load(f)

texts = [chunk["text"] for chunk in chunkedJSON]
chunk_ids = [chunk["chunk_id"] for chunk in chunkedJSON]


@lru_cache(maxsize=1)
def get_embedding_model() -> BGEM3FlagModel:
    from FlagEmbedding import BGEM3FlagModel

    return BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)


@lru_cache(maxsize=1)
def get_vector_collection():
    client = chromadb.PersistentClient(path=str(VECTOR_DB_PATH))
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    stored = collection.get(include=["documents"])
    stored_documents = dict(zip(stored["ids"], stored["documents"] or []))
    current_ids = set(chunk_ids)
    stale_ids = [chunk_id for chunk_id in stored["ids"] if chunk_id not in current_ids]
    if stale_ids:
        collection.delete(ids=stale_ids)

    chunks_to_embed = [
        chunk
        for chunk in chunkedJSON
        if stored_documents.get(chunk["chunk_id"]) != chunk["text"]
    ]
    if chunks_to_embed:
        chunk_embeddings = get_embedding_model().encode(
            [chunk["text"] for chunk in chunks_to_embed],
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
        )["dense_vecs"]
        collection.upsert(
            ids=[chunk["chunk_id"] for chunk in chunks_to_embed],
            documents=[chunk["text"] for chunk in chunks_to_embed],
            metadatas=[{"title": chunk.get("title", "")} for chunk in chunks_to_embed],
            embeddings=np.asarray(chunk_embeddings, dtype=np.float32).tolist(),
        )

    return collection
