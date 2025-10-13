"""Visibility filtering pass: Full IR → Visible IR.

Filters out invisible elements while preserving node IDs.
"""

from typing import Optional
from ..ir.nodes import ElementNode, TextNode, Node, IR


def visibility_pass(full_ir: IR) -> Optional[IR]:
    """
    Create Visible IR from Full IR by filtering invisible elements.

    Args:
        full_ir: Full IR with complete tree

    Returns:
        IR: Visible IR with only visible elements (IDs preserved), or None if empty
    """
    visible_root = _filter_node(full_ir.root)

    if visible_root is None:
        return None

    return IR(visible_root)


def _filter_node(node: ElementNode, parent_visible: bool = True) -> Optional[ElementNode]:
    """
    Recursively filter invisible nodes.

    Args:
        node: ElementNode to filter
        parent_visible: Whether parent chain is visible

    Returns:
        ElementNode with ID preserved, or None if invisible
    """
    # Check if this node is visible
    is_visible = parent_visible and _is_node_visible(node)

    if not is_visible:
        return None

    # Node is visible, create copy (preserving ID, excluding CDP data)
    new_node = node.copy(preserve_id=True, include_cdp_data=False)

    # Process children
    for child in node.children:
        if isinstance(child, ElementNode):
            visible_child = _filter_node(child, is_visible)
            if visible_child:
                new_node.add_child(visible_child)
        elif isinstance(child, TextNode):
            # Keep text nodes if parent is visible
            new_node.add_child(TextNode(text=child.text))

    return new_node


def _parse_inline_style(style_attr: str) -> dict:
    """
    Parse inline style attribute into a dictionary.

    Args:
        style_attr: Style attribute string like "display:none;color:red"

    Returns:
        Dictionary of style properties
    """
    styles = {}
    if not style_attr:
        return styles

    # Split by semicolon
    for declaration in style_attr.split(';'):
        declaration = declaration.strip()
        if ':' in declaration:
            prop, value = declaration.split(':', 1)
            styles[prop.strip().lower()] = value.strip().lower()

    return styles


def _is_node_visible(node: ElementNode) -> bool:
    """
    Check if a node is visible based on CDP data and inline styles.

    Returns:
        bool: True if visible, False otherwise
    """
    # Check computed styles from CDP
    display = node.styles.get('display', '').lower()
    visibility = node.styles.get('visibility', '').lower()
    opacity = node.styles.get('opacity', '1')

    # Also check inline style attribute (takes precedence)
    inline_style = node.attributes.get('style', '')
    if inline_style:
        inline_styles = _parse_inline_style(inline_style)
        display = inline_styles.get('display', display)
        visibility = inline_styles.get('visibility', visibility)
        opacity = inline_styles.get('opacity', opacity)

    # Check display style
    if display == 'none':
        return False

    # Check visibility style
    if visibility == 'hidden':
        return False

    # Check opacity
    try:
        if float(opacity) == 0:
            return False
    except (ValueError, TypeError):
        pass

    # Check bounding box
    if node.bounds:
        if node.bounds.width <= 0 or node.bounds.height <= 0:
            return False

    # Check hidden attribute
    if 'hidden' in node.attributes:
        return False

    # Check for hidden input
    if node.tag == 'input' and node.attributes.get('type', '').lower() == 'hidden':
        return False

    return True
