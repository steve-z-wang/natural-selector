"""Utility functions for embedding chunks."""

from typing import List
from ...interfaces import Embedder
from .chunker import Chunk


def embed_chunks(chunks: List[Chunk], embedder: Embedder) -> List[Chunk]:
    """
    Add embeddings to chunks in-place.

    Args:
        chunks: List of Chunk objects (modified in-place)
        embedder: Embedder instance (e.g., SentenceTransformerEmbedder, OpenAIEmbedder)

    Returns:
        Same list of chunks with embeddings added

    Example:
        >>> from natural_selector.integrations import SentenceTransformerEmbedder
        >>> embedder = SentenceTransformerEmbedder()
        >>> chunks = embed_chunks(chunks, embedder)
    """
    # Extract markdown texts
    texts = [chunk.markdown for chunk in chunks]

    # Generate embeddings
    embeddings = embedder.embed(texts)

    # Add embeddings to chunks
    for chunk, embedding in zip(chunks, embeddings):
        chunk.embedding = embedding

    return chunks
