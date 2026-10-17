from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from FlagEmbedding import BGEM3FlagModel


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = BASE_DIR / "data" / "knowledge_base" / "processed" / "PDFoutput2.json"

with DATA_PATH.open("r", encoding="utf-8") as f:
    chunkedJSON = json.load(f)

texts = [chunk["text"] for chunk in chunkedJSON]
chunk_ids = [chunk["chunk_id"] for chunk in chunkedJSON]


@lru_cache(maxsize=1)
def get_embedding_model() -> BGEM3FlagModel:
    from FlagEmbedding import BGEM3FlagModel

    return BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)


@lru_cache(maxsize=1)
def get_embeddings() -> np.ndarray:
    output = get_embedding_model().encode(
        texts,
        return_dense=True,
        return_sparse=False,
        return_colbert_vecs=False,
    )
    return np.asarray(output["dense_vecs"], dtype=np.float32)
