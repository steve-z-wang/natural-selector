"""Public API for natural-selector."""

from typing import Dict, Optional, List
from .interfaces import Embedder, LLM


class NaturalSelector:
    """
    Natural language browser automation selector.

    Example usage:
        ```python
        from natural_selector import NaturalSelector
        from natural_selector.integrations import OpenAILLM

        # Create selector with LLM
        selector = NaturalSelector(llm=OpenAILLM(api_key="sk-..."))

        # Get XPath for natural language query
        xpath = selector.select(cdp_snapshot, "search button")
        ```
    """

    def __init__(
        self,
        llm: LLM,
        embedder: Optional[Embedder] = None,
        top_k: int = 3
    ):
        """
        Initialize Natural Selector.

        Args:
            llm: LLM instance (required). User must provide.
            embedder: Embedder instance (optional). Defaults to Sentence Transformers.
            top_k: Number of chunks to retrieve for context (default: 3)
        """
        self.llm = llm
        self.top_k = top_k

        # Default embedder: Sentence Transformers (local, free)
        if embedder is None:
            from ._internal.rag.embedder import SentenceTransformerEmbedder
            self.embedder = SentenceTransformerEmbedder()
        else:
            self.embedder = embedder

        # Cache for processed page
        self._full_ir = None
        self._semantic_ir = None
        self._id_mapping = None
        self._embedded_chunks = None
        self._retriever = None

    def select(self, cdp_snapshot: Dict, query: str) -> List[str]:
        """
        Generate XPath selectors for natural language query.

        Args:
            cdp_snapshot: CDP DOMSnapshot dictionary
            query: Natural language query (e.g., "search button")

        Returns:
            List of XPath selector strings (empty list if not found)

        Example:
            >>> xpaths = selector.select(snapshot, "search button")
            >>> print(xpaths)
            ['//input[@name="btnK"][@type="submit"]', '//input[@name="btnK"][@type="submit"]']
        """
        # Step 1: Parse and filter if not cached
        if self._full_ir is None:
            self._process_snapshot(cdp_snapshot)

        # Step 2: Query with RAG
        element_ids = self._query_element(query)
        if not element_ids:
            return []

        # Step 3: Generate XPath for each element ID
        from ._internal.selector import generate_xpath
        xpaths = []
        for element_id in element_ids:
            xpath = generate_xpath(element_id, self._id_mapping, self._full_ir)
            if xpath:
                xpaths.append(xpath)

        return xpaths

    def _process_snapshot(self, cdp_snapshot: Dict):
        """Process CDP snapshot through pipeline."""
        from ._internal.parsers.cdp_parser import parse_cdp_snapshot
        from ._internal.transforms import visibility_pass, semantic_pass, add_identifiers_pass
        from ._internal.rag.markdown_serializer import serialize_to_markdown
        from ._internal.rag.chunker import chunk_ir
        from ._internal.rag.embedder import embed_chunks
        from ._internal.rag.retriever import ChunkRetriever

        # Parse
        self._full_ir = parse_cdp_snapshot(cdp_snapshot)

        # Filter
        visible_ir = visibility_pass(self._full_ir)
        if not visible_ir:
            raise ValueError("No visible elements found")

        semantic_ir = semantic_pass(visible_ir)
        if not semantic_ir:
            raise ValueError("No semantic elements found")

        # Add identifiers
        self._semantic_ir = add_identifiers_pass(semantic_ir)

        # Serialize and chunk
        markdown_text, self._id_mapping = serialize_to_markdown(self._semantic_ir)
        chunks = chunk_ir(self._semantic_ir, max_tokens=500, overlap_tokens=50)

        # Embed chunks
        self._embedded_chunks = embed_chunks(chunks, self.embedder)

        # Create retriever
        self._retriever = ChunkRetriever(self._embedded_chunks, self.embedder)

    def _query_element(self, query: str) -> List[str]:
        """Query for element IDs using RAG + LLM.

        Returns:
            List of element IDs (may be empty if not found)
        """
        from ._internal.rag.llm import answer_query

        # Get answer using configured top_k
        result = answer_query(query, self._retriever, self.llm, top_k=self.top_k)

        # Extract element ID(s)
        response = result['response'].strip()

        # Handle NOT_FOUND
        if response == "NOT_FOUND" or not response:
            return []

        # Parse comma-separated IDs (LLM may return multiple)
        if ',' in response:
            ids = [id.strip() for id in response.split(',')]
        else:
            ids = [response]

        # Filter to only valid IDs that exist in mapping
        valid_ids = [id for id in ids if id in self._id_mapping]

        return valid_ids if valid_ids else []

    def clear_cache(self):
        """Clear cached page data to process a new page."""
        self._full_ir = None
        self._semantic_ir = None
        self._id_mapping = None
        self._embedded_chunks = None
        self._retriever = None
