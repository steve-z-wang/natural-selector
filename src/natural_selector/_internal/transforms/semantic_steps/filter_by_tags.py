"""Pass 1: Filter by tags - remove excluded tags."""

from typing import Optional, Set
from ...ir.nodes import ElementNode, TextNode

# Tags to exclude (not semantic, not useful for interaction)
EXCLUDED_TAGS: Set[str] = {
    'script', 'style', 'noscript', 'meta', 'link', 'title', 'head'
}


def filter_by_tags_pass(node: ElementNode) -> Optional[ElementNode]:
    """
    Pass 1: Filter by tags - remove excluded tags.

    Remove tags like script, style, head, meta, link, etc.

    Args:
        node: ElementNode to process

    Returns:
        ElementNode (ID preserved), or None if excluded
    """
    # Filter out excluded tags
    if node.tag in EXCLUDED_TAGS:
        return None

    # Create new node
    new_node = ElementNode(tag=node.tag, attributes=node.attributes.copy())
    new_node.id = node.id  # Preserve ID

    # Process children recursively
    for child in node.children:
        if isinstance(child, ElementNode):
            filtered_child = filter_by_tags_pass(child)
            if filtered_child:
                new_node.add_child(filtered_child)
        elif isinstance(child, TextNode):
            # Keep all text nodes for now
            new_node.add_child(TextNode(text=child.text))

    return new_node
