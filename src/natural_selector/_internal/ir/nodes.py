"""Node structures for the intermediate representation."""

import uuid
from abc import ABC
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class BoundingBox:
    """Bounding box coordinates from CDP layout data."""
    x: float
    y: float
    width: float
    height: float


class Node(ABC):
    """Base class for all nodes in the IR."""

    def __init__(self):
        self.id = str(uuid.uuid4())


class TextNode(Node):
    """Text content node."""

    def __init__(self, text: str):
        super().__init__()
        self.text = text

    def to_dict(self) -> str:
        """Convert to string (text content directly)."""
        return self.text

    def __repr__(self) -> str:
        preview = self.text[:50] + "..." if len(self.text) > 50 else self.text
        return f'TextNode(id="{self.id}", text="{preview}")'


class ElementNode(Node):
    """Element node with tag, attributes, and children."""

    def __init__(
        self,
        tag: str,
        cdp_index: Optional[int] = None,
        attributes: Optional[Dict[str, str]] = None,
        styles: Optional[Dict[str, str]] = None,
        bounds: Optional[BoundingBox] = None
    ):
        super().__init__()
        self.cdp_index = cdp_index  # Only present in Full IR
        self.tag = tag
        self.attributes = attributes or {}
        self.styles = styles or {}  # Only present in Full IR
        self.bounds = bounds  # Only present in Full IR
        self.tag_id: Optional[int] = None  # LLM-friendly identifier (e.g., 1, 2, 3 for button-1, button-2, button-3)
        self.children: List[Node] = []

    def add_child(self, child: Node) -> None:
        """Add a child node (TextNode or ElementNode)."""
        self.children.append(child)

    def get_element_children(self) -> List['ElementNode']:
        """Get only ElementNode children."""
        return [c for c in self.children if isinstance(c, ElementNode)]

    def get_text_children(self) -> List[TextNode]:
        """Get only TextNode children."""
        return [c for c in self.children if isinstance(c, TextNode)]

    def get_all_text(self) -> str:
        """Get all text content recursively."""
        text_parts = []
        for child in self.children:
            if isinstance(child, TextNode):
                text_parts.append(child.text)
            elif isinstance(child, ElementNode):
                text_parts.append(child.get_all_text())
        return " ".join(text_parts).strip()

    def copy(
        self,
        preserve_id: bool = True,
        include_cdp_data: bool = False
    ) -> 'ElementNode':
        """
        Create a copy of this node.

        Args:
            preserve_id: If True, keep the same ID (for filtered IRs)
            include_cdp_data: If True, copy cdp_index, styles, bounds
        """
        new_node = ElementNode(
            tag=self.tag,
            cdp_index=self.cdp_index if include_cdp_data else None,
            attributes=self.attributes.copy(),
            styles=self.styles.copy() if include_cdp_data else None,
            bounds=self.bounds if include_cdp_data else None
        )
        if preserve_id:
            new_node.id = self.id
        return new_node

    def to_dict(self) -> dict:
        """
        Convert to dictionary representation.

        Format: {
            "tag": "div",
            "attr1": "value1",
            "attr2": "value2",
            "children": [...]
        }
        """
        result = {"tag": self.tag}

        # Add attributes directly to dict
        result.update(self.attributes)

        # Add children
        children_data = []
        for child in self.children:
            if isinstance(child, ElementNode):
                children_data.append(child.to_dict())
            elif isinstance(child, TextNode):
                children_data.append(child.to_dict())  # Returns string

        if children_data:
            result["children"] = children_data

        return result

    def __repr__(self) -> str:
        return f'ElementNode(id="{self.id}", tag="{self.tag}", children={len(self.children)})'


class SemanticNode(Node):
    """Semantic node for Semantic IR - minimal structure with only semantic info."""

    def __init__(self, tag: str, semantic_attributes: Optional[Dict[str, str]] = None):
        super().__init__()
        self.tag = tag
        self.semantic_attributes = semantic_attributes or {}
        self.semantic_children: List = []  # Can be SemanticNode or str (text)

    def add_child(self, child) -> None:
        """Add a child (SemanticNode or text string)."""
        self.semantic_children.append(child)

    def to_dict(self) -> dict:
        """
        Convert to dictionary representation.

        Format: {
            "tag": "button",
            "semantic_attr1": "value1",
            "children": [...]
        }
        """
        result = {"tag": self.tag}

        # Add semantic attributes directly to dict
        result.update(self.semantic_attributes)

        # Add children
        if self.semantic_children:
            children_data = []
            for child in self.semantic_children:
                if isinstance(child, SemanticNode):
                    children_data.append(child.to_dict())
                else:
                    # Text content as string
                    children_data.append(child)

            result["children"] = children_data

        return result

    def __repr__(self) -> str:
        return f'SemanticNode(id="{self.id}", tag="{self.tag}", children={len(self.semantic_children)})'


class IR:
    """Container for the intermediate representation tree."""

    def __init__(self, root: ElementNode):
        self.root = root
        self._node_index: Optional[Dict[str, ElementNode]] = None

    def _build_index(self) -> None:
        """Build index of all ElementNodes by ID."""
        self._node_index = {}

        def index_recursive(node: Node):
            if isinstance(node, ElementNode):
                self._node_index[node.id] = node
                for child in node.children:
                    index_recursive(child)

        index_recursive(self.root)

    def get_node_by_id(self, node_id: str) -> Optional[ElementNode]:
        """Get an ElementNode by its ID."""
        if self._node_index is None:
            self._build_index()
        return self._node_index.get(node_id)

    def all_element_nodes(self) -> List[ElementNode]:
        """Get all ElementNodes in the tree."""
        if self._node_index is None:
            self._build_index()
        return list(self._node_index.values())

    def to_dict(self) -> dict:
        """Convert entire IR tree to dictionary representation."""
        return self.root.to_dict()

    def __repr__(self) -> str:
        total = len(self.all_element_nodes())
        return f'IR(root="{self.root.tag}", total_nodes={total})'
