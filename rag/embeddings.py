"""
rag/embeddings.py
-----------------
Embedding model wrapper for the RAG pipeline.

Model: sentence-transformers/all-MiniLM-L6-v2
  - 384 dimensions
  - Free, runs fully offline
  - No API key required
  - Fast inference, lightweight
  - Good quality for short policy paragraphs

The embedding model is loaded once and reused across calls to avoid
repeated initialisation overhead.
"""

import os

# Force PyTorch backend — prevents sentence-transformers from trying
# to import TensorFlow, which may be blocked by system policies.
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")

from typing import Optional

from sentence_transformers import SentenceTransformer


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Normalize embeddings so cosine similarity == dot product.
# Recommended for retrieval use cases.
NORMALIZE_EMBEDDINGS = True


# ============================================================
# EMBEDDING MODEL WRAPPER
# ============================================================

class EmbeddingModel:
    """
    Thin wrapper around SentenceTransformer.

    Provides a consistent interface for embedding text and lists of texts.
    The model is loaded lazily on first use and cached for reuse.
    """

    _instance: Optional["EmbeddingModel"] = None
    _model: Optional[SentenceTransformer] = None

    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL):

        self.model_name = model_name
        self._model = SentenceTransformer(model_name)

        print(
            f"[Embeddings] Model loaded: {model_name} "
            f"({self._model.get_sentence_embedding_dimension()} dims)"
        )

    # --------------------------------------------------------
    # EMBED SINGLE TEXT
    # --------------------------------------------------------

    def embed(self, text: str) -> list[float]:
        """
        Embed a single text string.

        Parameters
        ----------
        text : The text to embed.

        Returns
        -------
        List of floats (embedding vector).
        """

        vector = self._model.encode(
            text,
            normalize_embeddings=NORMALIZE_EMBEDDINGS,
            show_progress_bar=False,
        )

        return vector.tolist()

    # --------------------------------------------------------
    # EMBED BATCH
    # --------------------------------------------------------

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a list of texts efficiently in a single batch call.

        Parameters
        ----------
        texts : List of strings to embed.

        Returns
        -------
        List of embedding vectors.
        """

        vectors = self._model.encode(
            texts,
            normalize_embeddings=NORMALIZE_EMBEDDINGS,
            show_progress_bar=False,
            batch_size=32,
        )

        return [v.tolist() for v in vectors]

    # --------------------------------------------------------
    # DIMENSION
    # --------------------------------------------------------

    @property
    def dimension(self) -> int:
        return self._model.get_sentence_embedding_dimension()


# ============================================================
# SINGLETON FACTORY
# ============================================================

_embedding_model_instance: Optional[EmbeddingModel] = None


def get_embedding_model(
    model_name: str = DEFAULT_EMBEDDING_MODEL,
) -> EmbeddingModel:
    """
    Return the shared EmbeddingModel instance.

    Creates it on first call. Subsequent calls return the cached instance.
    This avoids reloading the model weights on every retrieval request.
    """

    global _embedding_model_instance

    if _embedding_model_instance is None:
        _embedding_model_instance = EmbeddingModel(model_name)

    return _embedding_model_instance
