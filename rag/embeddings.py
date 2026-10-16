from functools import lru_cache
from sentence_transformers import SentenceTransformer


MODEL_NAME = (
    "sentence-transformers/"
    "paraphrase-multilingual-MiniLM-L12-v2"
)


@lru_cache(maxsize=1)
def get_embedding_model():
    """Charge le modèle une seule fois par processus."""
    return SentenceTransformer(MODEL_NAME)


def embed_texts(texts):
    """Transforme une liste de textes en vecteurs."""
    model = get_embedding_model()

    vectors = model.encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )

    return vectors.tolist()


def embed_query(query):
    """Transforme une question en vecteur."""
    return embed_texts([query])[0]