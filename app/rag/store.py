from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer
from app.config import settings

_model = None
_collection = None

def _get():
    global _model, _collection
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    if _collection is None:
        Path(settings.chroma_path).mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=settings.chroma_path)
        _collection = client.get_or_create_collection("it_knowledge")
    return _model, _collection

def add_documents(docs):
    model, col = _get()
    texts = [d["text"] for d in docs]
    embeddings = model.encode(texts).tolist()
    ids = [d["id"] for d in docs]
    metas = [{"source": d["source"], "title": d["title"]} for d in docs]
    col.upsert(ids=ids, documents=texts, embeddings=embeddings, metadatas=metas)

def search(query, k=5):
    model, col = _get()
    emb = model.encode([query]).tolist()
    if col.count() == 0:
        return []
    r = col.query(query_embeddings=emb, n_results=min(k, col.count()))
    return [
        {"text": doc, "source": meta.get("source",""), "title": meta.get("title","")}
        for doc, meta in zip(r["documents"][0], r["metadatas"][0])
    ]
