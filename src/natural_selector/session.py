"""Public API for natural-selector."""

from typing import Dict, Optional, List, Tuple
from domnode import Node, parse_html, parse_cdp, filter_all
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
        top_k: int = 5,
    ):
        """
        Initialize Session.

        Args:
            llm: LLM instance (required). User must provide.
            embedder: Embedder instance (optional). Defaults to Sentence Transformers.
            top_k: Number of elements to retrieve for RAG context (default: 5)

        Note:
            Visibility filtering (display:none, script/style tags, etc.) is always applied.
            CDP metadata (backend_node_id, styles, bounds) is always preserved in Node metadata.
        """
        self.llm = llm
        self.top_k = top_k

        # Default embedder: Sentence Transformers (local, free)
        if embedder is None:
            from .integrations import SentenceTransformerEmbedder
            self.embedder = SentenceTransformerEmbedder()
        else:
            self.embedder = embedder

    @staticmethod
    def _generate_semantic_ids(node: Node) -> Tuple[Node, Dict[str, Node]]:
        """Generate semantic IDs for all element nodes.

        Args:
            node: Root node of tree

        Returns:
            Tuple of (node with IDs in metadata, dict mapping ID to node)
        """
        tag_counts: Dict[str, int] = {}
        id_mapping: Dict[str, Node] = {}

        def traverse(n: Node) -> None:
            tag = n.tag
            if tag not in tag_counts:
                tag_counts[tag] = 0
            tag_counts[tag] += 1

            semantic_id = f"{tag}-{tag_counts[tag]}"
            n.metadata["semantic_id"] = semantic_id
            id_mapping[semantic_id] = n

            for child in n.children:
                if isinstance(child, Node):
                    traverse(child)

        traverse(node)
        return node, id_mapping

    def _create_page_from_node(self, root: Node) -> 'Page':
        """
        Internal: Create Page from filtered Node tree.

        Args:
            root: Filtered Node tree

        Returns:
            Page object ready for querying
        """
        from .page import Page

        # Generate semantic IDs
        root, id_mapping = self._generate_semantic_ids(root)

        # Create and return Page (index built lazily on first query!)
        return Page(
            root=root,
            id_mapping=id_mapping,
            embedder=self.embedder,
            llm=self.llm,
            default_top_k=self.top_k
        )

    def create_page_from_html(self, html: str) -> 'Page':
        """
        Create Page from HTML string.

        Parses HTML and creates a Page object with element embeddings.

        Args:
            html: HTML string (supports backend_node_id attributes from Mind2Web)

        Returns:
            Page object ready for querying

        Example:
            >>> page = session.create_page_from_html(html_string)
            >>> element = page.select_one("search button")
        """
        # Parse and filter HTML using domnode
        root = parse_html(html)
        filtered = filter_all(root)

        if filtered is None:
            raise ValueError("No visible elements found after filtering")

        # Create Page from filtered tree
        return self._create_page_from_node(filtered)

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
        # Parse and filter CDP using domnode
        root = parse_cdp(cdp_snapshot)
        filtered = filter_all(root)

        if filtered is None:
            raise ValueError("No visible elements found after filtering")

        # Create Page from filtered tree
        return self._create_page_from_node(filtered)
