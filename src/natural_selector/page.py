"""Page class - parsed page with cached element embeddings."""

from typing import List, Optional, Dict
from domnode import Node
from ._internal.page_index import PageIndex
from .element import SelectedElement
from .interfaces import Embedder, LLM


class Page:
    """
    Parsed page with cached element embeddings.

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
        root: Node,
        id_mapping: Dict[str, Node],
        embedder: Embedder,
        llm: LLM,
        default_top_k: int = 5
    ):
        """
        Initialize Page with Node tree and configuration.

        Args:
            root: Filtered Node tree with semantic IDs
            id_mapping: Mapping from semantic_id to Node
            embedder: Embedder for building index
            llm: LLM for query resolution
            default_top_k: Default number of elements for RAG context

        Note:
            - Index built lazily on first query (expensive operation!)
        """
        self._root = root
        self._id_mapping = id_mapping
        self._embedder = embedder
        self._llm = llm
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
            self._index = PageIndex.from_node_tree(
                self._root,
                self._id_mapping,
                embedder=self._embedder,
                llm=self._llm,
            )

        # Query index for element IDs (vector search + LLM)
        k = top_k if top_k is not None else self._default_top_k
        element_ids = self._index.query(query, top_k=k)

        if not element_ids:
            return []

        # Map IDs to Nodes
        selected_elements = []
        for rank, element_id in enumerate(element_ids, start=1):
            node = self._id_mapping.get(element_id)
            if node is not None:
                selected = SelectedElement(
                    element_id=element_id,
                    node=node,
                    confidence=1.0 / rank,  # Simple confidence based on rank
                    rank=rank,
                    id_mapping=self._id_mapping
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

    def get_formatted_page(self, format: str = "markdown") -> str:
        """
        Get formatted representation of the page structure.

        Args:
            format: "markdown" or "json"

        Returns:
            Formatted string representation of the page

        Example:
            >>> print(page.get_formatted_page())
            - body-1
              - nav-1 (role="navigation")
                - a-1 (href="/about")
                  - "About"
        """
        if format == "markdown":
            return self._to_markdown()
        elif format == "json":
            import json
            return json.dumps(self._to_json(), indent=2)
        else:
            raise ValueError(f"Format must be 'markdown' or 'json', got: {format}")

    def _to_markdown(self) -> str:
        """Convert node tree to markdown format."""
        from domnode import Text

        def node_to_markdown(node: Node, indent: int = 0) -> List[str]:
            lines = []
            semantic_id = node.metadata.get("semantic_id", "")

            # Format attributes
            attrs = []
            for key, value in node.attrib.items():
                attrs.append(f'{key}="{value}"')
            attr_str = f" ({', '.join(attrs)})" if attrs else ""

            # Add node line
            prefix = "  " * indent + "- "
            lines.append(f"{prefix}{semantic_id}{attr_str}")

            # Add children
            for child in node.children:
                if isinstance(child, Node):
                    lines.extend(node_to_markdown(child, indent + 1))
                elif isinstance(child, Text):
                    content = child.content.strip()
                    if content:
                        text_prefix = "  " * (indent + 1) + "- "
                        lines.append(f'{text_prefix}"{content}"')

            return lines

        return "\n".join(node_to_markdown(self._root))

    def _to_json(self) -> dict:
        """Convert node tree to JSON format."""
        from domnode import Text

        def node_to_dict(node: Node) -> dict:
            result = {
                'type': 'element',
                'tag': node.tag,
                'semantic_id': node.metadata.get('semantic_id'),
                'attributes': dict(node.attrib),
                'children': []
            }
            for child in node.children:
                if isinstance(child, Node):
                    result['children'].append(node_to_dict(child))
                elif isinstance(child, Text):
                    result['children'].append({
                        'type': 'text',
                        'text': child.content
                    })
            return result

        return {
            'root': node_to_dict(self._root),
            'total_elements': len(self._id_mapping)
        }

    def __repr__(self) -> str:
        return f"Page(elements={len(self._id_mapping)})"
