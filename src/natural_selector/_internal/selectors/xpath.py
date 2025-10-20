"""Generate XPath selectors from element IDs."""

from typing import Dict, Optional, List
from domnode import Node


def generate_xpath(element_id: str, id_mapping: Dict[str, Node], target_node: Node) -> Optional[str]:
    """
    Generate guaranteed unique XPath selector for an element ID.

    Args:
        element_id: Readable element ID from LLM (e.g., "button-1")
        id_mapping: Mapping from readable ID to Node
        target_node: The target Node

    Returns:
        XPath selector string (guaranteed unique), or None if element not found
    """
    # Find root node from id_mapping
    root = _find_root(id_mapping)
    if root is None:
        return None

    # Build guaranteed unique XPath
    return _build_unique_xpath(target_node, root)


def _find_root(id_mapping: Dict[str, Node]) -> Optional[Node]:
    """Find root node from id_mapping."""
    if not id_mapping:
        return None

    # Look for special __root__ key added by Page
    if "__root__" in id_mapping:
        return id_mapping["__root__"]

    # Fallback: find node with tag 'html' or 'body'
    for n in id_mapping.values():
        if n.tag in ('html', 'body'):
            return n

    # Last resort: return first node
    return next(iter(id_mapping.values()))


def _build_unique_xpath(target_node: Node, root: Node) -> str:
    """
    Build guaranteed unique XPath using attributes + position.

    Strategy:
    1. Build attribute-based selector
    2. Find position among all matching nodes
    3. Add position to guarantee uniqueness: (//tag[@attr='value'])[position]
    """
    # Build base XPath with attributes
    base_xpath = _build_attribute_xpath(target_node)

    if not base_xpath:
        # No attributes - use path-based XPath (already unique)
        return _build_path_xpath(target_node, root)

    # Find position among matching nodes
    position = _find_position_in_matches(target_node, base_xpath, root)

    if position == 1:
        # If it's the only match, position is optional but we'll include it for consistency
        return f"({base_xpath})[1]"
    else:
        # Multiple matches - add position
        return f"({base_xpath})[{position}]"


def _build_attribute_xpath(node: Node) -> Optional[str]:
    """
    Build XPath using unique attributes.

    Priority:
    1. id attribute (most unique)
    2. name attribute
    3. aria-label
    4. combination of tag + type + other attributes
    """
    tag = node.tag
    attrs = node.attrib

    # 1. Try id attribute
    if 'id' in attrs:
        return f"//{tag}[@id='{attrs['id']}']"

    # 2. Try name attribute
    if 'name' in attrs:
        return f"//{tag}[@name='{attrs['name']}']"

    # 3. Try aria-label
    if 'aria-label' in attrs:
        return f"//{tag}[@aria-label='{attrs['aria-label']}']"

    # 4. Try combination of attributes
    if len(attrs) > 0:
        # Build predicate with multiple attributes
        predicates = [f"@{key}='{value}'" for key, value in attrs.items()]
        predicate_str = " and ".join(predicates[:3])  # Limit to 3 attributes
        return f"//{tag}[{predicate_str}]"

    # No unique attributes
    return None


def _build_path_xpath(target_node: Node, root: Node) -> str:
    """
    Build XPath using path from root.

    Example: /html/body/div[2]/form/button[1]

    Note: Without parent references, we build a simple tag-based path
    """
    # For simplicity, just use a tag + position based XPath
    # Find position among all nodes with same tag
    position = _find_position_by_tag(target_node, root)
    return f"(//{target_node.tag})[{position}]"


def _find_position_by_tag(target_node: Node, root: Node) -> int:
    """
    Find the position of target_node among all nodes with same tag.

    Returns:
        1-based position (1 if first match, 2 if second, etc.)
    """
    matches = []

    def traverse(node: Node):
        if node.tag == target_node.tag:
            matches.append(node)

        # Traverse children
        for child in node.children:
            if isinstance(child, Node):
                traverse(child)

    traverse(root)

    # Find position using object identity
    for i, match in enumerate(matches, start=1):
        if match is target_node:
            return i

    return 1


def _find_position_in_matches(target_node: Node, base_xpath: str, root: Node) -> int:
    """
    Find the position of target_node among all nodes that match base_xpath.

    Args:
        target_node: The Node we're looking for
        base_xpath: XPath like "//input[@name='btnK']"
        root: Root Node to search from

    Returns:
        1-based position (1 if first match, 2 if second, etc.)
    """
    # Find all matching nodes in document order
    matches = []

    def traverse(node: Node):
        # Check if this node matches
        if node.tag == target_node.tag:
            # Check if attributes match
            if _node_matches_attributes(node, target_node):
                matches.append(node)

        # Traverse children
        for child in node.children:
            if isinstance(child, Node):
                traverse(child)

    traverse(root)

    # Find position using object identity
    for i, match in enumerate(matches, start=1):
        if match is target_node:
            return i

    return 1


def _node_matches_attributes(node: Node, target_node: Node) -> bool:
    """
    Check if node has the same key attributes as target.

    Used to determine if a node would match the same XPath.
    """
    # Priority attributes for matching
    key_attrs = ['id', 'name', 'aria-label', 'type', 'role']

    node_attrs = node.attrib
    target_attrs = target_node.attrib

    # If target has 'id', only match on id
    if 'id' in target_attrs:
        return node_attrs.get('id') == target_attrs.get('id')

    # If target has 'name', match on name
    if 'name' in target_attrs:
        if node_attrs.get('name') != target_attrs.get('name'):
            return False

    # If target has 'aria-label', match on aria-label
    if 'aria-label' in target_attrs:
        if node_attrs.get('aria-label') != target_attrs.get('aria-label'):
            return False

    # Check if all target's key attributes match
    for attr in key_attrs:
        if attr in target_attrs:
            if node_attrs.get(attr) != target_attrs.get(attr):
                return False

    # If target has no key attributes, match on all attributes
    if not any(attr in target_attrs for attr in key_attrs):
        if len(node_attrs) == 0 and len(target_attrs) == 0:
            return True
        # Match on all attributes
        return node_attrs == target_attrs

    return True
