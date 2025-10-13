"""Pass 2: Filter by attributes - remove non-semantic attributes and nodes."""

from typing import Optional, Set
from ...ir.nodes import ElementNode, TextNode

# Semantic attributes to preserve
SEMANTIC_ATTRIBUTES: Set[str] = {
    'role', 'aria-label', 'aria-labelledby', 'aria-describedby',
    'aria-checked', 'aria-selected', 'aria-expanded',
    'type', 'name', 'placeholder', 'value', 'alt', 'title'
}

# Non-semantic roles to filter out
NON_SEMANTIC_ROLES: Set[str] = {'none', 'presentation'}


def filter_by_attributes_pass(node: ElementNode) -> Optional[ElementNode]:
    """
    Pass 2: Filter by attributes.

    - Remove nodes with aria-hidden="true"
    - Remove nodes with role="presentation" or role="none"
    - Keep only SEMANTIC_ATTRIBUTES

    Args:
        node: ElementNode to process

    Returns:
        ElementNode with filtered attributes (ID preserved), or None if filtered
    """
    # Filter out nodes with aria-hidden="true"
    if node.attributes.get('aria-hidden', '').lower() == 'true':
        return None

    # Filter out nodes with non-semantic role
    role = node.attributes.get('role', '').lower()
    if role in NON_SEMANTIC_ROLES:
        return None

    # Filter attributes to keep only semantic ones
    filtered_attrs = {
        key: value
        for key, value in node.attributes.items()
        if key in SEMANTIC_ATTRIBUTES
    }

    # Create new node with filtered attributes
    new_node = ElementNode(tag=node.tag, attributes=filtered_attrs)
    new_node.id = node.id  # Preserve ID

    # Process children recursively
    for child in node.children:
        if isinstance(child, ElementNode):
            filtered_child = filter_by_attributes_pass(child)
            if filtered_child:
                new_node.add_child(filtered_child)
        elif isinstance(child, TextNode):
            # Keep text nodes with content
            if child.text.strip():
                new_node.add_child(TextNode(text=child.text))

    return new_node
