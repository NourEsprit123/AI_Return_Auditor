"""
rag/retriever.py
----------------
Vector store (ChromaDB) + Modular RAG retrieval pipeline.

Pipeline (Modular RAG):
  1. Query Rewriting  — prompt-engineered query from VisionAnalysis fields
  2. Dense Retrieval  — bi-encoder (all-MiniLM-L6-v2) + ChromaDB cosine search
  3. Reranking        — cross-encoder reranks Top-5 → Top-3
  4. Compression      — extract only policy-relevant sentences per chunk

This file is responsible for:
  - Building and persisting the ChromaDB vector store from DocumentChunks
  - Executing the 4-module retrieval pipeline at query time
  - Returning a PolicyResult consumed by Agent 3
"""

import os

# Force PyTorch backend before any sentence-transformers import
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings

from rag.documents import DocumentChunk, load_documents
from rag.embeddings import EmbeddingModel, get_embedding_model


# ============================================================
# CONFIGURATION
# ============================================================

CHROMA_PERSIST_DIR = (
    Path(__file__).resolve().parent.parent / "data" / "chroma_db"
)

COLLECTION_NAME = "policy_knowledge_base"

# Module 2 — Dense retrieval: how many candidates to fetch before reranking
TOP_K_RETRIEVAL = 5

# Module 3 — Reranking: how many final chunks to keep after reranking
TOP_K_FINAL = 3

# Reranker model — cross-encoder for accurate pairwise relevance scoring
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


# ============================================================
# POLICY RESULT
# ============================================================

@dataclass
class RetrievedChunk:
    """A single retrieved and scored policy chunk."""

    text: str
    source: str
    doc_type: str
    chunk_id: int
    relevance_score: float


@dataclass
class PolicyResult:
    """
    Structured output of the RAG Agent.
    Consumed by Agent 3 (Decision Agent).
    """

    query: str                              # The rewritten search query
    chunks: list[RetrievedChunk]            # Top-K reranked chunks
    sources: list[str]                      # Unique source filenames
    summary: str = ""                       # LLM-synthesized policy summary
    applicable_policy: str = ""             # Which policy applies
    retrieval_successful: bool = True
    error: str = ""


# ============================================================
# VECTOR STORE
# ============================================================

class PolicyVectorStore:
    """
    ChromaDB-backed vector store for policy document chunks.

    Responsibilities:
    - Build the collection from DocumentChunks (once, then persisted)
    - Query the collection with an embedded query vector
    - Return top-K candidate chunks for the reranker
    """

    def __init__(
        self,
        embedding_model: Optional[EmbeddingModel] = None,
        persist_dir: Optional[Path] = None,
        collection_name: str = COLLECTION_NAME,
    ):

        self.embedding_model = embedding_model or get_embedding_model()
        self.persist_dir = persist_dir or CHROMA_PERSIST_DIR
        self.collection_name = collection_name

        # Ensure persistence directory exists
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False),
        )

        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        print(
            f"[VectorStore] Collection '{self.collection_name}' "
            f"loaded. Documents: {self.collection.count()}"
        )

    # --------------------------------------------------------
    # BUILD INDEX
    # --------------------------------------------------------

    def build(self, chunks: list[DocumentChunk]) -> None:
        """
        Embed all document chunks and add them to the ChromaDB collection.

        Skips chunks that are already indexed (idempotent).
        Call this once during setup or whenever the knowledge base changes.
        """

        existing_ids = set(
            self.collection.get()["ids"]
        )

        new_chunks = [
            c for c in chunks
            if self._chunk_id(c) not in existing_ids
        ]

        if not new_chunks:
            print("[VectorStore] All chunks already indexed. Skipping build.")
            return

        texts = [c.text for c in new_chunks]
        ids = [self._chunk_id(c) for c in new_chunks]
        metadatas = [
            {
                "source":   c.source,
                "doc_type": c.doc_type,
                "chunk_id": c.chunk_id,
            }
            for c in new_chunks
        ]

        print(
            f"[VectorStore] Embedding {len(new_chunks)} new chunks..."
        )

        embeddings = self.embedding_model.embed_batch(texts)

        self.collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        print(
            f"[VectorStore] Indexed {len(new_chunks)} chunks. "
            f"Total: {self.collection.count()}"
        )

    # --------------------------------------------------------
    # QUERY
    # --------------------------------------------------------

    def query(
        self,
        query_text: str,
        top_k: int = TOP_K_RETRIEVAL,
    ) -> list[RetrievedChunk]:
        """
        Embed the query and retrieve the top-K most similar chunks
        using cosine similarity.

        Parameters
        ----------
        query_text : The search query (rewritten by Module 1).
        top_k      : Number of candidate chunks to retrieve.

        Returns
        -------
        List of RetrievedChunk ordered by cosine similarity (descending).
        """

        query_embedding = self.embedding_model.embed(query_text)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self.collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        chunks: list[RetrievedChunk] = []

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for doc, meta, dist in zip(documents, metadatas, distances):

            # ChromaDB cosine distance: 0 = identical, 2 = opposite.
            # Convert to similarity score in [0, 1].
            similarity = 1.0 - (dist / 2.0)

            chunks.append(
                RetrievedChunk(
                    text=doc,
                    source=meta.get("source", "unknown"),
                    doc_type=meta.get("doc_type", "Policy"),
                    chunk_id=int(meta.get("chunk_id", 0)),
                    relevance_score=round(similarity, 4),
                )
            )

        return chunks

    # --------------------------------------------------------
    # RESET
    # --------------------------------------------------------

    def reset(self) -> None:
        """Delete and recreate the collection. Used for testing."""

        self.client.delete_collection(self.collection_name)

        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        print("[VectorStore] Collection reset.")

    # --------------------------------------------------------
    # HELPERS
    # --------------------------------------------------------

    @staticmethod
    def _chunk_id(chunk: DocumentChunk) -> str:
        return f"{chunk.source}__chunk_{chunk.chunk_id}"


# ============================================================
# MODULE 3 — RERANKER
# ============================================================

class Reranker:
    """
    Cross-encoder reranker (Module 3).

    Scores each (query, chunk) pair jointly — more accurate than
    the cosine similarity used in Module 2, but too slow to run on
    the full knowledge base. Applied only to the Top-K shortlist
    from Module 2.
    """

    def __init__(self, model_name: str = RERANKER_MODEL):

        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(model_name)
            self.available = True
            print(f"[Reranker] Cross-encoder loaded: {model_name}")

        except Exception as exc:
            print(
                f"[Reranker] Cross-encoder unavailable ({exc}). "
                "Falling back to cosine similarity ranking."
            )
            self.model = None
            self.available = False

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int = TOP_K_FINAL,
    ) -> list[RetrievedChunk]:
        """
        Rerank chunks by cross-encoder relevance score.

        Parameters
        ----------
        query  : The search query.
        chunks : Candidate chunks from Module 2.
        top_k  : Number of chunks to return after reranking.

        Returns
        -------
        Top-K chunks sorted by cross-encoder score (descending).
        """

        if not self.available or not chunks:
            # Fallback: return top_k by cosine similarity
            return sorted(
                chunks,
                key=lambda c: c.relevance_score,
                reverse=True,
            )[:top_k]

        pairs = [(query, chunk.text) for chunk in chunks]

        scores = self.model.predict(pairs)

        for chunk, score in zip(chunks, scores):
            chunk.relevance_score = round(float(score), 4)

        reranked = sorted(
            chunks,
            key=lambda c: c.relevance_score,
            reverse=True,
        )

        return reranked[:top_k]


# ============================================================
# MODULE 4 — CONTEXT COMPRESSION
# ============================================================

def compress_chunk(chunk: RetrievedChunk, query: str) -> RetrievedChunk:
    """
    Module 4 — Context Compression.

    Extract only the sentences from a chunk that are directly relevant
    to the query. Reduces noise injected into Agent 3's prompt.

    Uses a simple heuristic: keep sentences that share at least one
    significant token with the query. For short policy chunks (≤ 500 chars)
    this is sufficient without requiring an additional LLM call.
    """

    query_tokens = set(query.lower().split())

    # Remove very common words that add no signal
    stopwords = {
        "a", "an", "the", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "shall", "can",
        "to", "of", "in", "for", "on", "with", "at", "by", "from",
        "up", "about", "into", "through", "during", "before", "after",
        "above", "below", "between", "out", "off", "over", "under",
        "again", "then", "once", "and", "or", "but", "if", "because",
        "as", "until", "while", "that", "this", "these", "those",
        "it", "its", "not", "no", "nor", "so", "yet", "both", "each",
        "more", "most", "other", "some", "such", "than", "too", "very",
        "just", "also", "any", "all",
    }

    query_signal = query_tokens - stopwords

    sentences = [s.strip() for s in chunk.text.split(". ") if s.strip()]

    relevant = []

    for sentence in sentences:

        sentence_tokens = set(sentence.lower().split()) - stopwords

        overlap = query_signal & sentence_tokens

        if overlap:
            relevant.append(sentence)

    if relevant:
        compressed_text = ". ".join(relevant)
        if not compressed_text.endswith("."):
            compressed_text += "."
    else:
        # If no sentence matched, keep the full chunk
        compressed_text = chunk.text

    return RetrievedChunk(
        text=compressed_text,
        source=chunk.source,
        doc_type=chunk.doc_type,
        chunk_id=chunk.chunk_id,
        relevance_score=chunk.relevance_score,
    )


# ============================================================
# MODULAR RAG RETRIEVER
# ============================================================

class ModularRAGRetriever:
    """
    Full Modular RAG pipeline for policy retrieval.

    Modules:
      1. Query Rewriting  (handled by RAGAgent using LLM prompt)
      2. Dense Retrieval  (PolicyVectorStore.query)
      3. Reranking        (Reranker.rerank)
      4. Compression      (compress_chunk)

    The retriever handles Modules 2, 3, and 4.
    Module 1 (query rewriting) is executed by the RAGAgent
    before calling this retriever, because it requires the LLM.
    """

    def __init__(
        self,
        vector_store: Optional[PolicyVectorStore] = None,
        reranker: Optional[Reranker] = None,
    ):
        self.vector_store = vector_store or PolicyVectorStore()
        self.reranker = reranker or Reranker()

    # --------------------------------------------------------
    # ENSURE INDEX IS BUILT
    # --------------------------------------------------------

    def ensure_index(self) -> None:
        """
        Load documents and build the ChromaDB index if not already done.
        Safe to call multiple times — skips re-indexing if up to date.
        """

        if self.vector_store.collection.count() == 0:
            print("[Retriever] Index is empty. Building from knowledge base...")
            chunks = load_documents()
            self.vector_store.build(chunks)
        else:
            print(
                f"[Retriever] Index ready. "
                f"{self.vector_store.collection.count()} chunks."
            )

    # --------------------------------------------------------
    # RETRIEVE
    # --------------------------------------------------------

    def retrieve(
        self,
        query: str,
        top_k_retrieval: int = TOP_K_RETRIEVAL,
        top_k_final: int = TOP_K_FINAL,
        compress: bool = True,
    ) -> list[RetrievedChunk]:
        """
        Execute Modules 2, 3, and 4 of the Modular RAG pipeline.

        Parameters
        ----------
        query          : Rewritten query from Module 1 (RAGAgent).
        top_k_retrieval: Number of candidates from dense retrieval.
        top_k_final    : Number of chunks after reranking.
        compress       : Whether to apply context compression.

        Returns
        -------
        Top-K reranked and optionally compressed chunks.
        """

        # Module 2 — Dense Retrieval
        candidates = self.vector_store.query(query, top_k=top_k_retrieval)

        if not candidates:
            return []

        # Module 3 — Reranking
        reranked = self.reranker.rerank(
            query=query,
            chunks=candidates,
            top_k=top_k_final,
        )

        # Module 4 — Context Compression
        if compress:
            reranked = [
                compress_chunk(chunk, query)
                for chunk in reranked
            ]

        return reranked


# ============================================================
# SETUP HELPER
# ============================================================

def setup_retriever() -> ModularRAGRetriever:
    """
    Initialize and return a ready-to-use ModularRAGRetriever.

    Builds the ChromaDB index from the knowledge base if not yet done.
    """

    retriever = ModularRAGRetriever()
    retriever.ensure_index()

    return retriever
