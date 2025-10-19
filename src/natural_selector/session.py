"""Public API for natural-selector."""

from typing import Dict, Optional, List
from domcontext import DomContext
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

    def _create_page_from_dom_context(self, dom_context: DomContext) -> 'Page':
        """
        Internal: Create Page from DomContext.

        Args:
            dom_context: DomContext with parsed and filtered DOM

        Returns:
            Page object ready for querying

        Raises:
            ValueError: If no semantic elements found
        """
        from .page import Page

        # Extract semantic_ir from DomContext (internal API)
        semantic_ir = dom_context._semantic_ir
        if not semantic_ir:
            raise ValueError("No semantic elements found")

        # Create and return Page (index built lazily on first query!)
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
            html: HTML string (supports backend_node_id attributes from Mind2Web)

        Returns:
            Page object ready for querying

        Example:
            >>> page = session.create_page_from_html(html_string)
            >>> element = page.select_one("search button")
        """
        # Use DomContext.from_html() with all filters enabled
        dom_context = DomContext.from_html(
            html,
            filter_non_visible_tags=True,
            filter_css_hidden=True,
            filter_zero_dimensions=True,
            filter_attributes=True,
            filter_empty=True,
            collapse_wrappers=True
        )

        # Create Page from DomContext
        return self._create_page_from_dom_context(dom_context)

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
        # Use DomContext.from_cdp() with all filters enabled
        dom_context = DomContext.from_cdp(
            cdp_snapshot,
            filter_non_visible_tags=True,
            filter_css_hidden=True,
            filter_zero_dimensions=True,
            filter_attributes=True,
            filter_empty=True,
            collapse_wrappers=True
        )

        # Create Page from DomContext
        return self._create_page_from_dom_context(dom_context)
