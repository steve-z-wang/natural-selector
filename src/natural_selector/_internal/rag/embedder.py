"""Generate embeddings for markdown chunks."""

from typing import List, Dict, Optional, Literal
from abc import ABC, abstractmethod
import numpy as np


class Embedder(ABC):
    """Base class for embedding models."""

    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        pass

    @abstractmethod
    def embed_single(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text string to embed

        Returns:
            Embedding vector
        """
        pass


class OpenAIEmbedder(Embedder):
    """OpenAI embeddings using their API."""

    def __init__(self, model: str = "text-embedding-3-small", api_key: Optional[str] = None):
        """
        Initialize OpenAI embedder.

        Args:
            model: OpenAI embedding model name
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("OpenAI package not installed. Run: pip install openai")

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI API."""
        response = self.client.embeddings.create(
            input=texts,
            model=self.model
        )
        return [item.embedding for item in response.data]

    def embed_single(self, text: str) -> List[float]:
        """Generate single embedding using OpenAI API."""
        return self.embed([text])[0]


class SentenceTransformerEmbedder(Embedder):
    """Local embeddings using Sentence Transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize Sentence Transformer embedder.

        Args:
            model_name: Sentence Transformer model name
        """
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError("Sentence Transformers not installed. Run: pip install sentence-transformers")

        self.model = SentenceTransformer(model_name)

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Sentence Transformers."""
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    def embed_single(self, text: str) -> List[float]:
        """Generate single embedding using Sentence Transformers."""
        embedding = self.model.encode([text], convert_to_numpy=True)
        return embedding[0].tolist()


def create_embedder(
    provider: Literal["openai", "sentence-transformers"] = "sentence-transformers",
    **kwargs
) -> Embedder:
    """
    Factory function to create an embedder.

    Args:
        provider: Embedding provider ("openai" or "sentence-transformers")
        **kwargs: Additional arguments for the embedder

    Returns:
        Embedder instance
    """
    if provider == "openai":
        return OpenAIEmbedder(**kwargs)
    elif provider == "sentence-transformers":
        return SentenceTransformerEmbedder(**kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def embed_chunks(
    chunks: List[Dict],
    embedder: Embedder
) -> List[Dict]:
    """
    Generate embeddings for chunks.

    Args:
        chunks: List of chunk dictionaries with 'markdown' field
        embedder: Embedder instance

    Returns:
        List of chunks with added 'embedding' field
    """
    # Extract markdown texts
    texts = [chunk['markdown'] for chunk in chunks]

    # Generate embeddings
    embeddings = embedder.embed(texts)

    # Add embeddings to chunks
    embedded_chunks = []
    for chunk, embedding in zip(chunks, embeddings):
        chunk_with_embedding = chunk.copy()
        chunk_with_embedding['embedding'] = embedding
        chunk_with_embedding['embedding_dim'] = len(embedding)
        embedded_chunks.append(chunk_with_embedding)

    return embedded_chunks
