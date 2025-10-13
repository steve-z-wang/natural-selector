"""OpenAI Embedder integration."""

import os
from typing import Optional, List

# Try to load .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from ..interfaces import Embedder


class OpenAIEmbedder(Embedder):
    """OpenAI embeddings using their API."""

    def __init__(self, model: str = "text-embedding-3-small", api_key: Optional[str] = None):
        """
        Initialize OpenAI embedder.

        Args:
            model: OpenAI embedding model name
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = model

        if not self.api_key:
            raise ValueError(
                "OpenAI API key not provided. Either:\n"
                "1. Pass api_key parameter\n"
                "2. Set OPENAI_API_KEY environment variable\n"
                "3. Create .env file with OPENAI_API_KEY=your-key"
            )

        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError("OpenAI package not installed. Run: pip install openai")

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
