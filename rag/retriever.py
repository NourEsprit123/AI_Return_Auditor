import re
from pathlib import Path
from collections import defaultdict

import chromadb
from rank_bm25 import BM25Okapi

from rag.documents import load_documents
from rag.embeddings import embed_query


PROJECT_DIR = Path(__file__).resolve().parent.parent
STORE_DIR = PROJECT_DIR / "data" / "vector_store"
COLLECTION_NAME = "return_policies"


def tokenize(text):
    """Tokenisation simple pour BM25."""
    return re.findall(r"\w+", text.lower(), flags=re.UNICODE)


class HybridRetriever:

    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=str(STORE_DIR)
        )

        try:
            self.collection = self.client.get_collection(
                COLLECTION_NAME
            )
        except Exception as exc:
            raise RuntimeError(
                "L'index RAG n'existe pas. "
                "Exécute d'abord : "
                "python -m rag.build_index"
            ) from exc

        if self.collection.count() == 0:
            raise RuntimeError(
                "L'index RAG est vide. "
                "Exécute : python -m rag.build_index"
            )

        # Les documents sont chargés pour construire l'index BM25.
        self.records = load_documents()
        self.tokenized_corpus = [
            tokenize(record["text"])
            for record in self.records
        ]

        self.bm25 = BM25Okapi(self.tokenized_corpus)

        self.records_by_id = {
            record["id"]: record
            for record in self.records
        }

    def retrieve(self, query, top_k=5, candidate_k=10):
        """Recherche sémantique + BM25 + fusion RRF."""

        query = query.strip()

        if not query:
            return []

        total = self.collection.count()
        candidate_k = min(candidate_k, total)

        # 1. Recherche sémantique
        query_vector = embed_query(query)

        semantic_result = self.collection.query(
            query_embeddings=[query_vector],
            n_results=candidate_k,
            include=[
                "documents",
                "metadatas",
                "distances",
            ],
        )

        semantic_ids = semantic_result["ids"][0]
        semantic_docs = semantic_result["documents"][0]
        semantic_meta = semantic_result["metadatas"][0]
        semantic_distances = semantic_result["distances"][0]

        candidates = {}

        for rank, doc_id in enumerate(semantic_ids, start=1):
            distance = semantic_distances[rank - 1]

            candidates[doc_id] = {
                "id": doc_id,
                "text": semantic_docs[rank - 1],
                "source": semantic_meta[rank - 1].get(
                    "source", "Source inconnue"
                ),
                "page": semantic_meta[rank - 1].get("page", 0),
                "semantic_score": max(0.0, 1.0 - distance),
                "bm25_score": 0.0,
                "rrf_score": 0.0,
            }

        # 2. Recherche lexicale BM25
        query_tokens = tokenize(query)
        bm25_scores = self.bm25.get_scores(query_tokens)

        lexical_ranking = sorted(
            range(len(self.records)),
            key=lambda index: bm25_scores[index],
            reverse=True,
        )[:candidate_k]

        lexical_ids = []

        for index in lexical_ranking:
            record = self.records[index]
            doc_id = record["id"]
            score = float(bm25_scores[index])

            lexical_ids.append(doc_id)

            if doc_id not in candidates:
                candidates[doc_id] = {
                    "id": doc_id,
                    "text": record["text"],
                    "source": record["metadata"]["source"],
                    "page": record["metadata"]["page"],
                    "semantic_score": 0.0,
                    "bm25_score": score,
                    "rrf_score": 0.0,
                }
            else:
                candidates[doc_id]["bm25_score"] = score

        # 3. Fusion Reciprocal Rank Fusion
        rrf_k = 60

        for rank, doc_id in enumerate(semantic_ids, start=1):
            candidates[doc_id]["rrf_score"] += (
                1.0 / (rrf_k + rank)
            )

        for rank, doc_id in enumerate(lexical_ids, start=1):
            candidates[doc_id]["rrf_score"] += (
                1.0 / (rrf_k + rank)
            )

        # 4. Classement final
        ranked = sorted(
            candidates.values(),
            key=lambda item: item["rrf_score"],
            reverse=True,
        )

        return ranked[:top_k]