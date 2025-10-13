"""LLM interface for generating responses from retrieved chunks."""

import os
from typing import List, Dict, Tuple, Optional, Literal
from abc import ABC, abstractmethod

# Try to load .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available, use environment variables only


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
            Generated response text
        """
        pass


class OpenAILLM(LLM):
    """OpenAI chat completion LLM."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        """
        Initialize OpenAI LLM.

        Args:
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            model: Model to use (default: gpt-4o)
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

    def generate(self, query: str, context: str, system_prompt: Optional[str] = None) -> str:
        """Generate response using OpenAI."""
        # Default system prompt
        if system_prompt is None:
            system_prompt = """You are a browser automation assistant. Given a webpage's semantic structure
and a user query, identify the relevant element ID.

The context shows the webpage structure in markdown format with element IDs like:
- button-1, div-2, input-3, etc.

IMPORTANT: Only return the element ID(s), nothing else.
- For single element: just "button-1"
- For multiple elements: "button-1, input-2, div-3"
- If not found: "NOT_FOUND"

Do not include explanations, just the ID."""

        # Create messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Webpage Context:\n{context}\n\nQuery: {query}"}
        ]

        # Call OpenAI
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.1,  # Low temperature for consistent responses
        )

        return response.choices[0].message.content


def create_llm(
    provider: Literal["openai"] = "openai",
    **kwargs
) -> LLM:
    """
    Factory function to create an LLM.

    Args:
        provider: LLM provider ("openai")
        **kwargs: Additional arguments for the LLM

    Returns:
        LLM instance
    """
    if provider == "openai":
        return OpenAILLM(**kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def answer_query(
    query: str,
    retriever,
    llm: LLM,
    top_k: int = 3
) -> Dict:
    """
    Answer a query using RAG pipeline.

    Args:
        query: User's natural language query
        retriever: ChunkRetriever instance
        llm: LLM instance
        top_k: Number of chunks to retrieve

    Returns:
        Dictionary with query, retrieved chunks, and response
    """
    # Retrieve relevant chunks
    chunks = retriever.query(query, top_k=top_k)

    # Build context from chunks
    context_parts = []
    for i, (chunk, score) in enumerate(chunks):
        context_parts.append(f"## Context {i+1} (relevance: {score:.2f})")
        context_parts.append(chunk['markdown'])
        context_parts.append("")

    context = "\n".join(context_parts)

    # Generate response
    response = llm.generate(query, context)

    return {
        "query": query,
        "retrieved_chunks": chunks,
        "response": response,
        "num_chunks": len(chunks)
    }
