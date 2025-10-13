"""Pass 4: Collapse wrappers - collapse single-child wrappers with no attributes."""

from typing import Optional
from ...ir.nodes import ElementNode, TextNode


def collapse_wrappers_pass(node: ElementNode) -> Optional[ElementNode]:
    """
    Pass 4: Collapse single-child wrappers with no attributes.

    If a node has:
    - No attributes AND
    - Exactly one element child (ignoring whitespace text)
    → Promote the child (collapse wrapper)

    Args:
        node: ElementNode to process

    Returns:
        ElementNode (ID preserved) or promoted child, or None
    """
    # Process children first (bottom-up)
    collapsed_children = []
    for child in node.children:
        if isinstance(child, ElementNode):
            collapsed_child = collapse_wrappers_pass(child)
            if collapsed_child:
                collapsed_children.append(collapsed_child)
        elif isinstance(child, TextNode):
            collapsed_children.append(child)

    # Check if this is a wrapper to collapse
    has_attributes = bool(node.attributes)

    if not has_attributes:
        # Count element children and meaningful text
        element_children = [c for c in collapsed_children if isinstance(c, ElementNode)]
        text_children = [c for c in collapsed_children if isinstance(c, TextNode)]
        has_meaningful_text = any(c.text.strip() for c in text_children)

        # Collapse if: no attributes, single element child, no meaningful text
        if len(element_children) == 1 and not has_meaningful_text:
            # Promote the child
            return element_children[0]

    # Keep node
    new_node = ElementNode(tag=node.tag, attributes=node.attributes.copy())
    new_node.id = node.id  # Preserve ID

    for child in collapsed_children:
        new_node.add_child(child)

    return new_node
