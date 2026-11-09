"""The only module that talks to Chroma: build, open, read one document whole, and search."""
import os
import shutil

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from config import config


def _embedding_function():
    return SentenceTransformerEmbeddingFunction(model_name=config.EMBEDDING_MODEL_NAME, device=config.EMBEDDING_DEVICE)


def build_vector_index(chunk_records, store_path, collection_name):
    """Rebuild the store from nothing and add every passage in one call."""
    if os.path.exists(store_path):
        shutil.rmtree(store_path)
    with chromadb.PersistentClient(path=store_path) as client:
        collection = client.create_collection(name=collection_name, embedding_function=_embedding_function(),
                                              configuration={"hnsw": {"space": "cosine"}})
        collection.add(ids=[r["chunk_id"] for r in chunk_records],
                       documents=[r["chunk_text"] for r in chunk_records],
                       metadatas=[{"document_name": r["document_name"]} for r in chunk_records])
        return collection.count()


def open_vector_index(store_path, collection_name):
    """Open the store indexing built; a missing store or collection is Chroma's error, never an empty store."""
    client = chromadb.PersistentClient(path=store_path)
    return client.get_collection(name=collection_name, embedding_function=_embedding_function())


def read_document_chunks(collection, document_name):
    """Every passage of one document, with no similarity ranking."""
    result = collection.get(where={"document_name": {"$eq": document_name}})
    documents = result.get("documents") or []
    if not documents:
        raise ValueError(f"the index holds no chunks of {document_name}")
    return list(documents)


def search_document(collection, question, document_name, result_count):
    """The passages of one document closest in meaning to one question, closest first."""
    result = collection.query(query_texts=[question], n_results=result_count,
                              where={"document_name": {"$eq": document_name}})
    documents = (result.get("documents") or [[]])[0]
    if not documents:
        raise ValueError(f"the index holds no chunks of {document_name}")
    return list(documents)


def search_documents(collection, query_texts, result_count, document_filter):
    """One result list per question, each passage with its id, text, document and cosine distance."""
    result = collection.query(query_texts=list(query_texts), n_results=result_count,
                              where={"document_name": document_filter})
    found = []
    for ids, texts, metadatas, distances in zip(result["ids"], result["documents"], result["metadatas"],
                                                result["distances"]):
        found.append([{"chunk_id": chunk_id, "chunk_text": text, "document_name": metadata["document_name"],
                       "distance": float(distance)}
                      for chunk_id, text, metadata, distance in zip(ids, texts, metadatas, distances)])
    return found
