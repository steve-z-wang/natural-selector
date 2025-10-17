"""Public API for natural-selector."""

from typing import Dict, Optional, List
from .interfaces import Embedder, LLM


class Session:
    """
    Session for natural language browser automation.

    Configure once and create multiple pages with the same settings.

    Example usage:
        ```python
        from natural_selector import Session
        from natural_selector.integrations import OpenAILLM

        # Create session with LLM
        session = Session(llm=OpenAILLM(api_key="sk-..."))

        # Create pages
        page = session.create_page_from_html(html)
        element = page.select_one("search button")
        ```
    """

    def __init__(
        self,
        llm: LLM,
        embedder: Optional[Embedder] = None,
        # RAG parameters
        top_k: int = 3,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ):
        """
        Initialize Session.

        Args:
            llm: LLM instance (required). User must provide.
            embedder: Embedder instance (optional). Defaults to Sentence Transformers.
            top_k: Number of chunks to retrieve for RAG context (default: 3)
            chunk_size: Maximum tokens per chunk (default: 500)
            chunk_overlap: Overlap between chunks in tokens (default: 50)

        Note:
            Visibility filtering (display:none, script/style tags, etc.) is always applied.
            CDP metadata (cdp_index, styles, bounds) is always preserved in DomElement.
        """
        self.llm = llm
        self.top_k = top_k
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Default embedder: Sentence Transformers (local, free)
        if embedder is None:
            from .integrations import SentenceTransformerEmbedder
            self.embedder = SentenceTransformerEmbedder()
        else:
            self.embedder = embedder

    def _create_page_from_dom_ir(self, dom_ir: 'DomIR') -> 'Page':
        """
        Internal: Create Page from DomIR through filtering pipeline.

        Args:
            dom_ir: DomIR to process

        Returns:
            Page object ready for querying

        Raises:
            ValueError: If no visible or semantic elements found
        """
        from ._internal.filters import visibility_pass, semantic_pass
        from .page import Page

        # Apply visibility filter (DomIR → DomIR)
        visible_dom_ir = visibility_pass(dom_ir)
        if not visible_dom_ir:
            raise ValueError("No visible elements found")

        # Apply semantic filter (DomIR → SemanticIR)
        semantic_ir = semantic_pass(visible_dom_ir)
        if not semantic_ir:
            raise ValueError("No semantic elements found")

        # Create and return Page (index built lazily on first query!)
        # Note: DomIR access is via SemanticElement.dom_tree_node references
        return Page(
            semantic_ir=semantic_ir,
            embedder=self.embedder,
            llm=self.llm,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            default_top_k=self.top_k
        )

    def create_page_from_html(self, html: str) -> 'Page':
        """
        Create Page from HTML string.

        Parses HTML and creates a Page object with cached embeddings.

        Args:
            html: HTML string

        Returns:
            Page object ready for querying

        Example:
            >>> page = session.create_page_from_html(html_string)
            >>> element = page.select_one("search button")
        """
        # TODO: Implement HTML parser
        # from ._internal.parsers.html_parser import parse_html
        # dom_ir = parse_html(html)
        # return self._create_page_from_dom_ir(dom_ir)
        raise NotImplementedError("HTML parser not yet implemented. Use create_page_from_cdp() for now.")

    def create_page_from_cdp(self, cdp_snapshot: Dict) -> 'Page':
        """
        Create Page from CDP snapshot dictionary.

        Parses CDP snapshot and creates a Page object.
        Embedding happens lazily on first query.

        Args:
            cdp_snapshot: CDP DOMSnapshot dictionary from Playwright/Puppeteer

        Returns:
            Page object ready for querying

        Example:
            >>> page = session.create_page_from_cdp(snapshot)
            >>> element = page.select_one("search button")
        """
        from ._internal.parsers.cdp_parser import parse_cdp_snapshot

        # Parse CDP snapshot to DomIR
        dom_ir = parse_cdp_snapshot(cdp_snapshot)

        # Apply filtering pipeline and create Page
        return self._create_page_from_dom_ir(dom_ir)
