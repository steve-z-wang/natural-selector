"""SelectedElement class - rich element objects with multiple output formats."""

from dataclasses import dataclass
from typing import Optional, Dict
from domcontext._internal.ir.dom_ir import DomTreeNode, DomElement
from domcontext._internal.ir.semantic_ir import SemanticElement


@dataclass
class SelectedElement:
    """
    Rich element object with multiple output formats.

    Represents an element selected by natural language query with methods
    to convert to different selector formats (XPath, CSS, backend_node_id).
    """

    element_id: str  # Readable ID like "button-1"
    dom_tree_node: DomTreeNode  # The DOM tree node (has parent references!)
    confidence: float  # Selection confidence score
    rank: int  # Result ranking (1 = top result)
    id_mapping: Dict[str, SemanticElement]  # Mapping from readable ID to SemanticElement

    def to_xpath(self) -> str:
        """
        Generate XPath selector for this element.

        Returns:
            XPath selector string (guaranteed unique)

        Example:
            >>> element.to_xpath()
            '(//button[@type="submit"])[1]'
        """
        from ._internal.selectors.xpath import generate_xpath
        xpath = generate_xpath(self.element_id, self.id_mapping, self.dom_tree_node)
        if xpath is None:
            raise ValueError(f"Could not generate XPath for element {self.element_id}")
        return xpath

    def to_css(self) -> str:
        """
        Generate CSS selector for this element.

        Returns:
            CSS selector string

        Example:
            >>> element.to_css()
            'button[type="submit"]'
        """
        # TODO: Implement CSS selector generation
        # For now, return a basic CSS selector
        if not isinstance(self.dom_tree_node.data, DomElement):
            return ""

        element = self.dom_tree_node.data
        tag = element.tag
        attrs = element.attributes

        # Try id first (most specific)
        if 'id' in attrs:
            return f"{tag}#{attrs['id']}"

        # Try name
        if 'name' in attrs:
            return f"{tag}[name='{attrs['name']}']"

        # Try class
        if 'class' in attrs:
            classes = attrs['class'].replace(' ', '.')
            return f"{tag}.{classes}"

        # Fall back to tag with attributes
        if attrs:
            attr_selectors = [f"[{k}='{v}']" for k, v in list(attrs.items())[:2]]
            return f"{tag}{''.join(attr_selectors)}"

        # Just tag
        return tag

    def to_dict(self) -> dict:
        """
        Serialize element to dictionary.

        Returns:
            Dictionary with element details

        Example:
            >>> element.to_dict()
            {
                'element_id': 'button-1',
                'tag': 'button',
                'text': 'Submit',
                'attributes': {'type': 'submit'},
                'confidence': 0.95,
                'rank': 1,
                'xpath': '//button[@type="submit"]',
                'css': 'button[type="submit"]'
            }
        """
        return {
            'element_id': self.element_id,
            'tag': self.tag,
            'text': self.text,
            'attributes': self.attributes,
            'confidence': self.confidence,
            'rank': self.rank,
            'xpath': self.to_xpath(),
            'css': self.to_css()
        }

    @property
    def tag(self) -> str:
        """Element tag name."""
        if not isinstance(self.dom_tree_node.data, DomElement):
            return ""
        return self.dom_tree_node.data.tag

    @property
    def text(self) -> Optional[str]:
        """Element text content."""
        from domcontext._internal.ir.dom_ir import DomText

        # Collect all text from this node and descendants
        texts = []

        def collect_text(tree_node: DomTreeNode):
            if isinstance(tree_node.data, DomText):
                texts.append(tree_node.data.text.strip())
            for child in tree_node.children:
                collect_text(child)

        collect_text(self.dom_tree_node)
        text = " ".join(texts)
        return text if text else None

    @property
    def attributes(self) -> dict:
        """Element attributes."""
        if not isinstance(self.dom_tree_node.data, DomElement):
            return {}
        return self.dom_tree_node.data.attributes

    def __repr__(self) -> str:
        return f"SelectedElement(id='{self.element_id}', tag='{self.tag}', rank={self.rank}, confidence={self.confidence:.2f})"
