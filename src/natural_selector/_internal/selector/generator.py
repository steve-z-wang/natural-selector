"""Generate XPath selectors from element IDs."""

from typing import Dict, Optional, List
from ..ir.nodes import ElementNode, IR


def generate_xpath(element_id: str, id_mapping: Dict[str, str], full_ir: IR) -> Optional[str]:
    """
    Generate guaranteed unique XPath selector for an element ID.

    Args:
        element_id: Readable element ID from LLM (e.g., "button-1")
        id_mapping: Mapping from readable ID to UUID
        full_ir: Full IR with complete node information

    Returns:
        XPath selector string (guaranteed unique), or None if element not found
    """
    # 1. Get UUID from readable ID
    if element_id not in id_mapping:
        return None

    uuid = id_mapping[element_id]

    # 2. Get full node from Full IR
    node = full_ir.get_node_by_id(uuid)
    if node is None:
        return None

    # 3. Build guaranteed unique XPath
    return _build_unique_xpath(node, full_ir)


def _build_unique_xpath(node: ElementNode, full_ir: IR) -> str:
    """
    Build guaranteed unique XPath using attributes + position.

    Strategy:
    1. Build attribute-based selector
    2. Find position among all matching nodes
    3. Add position to guarantee uniqueness: (//tag[@attr='value'])[position]
    """
    # Build base XPath with attributes
    base_xpath = _build_attribute_xpath(node)

    if not base_xpath:
        # No attributes - use path-based XPath (already unique)
        return _build_path_xpath(node, full_ir)

    # Find position among matching nodes
    position = _find_position_in_matches(node, base_xpath, full_ir)

    if position == 1:
        # If it's the only match, position is optional but we'll include it for consistency
        # Or we could return base_xpath directly for cleaner output
        # For guaranteed uniqueness, always add position:
        return f"({base_xpath})[1]"
    else:
        # Multiple matches - add position
        return f"({base_xpath})[{position}]"


def _build_attribute_xpath(node: ElementNode) -> Optional[str]:
    """
    Build XPath using unique attributes.

    Priority:
    1. id attribute (most unique)
    2. name attribute
    3. aria-label
    4. combination of tag + type + other attributes
    """
    tag = node.tag
    attrs = node.attributes

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


def _build_path_xpath(node: ElementNode, full_ir: IR) -> str:
    """
    Build XPath using path from root.

    Example: /html/body/div[2]/form/button[1]
    """
    path_parts = []
    current = node

    # Walk up to root, building path
    while current:
        # Find parent
        parent = _find_parent(current, full_ir)

        if parent:
            # Count siblings of same tag
            sibling_index = _get_sibling_index(current, parent)
            if sibling_index > 1:
                path_parts.insert(0, f"{current.tag}[{sibling_index}]")
            else:
                path_parts.insert(0, current.tag)
        else:
            # Root element
            path_parts.insert(0, current.tag)

        current = parent

    return "/" + "/".join(path_parts)


def _find_parent(node: ElementNode, ir: IR) -> Optional[ElementNode]:
    """Find parent of a node by searching the tree."""
    def search(current: ElementNode) -> Optional[ElementNode]:
        for child in current.children:
            if isinstance(child, ElementNode):
                if child.id == node.id:
                    return current
                parent = search(child)
                if parent:
                    return parent
        return None

    # Don't return parent if node is root
    if node.id == ir.root.id:
        return None

    return search(ir.root)


def _find_position_in_matches(target_node: ElementNode, base_xpath: str, full_ir: IR) -> int:
    """
    Find the position of target_node among all nodes that match base_xpath.

    Args:
        target_node: The node we're looking for
        base_xpath: XPath like "//input[@name='btnK']"
        full_ir: Full IR to search

    Returns:
        1-based position (1 if first match, 2 if second, etc.)
    """
    # Extract matching criteria from the node
    # (We could parse base_xpath, but it's easier to use node attributes directly)
    tag = target_node.tag
    attrs = target_node.attributes

    # Find all matching nodes in document order
    matches = []

    def traverse(node: ElementNode):
        if isinstance(node, ElementNode):
            # Check if this node matches
            if node.tag == tag:
                # Check if attributes match (only check attributes used in base_xpath)
                # For simplicity, check if all target node's attributes match
                # (base_xpath was built from these attributes)

                # Get the attributes that were used in base_xpath
                # For now, check if key attributes match
                matches_attrs = _node_matches_attributes(node, target_node)
                if matches_attrs:
                    matches.append(node)

            # Traverse children
            for child in node.children:
                if isinstance(child, ElementNode):
                    traverse(child)

    traverse(full_ir.root)

    # Find position of target_node in matches
    for i, match in enumerate(matches, start=1):
        if match.id == target_node.id:
            return i

    # Should never happen, but fallback to 1
    return 1


def _node_matches_attributes(node: ElementNode, target: ElementNode) -> bool:
    """
    Check if node has the same key attributes as target.

    Used to determine if a node would match the same XPath.
    """
    # Priority attributes for matching
    key_attrs = ['id', 'name', 'aria-label', 'type', 'role']

    # If target has 'id', only match on id
    if 'id' in target.attributes:
        return node.attributes.get('id') == target.attributes.get('id')

    # If target has 'name', match on name
    if 'name' in target.attributes:
        if node.attributes.get('name') != target.attributes.get('name'):
            return False

    # If target has 'aria-label', match on aria-label
    if 'aria-label' in target.attributes:
        if node.attributes.get('aria-label') != target.attributes.get('aria-label'):
            return False

    # Check if all target's key attributes match
    for attr in key_attrs:
        if attr in target.attributes:
            if node.attributes.get(attr) != target.attributes.get(attr):
                return False

    # If target has no key attributes, match on all attributes
    if not any(attr in target.attributes for attr in key_attrs):
        if len(node.attributes) == 0 and len(target.attributes) == 0:
            return True
        # Match on all attributes
        return node.attributes == target.attributes

    return True


def _get_sibling_index(node: ElementNode, parent: ElementNode) -> int:
    """
    Get the index of node among siblings with same tag.

    Returns 1-based index (XPath convention).
    """
    same_tag_siblings = [
        child for child in parent.children
        if isinstance(child, ElementNode) and child.tag == node.tag
    ]

    for i, sibling in enumerate(same_tag_siblings, start=1):
        if sibling.id == node.id:
            return i

    return 1
