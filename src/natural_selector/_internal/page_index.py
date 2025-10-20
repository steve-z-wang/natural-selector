"""Page index - holds all indexed data for element-based embeddings."""

from typing import List, Optional, Dict
from dataclasses import dataclass
from domnode import Node, Text
from ..interfaces import Embedder, LLM


@dataclass
class ElementData:
    """An element with its text representation and embedding."""
    element_id: str
    text_repr: str
    embedding: Optional[List[float]] = None


class PageIndex:
    """
    Index for element-based embeddings with vector search and LLM resolution.

    Provides:
    - Vector search + LLM resolution via query() method
    - Returns element IDs directly

    Follows LlamaIndex pattern: PageIndex.from_node_tree() factory method.
    """

    def __init__(
        self,
        elements: List[ElementData],
        embedder: Embedder,
        llm: LLM
    ):
        """
        Initialize PageIndex.

        Args:
            elements: List of ElementData objects with embeddings
            embedder: Embedder for query embedding
            llm: LLM for query resolution
        """
        self.elements = elements
        self._embedder = embedder
        self._llm = llm

    @staticmethod
    def _generate_element_repr(
        node: Node,
        element_id: str,
        id_mapping: Dict[str, Node],
        max_text_length: int = 200,
        max_sibling_text: int = 50
    ) -> str:
        """
        Generate natural language text representation for an element.

        Format:
            tag: button
            attributes: role="button", aria-label="Search"
            path: body-1 > div-1 > nav-2 > button-3
            text: "Search the web"
            previous sibling: button-2 (text: "Login")
            next sibling: input-1 (placeholder: "Enter query")

        Args:
            node: Node to generate representation for
            element_id: Semantic ID (e.g., "button-3")
            id_mapping: Mapping from semantic_id to Node
            max_text_length: Maximum text length before truncation
            max_sibling_text: Maximum text per sibling

        Returns:
            Natural language text representation
        """
        from domnode import Text

        lines = []

        # 1. Tag
        lines.append(f"tag: {node.tag}")

        # 2. Attributes (semantic ones only)
        semantic_attrs = {}
        for key, value in node.attrib.items():
            # Keep semantic attributes
            if key in {'role', 'type', 'placeholder', 'aria-label', 'aria-describedby',
                      'href', 'src', 'alt', 'title', 'name', 'value', 'for'}:
                semantic_attrs[key] = value

        if semantic_attrs:
            attr_str = ", ".join(f'{k}="{v}"' for k, v in semantic_attrs.items())
            lines.append(f"attributes: {attr_str}")

        # 3. Path (full parent path)
        path_parts = []
        current = node
        while current is not None:
            current_id = current.metadata.get("semantic_id")
            if current_id:
                path_parts.append(current_id)
            # Find parent
            parent = None
            for node_id, n in id_mapping.items():
                if current in n.children:
                    parent = n
                    break
            current = parent

        path_parts.reverse()
        if path_parts:
            lines.append(f"path: {' > '.join(path_parts)}")

        # 4. Text content (all descendant text, truncated)
        def get_all_text(n: Node) -> str:
            texts = []
            for child in n.children:
                if isinstance(child, Text):
                    content = child.content.strip()
                    if content:
                        texts.append(content)
                elif isinstance(child, Node):
                    texts.append(get_all_text(child))
            return " ".join(texts)

        text = get_all_text(node)
        if text:
            if len(text) > max_text_length:
                text = text[:max_text_length] + "..."
            lines.append(f'text: "{text}"')

        # 5. Siblings (previous and next)
        # Find parent and siblings
        parent = None
        for node_id, n in id_mapping.items():
            if node in n.children:
                parent = n
                break

        if parent:
            siblings = [child for child in parent.children if isinstance(child, Node)]
            try:
                current_index = siblings.index(node)

                # Previous sibling
                if current_index > 0:
                    prev_sibling = siblings[current_index - 1]
                    prev_id = prev_sibling.metadata.get("semantic_id", "unknown")
                    prev_text = get_all_text(prev_sibling)
                    if len(prev_text) > max_sibling_text:
                        prev_text = prev_text[:max_sibling_text] + "..."
                    if prev_text:
                        lines.append(f'previous sibling: {prev_id} (text: "{prev_text}")')
                    else:
                        lines.append(f'previous sibling: {prev_id}')

                # Next sibling
                if current_index < len(siblings) - 1:
                    next_sibling = siblings[current_index + 1]
                    next_id = next_sibling.metadata.get("semantic_id", "unknown")
                    next_text = get_all_text(next_sibling)
                    if len(next_text) > max_sibling_text:
                        next_text = next_text[:max_sibling_text] + "..."
                    if next_text:
                        lines.append(f'next sibling: {next_id} (text: "{next_text}")')
                    else:
                        lines.append(f'next sibling: {next_id}')
            except ValueError:
                pass  # Node not found in siblings

        return "\n".join(lines)

    @classmethod
    def from_node_tree(
        cls,
        root: Node,
        id_mapping: Dict[str, Node],
        embedder: Embedder,
        llm: LLM
    ) -> 'PageIndex':
        """
        Build PageIndex from Node tree with element-based embeddings.

        Factory method following LlamaIndex pattern (VectorStoreIndex.from_documents).

        Args:
            root: Root node of filtered tree
            id_mapping: Mapping from semantic_id to Node
            embedder: Embedder instance for element embeddings
            llm: LLM for query resolution

        Returns:
            PageIndex with all indexed data

        Example:
            >>> index = PageIndex.from_node_tree(
            ...     root,
            ...     id_mapping,
            ...     embedder=SentenceTransformerEmbedder(),
            ...     llm=OpenAILLM()
            ... )
        """
        from .embedder import embed_elements

        # 1. Generate text representations for all elements
        elements = []
        for element_id, node in id_mapping.items():
            text_repr = cls._generate_element_repr(node, element_id, id_mapping)
            elements.append(ElementData(
                element_id=element_id,
                text_repr=text_repr,
                embedding=None
            ))

        # 2. Embed elements (adds embedding field to each element)
        elements = embed_elements(elements, embedder)

        # 3. Return PageIndex
        return cls(
            elements=elements,
            embedder=embedder,
            llm=llm
        )

    def query(self, query_text: str, top_k: int = 5) -> List[str]:
        """
        Query the index and return element IDs.

        Full pipeline: vector search → LLM → parse element IDs.

        Args:
            query_text: Natural language query (e.g., "search button")
            top_k: Number of elements to retrieve for context

        Returns:
            List of element IDs (e.g., ["button-1", "button-2"]) ranked by relevance

        Example:
            >>> ids = index.query("search button", top_k=3)
            >>> # ["button-1", "button-2"]
        """
        # 1. Retrieve relevant elements via vector search
        from .retriever import search_elements
        elements = search_elements(
            query_text,
            self.elements,
            self._embedder,
            top_k=top_k
        )

        # 2. Build context from elements
        context_parts = []
        for i, (element, score) in enumerate(elements):
            context_parts.append(f"## Element {i+1} (relevance: {score:.2f})")
            context_parts.append(f"ID: {element.element_id}")
            context_parts.append(element.text_repr)
            context_parts.append("")

        context = "\n".join(context_parts)

        # 3. Generate LLM response with system prompt
        system_prompt = """You are a browser automation assistant. Given webpage elements and a user query, identify the relevant element ID.

The context shows element details with IDs like:
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
        return f"PageIndex(elements={len(self.elements)})"
