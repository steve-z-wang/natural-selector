"""Public interfaces for natural-selector.

Users can implement these interfaces to provide custom models.
"""

from .embedder import Embedder
from .llm import LLM

__all__ = ["Embedder", "LLM"]
