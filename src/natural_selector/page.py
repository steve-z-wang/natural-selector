"""Page class - parsed page with cached IR and embeddings."""

from typing import List, Optional
from ._internal.ir.semantic_ir import SemanticIR
from ._internal.index.page_index import PageIndex
from .element import SelectedElement
from .interfaces import Embedder, LLM


class Page:
    """
    Parsed page with cached IR and embeddings.

    Allows multiple queries on the same page without recomputing embeddings.

    Example usage:
        ```python
        # Create page from session
        page = session.create_page_from_html(html)

        # Query multiple times (reuses embeddings)
        button = page.select_one("search button")
        input_field = page.select_one("email input")
        all_links = page.select("navigation links")
        ```
    """

    def __init__(
        self,
        semantic_ir: SemanticIR,
        embedder: Embedder,
        llm: LLM,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        default_top_k: int = 5
    ):
        """
        Initialize Page with SemanticIR and configuration.

        Args:
            semantic_ir: SemanticIR (for element resolution)
            embedder: Embedder for building index
            llm: LLM for query resolution
            chunk_size: Maximum tokens per chunk
            chunk_overlap: Overlap between chunks
            default_top_k: Default number of chunks for RAG context

        Note:
            - DomIR access is via SemanticElement.dom_tree_node references
            - Index built lazily on first query (expensive operation!)
        """
        self._semantic_ir = semantic_ir
        self._embedder = embedder
        self._llm = llm
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._default_top_k = default_top_k
        self._index: Optional[PageIndex] = None  # Built lazily on first query!

    def select(self, query: str, top_k: Optional[int] = None) -> List[SelectedElement]:
        """
        Query elements with natural language.

        Args:
            query: Natural language query (e.g., "search button")
            top_k: Override default top_k if specified

        Returns:
            List of selected elements, ranked by confidence

        Example:
            >>> elements = page.select("all buttons")
            >>> for elem in elements:
            ...     print(elem.tag, elem.confidence)
        """
        # Build index lazily on first query (expensive operation!)
        if self._index is None:
            self._index = PageIndex.from_semantic_ir(
                self._semantic_ir,
                embedder=self._embedder,
                llm=self._llm,
                chunk_size=self._chunk_size,
                chunk_overlap=self._chunk_overlap
            )

        # Query index for element IDs (vector search + LLM)
        k = top_k if top_k is not None else self._default_top_k
        element_ids = self._index.query(query, top_k=k)

        if not element_ids:
            return []

        # Map IDs to DomTreeNodes via SemanticIR
        selected_elements = []
        for rank, element_id in enumerate(element_ids, start=1):
            # Use SemanticIR to get element by ID
            semantic_element = self._semantic_ir.get_element_by_id(element_id)
            if semantic_element and semantic_element.dom_tree_node:
                selected = SelectedElement(
                    element_id=element_id,
                    dom_tree_node=semantic_element.dom_tree_node,
                    confidence=1.0 / rank,  # Simple confidence based on rank
                    rank=rank,
                    id_mapping=self._semantic_ir.get_all_elements_with_ids()
                )
                selected_elements.append(selected)

        return selected_elements

    def select_one(self, query: str) -> Optional[SelectedElement]:
        """
        Get top result for natural language query.

        Args:
            query: Natural language query (e.g., "search button")

        Returns:
            Top selected element, or None if not found

        Example:
            >>> button = page.select_one("submit button")
            >>> if button:
            ...     print(button.to_xpath())
        """
        results = self.select(query)
        return results[0] if results else None

    def __repr__(self) -> str:
        return f"Page(semantic_ir={self._semantic_ir})"
