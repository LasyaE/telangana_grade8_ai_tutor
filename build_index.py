"""Build a local Chroma vector index from the prepared textbook corpus."""
import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from config import (
    CHROMA_PATH, COLLECTION_NAME, CORPUS_PATH, EMBEDDING_MODEL
)

def main():
    corpus_path = Path(CORPUS_PATH)
    if not corpus_path.exists():
        raise FileNotFoundError(f"Corpus not found: {corpus_path}")

    rows = [
        json.loads(line)
        for line in corpus_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows:
        raise ValueError("The corpus is empty.")

    print(f"Loading embedding model: {EMBEDDING_MODEL}")
    embedder = SentenceTransformer(EMBEDDING_MODEL)
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    # Rebuild cleanly so rerunning this script does not create duplicate records.
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    batch_size = 64
    for start in range(0, len(rows), batch_size):
        batch = rows[start:start + batch_size]
        texts = [r["text"] for r in batch]
        vectors = embedder.encode(
            texts, normalize_embeddings=True, show_progress_bar=False
        ).tolist()
        ids = [r["id"] for r in batch]
        metadatas = [{
            "subject": r["subject"],
            "grade": int(r["grade"]),
            "curriculum": r["curriculum"],
            "source_file": r["source_file"],
            "page": int(r["page"]),
            "chunk_index": int(r["chunk_index"])
        } for r in batch]

        collection.add(
            ids=ids,
            documents=texts,
            embeddings=vectors,
            metadatas=metadatas
        )
        print(f"Indexed {min(start + batch_size, len(rows))}/{len(rows)}")

    print(f"Done. Chunks indexed: {collection.count()}")
    print(f"Database saved at: {CHROMA_PATH}")

if __name__ == "__main__":
    main()
