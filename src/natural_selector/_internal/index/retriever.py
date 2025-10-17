"""Retrieve relevant chunks based on natural language queries."""

from typing import List, Tuple
import numpy as np
from ...interfaces import Embedder
from .chunker import Chunk


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Compute cosine similarity between two vectors.

    Args:
        a: First vector
        b: Second vector

    Returns:
        Cosine similarity score (0-1)
    """
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def search_chunks(
    query_text: str,
    chunks: List[Chunk],
    embedder: Embedder,
    top_k: int = 3
) -> List[Tuple[Chunk, float]]:
    """
    Find top k most relevant chunks for a query.

    Args:
        query_text: Natural language query
        chunks: List of Chunk objects with embeddings
        embedder: Embedder instance for query embedding
        top_k: Number of top results to return

    Returns:
        List of (chunk, similarity_score) tuples, sorted by score (highest first)
    """
    # Build embeddings matrix from chunks
    # Explicit relationship: embeddings_matrix[i] = chunks[i].embedding
    embeddings_matrix = np.array([chunk.embedding for chunk in chunks])

    # Embed the query
    query_embedding = np.array(embedder.embed_single(query_text))

    # Compute similarities with all chunks
    similarities = []
    for i, chunk_embedding in enumerate(embeddings_matrix):
        score = cosine_similarity(query_embedding, chunk_embedding)
        similarities.append((i, score))

    # Sort by similarity (highest first)
    similarities.sort(key=lambda x: x[1], reverse=True)

    # Get top k chunks with scores
    results = []
    for i, score in similarities[:top_k]:
        chunk = chunks[i]  # chunks[i] maps to embeddings_matrix[i]
        results.append((chunk, float(score)))

    return results


def format_results(results: List[Tuple[Chunk, float]], show_full: bool = False) -> str:
    """
    Format query results for display.

    Args:
        results: List of (Chunk, score) tuples
        show_full: Show full markdown or just preview

    Returns:
        Formatted string
    """
    lines = []
    for i, (chunk, score) in enumerate(results):
        lines.append(f"\n{'='*60}")
        lines.append(f"Result {i+1} | Similarity: {score:.4f}")
        lines.append(f"{'='*60}")
        lines.append(f"Tokens: {chunk.tokens}")

        if show_full:
            lines.append(f"\n{chunk.markdown}")
        else:
            # Show first 200 chars
            preview = chunk.markdown[:200]
            if len(chunk.markdown) > 200:
                preview += "..."
            lines.append(f"\n{preview}")

    return "\n".join(lines)
