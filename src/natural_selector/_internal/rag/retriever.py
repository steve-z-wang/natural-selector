"""Retrieve relevant chunks based on natural language queries."""

from typing import List, Dict, Tuple
import numpy as np
from .embedder import Embedder


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


class ChunkRetriever:
    """Retrieve relevant chunks based on semantic similarity."""

    def __init__(self, embedded_chunks: List[Dict], embedder: Embedder):
        """
        Initialize retriever with embedded chunks.

        Args:
            embedded_chunks: List of chunks with 'embedding' field
            embedder: Embedder instance for query embedding
        """
        self.chunks = embedded_chunks
        self.embedder = embedder

        # Pre-compute embeddings matrix for efficient search
        self.embeddings = np.array([chunk['embedding'] for chunk in embedded_chunks])

    def query(self, query_text: str, top_k: int = 3) -> List[Tuple[Dict, float]]:
        """
        Find top k most relevant chunks for a query.

        Args:
            query_text: Natural language query
            top_k: Number of top results to return

        Returns:
            List of (chunk, similarity_score) tuples, sorted by score (highest first)
        """
        # Embed the query
        query_embedding = np.array(self.embedder.embed_single(query_text))

        # Compute similarities with all chunks
        similarities = []
        for i, chunk_embedding in enumerate(self.embeddings):
            score = cosine_similarity(query_embedding, chunk_embedding)
            similarities.append((i, score))

        # Sort by similarity (highest first)
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Get top k chunks with scores
        results = []
        for i, score in similarities[:top_k]:
            chunk = self.chunks[i]
            results.append((chunk, float(score)))

        return results

    def query_with_threshold(
        self,
        query_text: str,
        threshold: float = 0.5,
        top_k: int = 10
    ) -> List[Tuple[Dict, float]]:
        """
        Find chunks above similarity threshold.

        Args:
            query_text: Natural language query
            threshold: Minimum similarity score (0-1)
            top_k: Maximum number of results

        Returns:
            List of (chunk, similarity_score) tuples above threshold
        """
        results = self.query(query_text, top_k=top_k)
        return [(chunk, score) for chunk, score in results if score >= threshold]


def format_results(results: List[Tuple[Dict, float]], show_full: bool = False) -> str:
    """
    Format query results for display.

    Args:
        results: List of (chunk, score) tuples
        show_full: Show full markdown or just preview

    Returns:
        Formatted string
    """
    lines = []
    for i, (chunk, score) in enumerate(results):
        lines.append(f"\n{'='*60}")
        lines.append(f"Result {i+1} | Similarity: {score:.4f}")
        lines.append(f"{'='*60}")
        lines.append(f"Tokens: {chunk['tokens']} | Items: {chunk['item_count']}")

        if show_full:
            lines.append(f"\n{chunk['markdown']}")
        else:
            # Show first 200 chars
            preview = chunk['markdown'][:200]
            if len(chunk['markdown']) > 200:
                preview += "..."
            lines.append(f"\n{preview}")

    return "\n".join(lines)
