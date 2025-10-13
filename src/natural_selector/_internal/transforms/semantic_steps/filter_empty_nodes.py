"""Pass 3: Filter empty nodes - remove nodes with no attributes and no children."""

from typing import Optional, Set
from ...ir.nodes import ElementNode, TextNode

# Interactive tags that should be kept even without attributes
INTERACTIVE_TAGS: Set[str] = {
    'a', 'button', 'input', 'select', 'textarea', 'label'
}


def filter_empty_nodes_pass(node: ElementNode) -> Optional[ElementNode]:
    """
    Pass 3: Filter empty nodes.

    Remove nodes that have:
    - No semantic attributes AND
    - No children

    Exception: Keep interactive tags even without attributes (they may be useful)

    Args:
        node: ElementNode to process

    Returns:
        ElementNode (ID preserved), or None if empty
    """
    # Process children first (bottom-up)
    filtered_children = []
    for child in node.children:
        if isinstance(child, ElementNode):
            filtered_child = filter_empty_nodes_pass(child)
            if filtered_child:
                filtered_children.append(filtered_child)
        elif isinstance(child, TextNode):
            # Keep text with content
            if child.text.strip():
                filtered_children.append(child)

    # Check if node should be filtered
    has_attributes = bool(node.attributes)
    has_children = bool(filtered_children)
    is_interactive = node.tag in INTERACTIVE_TAGS

    # Filter out if: no attributes AND no children AND not interactive
    if not has_attributes and not has_children and not is_interactive:
        return None

    # Keep node
    new_node = ElementNode(tag=node.tag, attributes=node.attributes.copy())
    new_node.id = node.id  # Preserve ID

    for child in filtered_children:
        new_node.add_child(child)

    return new_node
