"""Sentence Transformer Embedder integration."""

from typing import List
from ..interfaces import Embedder


class SentenceTransformerEmbedder(Embedder):
    """Local embeddings using Sentence Transformers (free, runs locally)."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize Sentence Transformer embedder.

        Args:
            model_name: Sentence Transformer model name (default: all-MiniLM-L6-v2)

        Example:
            >>> embedder = SentenceTransformerEmbedder()
            >>> embeddings = embedder.embed(["hello world", "goodbye"])
        """
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "Sentence Transformers not installed. Run: pip install sentence-transformers"
            )

        self.model = SentenceTransformer(model_name)
        self.model_name = model_name

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Sentence Transformers."""
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    def embed_single(self, text: str) -> List[float]:
        """Generate single embedding using Sentence Transformers."""
        embedding = self.model.encode([text], convert_to_numpy=True)
        return embedding[0].tolist()
