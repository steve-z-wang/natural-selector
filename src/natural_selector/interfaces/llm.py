"""LLM interface for natural-selector.

Users can implement this interface to provide custom LLM models.
"""

from abc import ABC, abstractmethod
from typing import Optional


class LLM(ABC):
    """Base class for LLM providers."""

    @abstractmethod
    def generate(self, query: str, context: str, system_prompt: Optional[str] = None) -> str:
        """
        Generate response given query and context.

        Args:
            query: User's natural language query
            context: Context text (markdown chunks)
            system_prompt: Optional system prompt

        Returns:
            Generated element ID (e.g., "button-1" or "button-1, input-2")
        """
        pass
