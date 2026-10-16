import chromadb

from rag.documents import load_documents
from rag.embeddings import embed_texts


PROJECT_DIR = __import__("pathlib").Path(__file__).resolve().parent.parent
STORE_DIR = PROJECT_DIR / "data" / "vector_store"
COLLECTION_NAME = "return_policies"


def build_index():
    records = load_documents()

    client = chromadb.PersistentClient(
        path=str(STORE_DIR)
    )

    # Reconstruire l'index évite de conserver des versions obsolètes.
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    batch_size = 64

    for start in range(0, len(records), batch_size):
        batch = records[start:start + batch_size]

        texts = [record["text"] for record in batch]
        embeddings = embed_texts(texts)

        collection.add(
            ids=[record["id"] for record in batch],
            documents=texts,
            metadatas=[
                record["metadata"] for record in batch
            ],
            embeddings=embeddings,
        )

    print(f"Index créé : {collection.count()} passages")
    print(f"Emplacement : {STORE_DIR}")


if __name__ == "__main__":
    build_index()