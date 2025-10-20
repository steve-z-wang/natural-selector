"""Utility functions for embedding elements."""

from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .page_index import ElementData

from ..interfaces import Embedder


def embed_elements(elements: List["ElementData"], embedder: Embedder) -> List["ElementData"]:
    """
    Add embeddings to elements in-place.

    Args:
        elements: List of ElementData objects (modified in-place)
        embedder: Embedder instance (e.g., SentenceTransformerEmbedder, OpenAIEmbedder)

    Returns:
        Same list of elements with embeddings added

    Example:
        >>> from natural_selector.integrations import SentenceTransformerEmbedder
        >>> embedder = SentenceTransformerEmbedder()
        >>> elements = embed_elements(elements, embedder)
    """
    # Extract text representations
    texts = [element.text_repr for element in elements]

    # Generate embeddings
    embeddings = embedder.embed(texts)

    # Add embeddings to elements
    for element, embedding in zip(elements, embeddings):
        element.embedding = embedding

    return elements
