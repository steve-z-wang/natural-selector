"""Retrieve relevant elements based on natural language queries."""

from typing import List, Tuple, TYPE_CHECKING
import numpy as np

if TYPE_CHECKING:
    from .page_index import ElementData

from ..interfaces import Embedder


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


def search_elements(
    query_text: str,
    elements: List["ElementData"],
    embedder: Embedder,
    top_k: int = 3
) -> List[Tuple["ElementData", float]]:
    """
    Find top k most relevant elements for a query.

    Args:
        query_text: Natural language query
        elements: List of ElementData objects with embeddings
        embedder: Embedder instance for query embedding
        top_k: Number of top results to return

    Returns:
        List of (element, similarity_score) tuples, sorted by score (highest first)
    """
    # Build embeddings matrix from elements
    # Explicit relationship: embeddings_matrix[i] = elements[i].embedding
    embeddings_matrix = np.array([element.embedding for element in elements])

    # Embed the query
    query_embedding = np.array(embedder.embed_single(query_text))

    # Compute similarities with all elements
    similarities = []
    for i, element_embedding in enumerate(embeddings_matrix):
        score = cosine_similarity(query_embedding, element_embedding)
        similarities.append((i, score))

    # Sort by similarity (highest first)
    similarities.sort(key=lambda x: x[1], reverse=True)

    # Get top k elements with scores
    results = []
    for i, score in similarities[:top_k]:
        element = elements[i]  # elements[i] maps to embeddings_matrix[i]
        results.append((element, float(score)))

    return results


def format_results(results: List[Tuple["ElementData", float]], show_full: bool = False) -> str:
    """
    Format query results for display.

    Args:
        results: List of (ElementData, score) tuples
        show_full: Show full text representation or just preview

    Returns:
        Formatted string
    """
    lines = []
    for i, (element, score) in enumerate(results):
        lines.append(f"\n{'='*60}")
        lines.append(f"Result {i+1} | Similarity: {score:.4f}")
        lines.append(f"{'='*60}")
        lines.append(f"Element ID: {element.element_id}")

        if show_full:
            lines.append(f"\n{element.text_repr}")
        else:
            # Show first 200 chars
            preview = element.text_repr[:200]
            if len(element.text_repr) > 200:
                preview += "..."
            lines.append(f"\n{preview}")

    return "\n".join(lines)
