"""Page index - holds all indexed data for a semantic IR."""

from typing import List
from ..ir.semantic_ir import SemanticIR
from ...interfaces import Embedder, LLM
from .chunker import Chunk


class PageIndex:
    """
    Index for a page's semantic IR with encapsulated search and LLM resolution.

    Provides:
    - Vector search + LLM resolution via query() method
    - Returns element IDs directly

    Follows LlamaIndex pattern: PageIndex.from_semantic_ir() factory method.
    """

    def __init__(
        self,
        chunks: List[Chunk],
        embedder: Embedder,
        llm: LLM
    ):
        """
        Initialize PageIndex.

        Args:
            chunks: List of Chunk objects with embeddings
            embedder: Embedder for query embedding
            llm: LLM for query resolution
        """
        self.chunks = chunks
        self._embedder = embedder
        self._llm = llm

    @classmethod
    def from_semantic_ir(
        cls,
        semantic_ir: SemanticIR,
        embedder: Embedder,
        llm: LLM,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ) -> 'PageIndex':
        """
        Build PageIndex from SemanticIR.

        Factory method following LlamaIndex pattern (VectorStoreIndex.from_documents).

        Args:
            semantic_ir: SemanticIR with readable IDs
            embedder: Embedder instance for chunking
            llm: LLM for query resolution
            chunk_size: Maximum tokens per chunk
            chunk_overlap: Overlap between chunks

        Returns:
            PageIndex with all indexed data

        Example:
            >>> index = PageIndex.from_semantic_ir(
            ...     semantic_ir,
            ...     embedder=SentenceTransformerEmbedder(),
            ...     llm=OpenAILLM(),
            ...     chunk_size=500
            ... )
        """
        from .chunker import create_chunks
        from .embedder import embed_chunks

        # 1. Create chunks from SemanticIR
        chunks = create_chunks(
            semantic_ir,
            max_tokens=chunk_size,
            overlap_tokens=chunk_overlap
        )

        # 2. Embed chunks (adds embedding field to each chunk)
        chunks = embed_chunks(chunks, embedder)

        # 3. Return PageIndex
        return cls(
            chunks=chunks,
            embedder=embedder,
            llm=llm
        )

    def query(self, query_text: str, top_k: int = 5) -> List[str]:
        """
        Query the index and return element IDs.

        Full pipeline: vector search → LLM → parse element IDs.

        Args:
            query_text: Natural language query (e.g., "search button")
            top_k: Number of chunks to retrieve for context

        Returns:
            List of element IDs (e.g., ["button-1", "button-2"]) ranked by relevance

        Example:
            >>> ids = index.query("search button", top_k=3)
            >>> # ["button-1", "button-2"]
        """
        # 1. Retrieve relevant chunks via vector search
        from .retriever import search_chunks
        chunks = search_chunks(
            query_text,
            self.chunks,
            self._embedder,
            top_k=top_k
        )

        # 2. Build context from chunks
        context_parts = []
        for i, (chunk, score) in enumerate(chunks):
            context_parts.append(f"## Context {i+1} (relevance: {score:.2f})")
            context_parts.append(chunk.markdown)
            context_parts.append("")

        context = "\n".join(context_parts)

        # 3. Generate LLM response with system prompt
        system_prompt = """You are a browser automation assistant. Given a webpage's semantic structure and a user query, identify the relevant element ID.

The context shows the webpage structure in markdown format with element IDs like:
- button-1, div-2, input-3, etc.

IMPORTANT: Only return the element ID(s), nothing else.
- For single element: just "button-1"
- For multiple elements: "button-1, input-2, div-3"
- If not found: "NOT_FOUND"

Do not include explanations, just the ID."""

        response = self._llm.generate(query_text, context, system_prompt=system_prompt)

        # 4. Parse element IDs from response
        response = response.strip()

        # Handle NOT_FOUND
        if response == "NOT_FOUND" or not response:
            return []

        # Parse comma-separated IDs (LLM may return multiple)
        if ',' in response:
            element_ids = [id.strip() for id in response.split(',')]
        else:
            element_ids = [response]

        return element_ids

    def __repr__(self) -> str:
        return f"PageIndex(chunks={len(self.chunks)})"
