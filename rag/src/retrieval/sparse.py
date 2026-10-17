import re
import numpy as np
from rank_bm25 import BM25Okapi
from nltk.stem import PorterStemmer  # or snowballstemmer for other languages



"""
BM25Okapi(corpus, k1=1.5, b=0.75, epsilon=0.25)
k1 (default 1.5) controls term-frequency saturation. 
    A higher value means repeated mentions of a term keep adding to the score. 
    A lower value means the first mention counts most and repeats add little. 
    The typical range is 1.2 to 2.0. For short policy chunks where a product type is mentioned once or twice, this rarely matters much.
b (default 0.75) controls length normalization. At b=1, long chunks are penalized fully. At b=0, length is ignored. 
    If your chunks are roughly uniform in size, b has little effect. If lengths vary a lot, a long policy chunk that contains your product type can get pushed down, 
    so try a lower b (0.3 to 0.5).
epsilon (default 0.25) is the one most relevant to your corpus. In rank_bm25, a term appearing in more than half of the chunks gets a negative IDF, 
    and the library replaces that with epsilon times the average IDF. In a small, repetitive corpus like policy documents, 
    words such as “policy”, “return”, “customer”, or even a common product category can hit this floor and contribute almost nothing. If your literal product type appears in many chunks, this can partly explain the weak signal. Checking this is easy: count how many chunks contain the term.
"""




from rag.src.embeddings import chunk_ids, texts

_stemmer = PorterStemmer()
_STOPWORDS = {"the", "a", "an", "is", "are", "of", "for", "to", "and", "in", "on", "what", "how"}

def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"\w+", text.lower())
    return [_stemmer.stem(t) for t in tokens if t not in _STOPWORDS]


bm25 = BM25Okapi([tokenize(t) for t in texts])

def sparse_search(query: str, top_k: int = 10):
    tokens = tokenize(query)
    if not tokens:
        return []
    scores = bm25.get_scores(tokens)
    top_indices = np.argsort(scores)[::-1][:top_k]
    return [
        {"chunk_id": chunk_ids[i], "score": float(scores[i]), "text": texts[i]}
        for i in top_indices if scores[i] > 0
    ]