"""Generate XPath selectors from element IDs."""

from typing import Dict, Optional, List
from ..ir.dom_ir import DomTreeNode, DomElement
from ..ir.semantic_ir import SemanticElement


def generate_xpath(element_id: str, id_mapping: Dict[str, SemanticElement], dom_tree_node: DomTreeNode) -> Optional[str]:
    """
    Generate guaranteed unique XPath selector for an element ID.

    Args:
        element_id: Readable element ID from LLM (e.g., "button-1")
        id_mapping: Mapping from readable ID to SemanticElement
        dom_tree_node: DomTreeNode for the target element (has parent references!)

    Returns:
        XPath selector string (guaranteed unique), or None if element not found
    """
    # Build guaranteed unique XPath using dom_tree_node
    # (dom_tree_node.parent allows navigation to root!)
    return _build_unique_xpath(dom_tree_node, id_mapping)


def _build_unique_xpath(dom_tree_node: DomTreeNode, id_mapping: Dict[str, SemanticElement]) -> str:
    """
    Build guaranteed unique XPath using attributes + position.

    Strategy:
    1. Build attribute-based selector
    2. Find position among all matching nodes
    3. Add position to guarantee uniqueness: (//tag[@attr='value'])[position]
    """
    # Build base XPath with attributes
    base_xpath = _build_attribute_xpath(dom_tree_node)

    if not base_xpath:
        # No attributes - use path-based XPath (already unique)
        return _build_path_xpath(dom_tree_node)

    # Find root by walking up parent references
    root = dom_tree_node
    while root.parent is not None:
        root = root.parent

    # Find position among matching nodes
    position = _find_position_in_matches(dom_tree_node, base_xpath, root)

    if position == 1:
        # If it's the only match, position is optional but we'll include it for consistency
        # Or we could return base_xpath directly for cleaner output
        # For guaranteed uniqueness, always add position:
        return f"({base_xpath})[1]"
    else:
        # Multiple matches - add position
        return f"({base_xpath})[{position}]"


def _build_attribute_xpath(dom_tree_node: DomTreeNode) -> Optional[str]:
    """
    Build XPath using unique attributes.

    Priority:
    1. id attribute (most unique)
    2. name attribute
    3. aria-label
    4. combination of tag + type + other attributes
    """
    if not isinstance(dom_tree_node.data, DomElement):
        return None

    element = dom_tree_node.data
    tag = element.tag
    attrs = element.attributes

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


def _build_path_xpath(dom_tree_node: DomTreeNode) -> str:
    """
    Build XPath using path from root.

    Example: /html/body/div[2]/form/button[1]

    Uses DomTreeNode.parent for efficient navigation!
    """
    if not isinstance(dom_tree_node.data, DomElement):
        return ""

    path_parts = []
    current = dom_tree_node

    # Walk up to root using parent references (O(depth) instead of O(n)!)
    while current is not None:
        if isinstance(current.data, DomElement):
            element = current.data
            parent = current.parent

            if parent is not None:
                # Count siblings of same tag
                sibling_index = _get_sibling_index(current, parent)
                if sibling_index > 1:
                    path_parts.insert(0, f"{element.tag}[{sibling_index}]")
                else:
                    path_parts.insert(0, element.tag)
            else:
                # Root element
                path_parts.insert(0, element.tag)

        current = current.parent

    return "/" + "/".join(path_parts)


def _find_position_in_matches(target_dom_tree_node: DomTreeNode, base_xpath: str, root: DomTreeNode) -> int:
    """
    Find the position of target_dom_tree_node among all nodes that match base_xpath.

    Args:
        target_dom_tree_node: The DOM tree node we're looking for
        base_xpath: XPath like "//input[@name='btnK']"
        root: Root DomTreeNode to search from

    Returns:
        1-based position (1 if first match, 2 if second, etc.)
    """
    if not isinstance(target_dom_tree_node.data, DomElement):
        return 1

    target_element = target_dom_tree_node.data

    # Find all matching nodes in document order
    matches = []

    def traverse(tree_node: DomTreeNode):
        if isinstance(tree_node.data, DomElement):
            # Check if this node matches
            if tree_node.data.tag == target_element.tag:
                # Check if attributes match
                matches_attrs = _node_matches_attributes(tree_node, target_dom_tree_node)
                if matches_attrs:
                    matches.append(tree_node)

            # Traverse children
            for child in tree_node.children:
                traverse(child)

    traverse(root)

    # Find position of target_dom_tree_node in matches (using object identity!)
    for i, match in enumerate(matches, start=1):
        if match is target_dom_tree_node:  # Direct object comparison!
            return i

    # Should never happen, but fallback to 1
    return 1


def _node_matches_attributes(dom_tree_node: DomTreeNode, target_dom_tree_node: DomTreeNode) -> bool:
    """
    Check if node has the same key attributes as target.

    Used to determine if a node would match the same XPath.
    """
    if not isinstance(dom_tree_node.data, DomElement) or not isinstance(target_dom_tree_node.data, DomElement):
        return False

    node_element = dom_tree_node.data
    target_element = target_dom_tree_node.data

    # Priority attributes for matching
    key_attrs = ['id', 'name', 'aria-label', 'type', 'role']

    # If target has 'id', only match on id
    if 'id' in target_element.attributes:
        return node_element.attributes.get('id') == target_element.attributes.get('id')

    # If target has 'name', match on name
    if 'name' in target_element.attributes:
        if node_element.attributes.get('name') != target_element.attributes.get('name'):
            return False

    # If target has 'aria-label', match on aria-label
    if 'aria-label' in target_element.attributes:
        if node_element.attributes.get('aria-label') != target_element.attributes.get('aria-label'):
            return False

    # Check if all target's key attributes match
    for attr in key_attrs:
        if attr in target_element.attributes:
            if node_element.attributes.get(attr) != target_element.attributes.get(attr):
                return False

    # If target has no key attributes, match on all attributes
    if not any(attr in target_element.attributes for attr in key_attrs):
        if len(node_element.attributes) == 0 and len(target_element.attributes) == 0:
            return True
        # Match on all attributes
        return node_element.attributes == target_element.attributes

    return True


def _get_sibling_index(dom_tree_node: DomTreeNode, parent_dom_tree_node: DomTreeNode) -> int:
    """
    Get the index of node among siblings with same tag.

    Returns 1-based index (XPath convention).
    """
    if not isinstance(dom_tree_node.data, DomElement):
        return 1

    node_element = dom_tree_node.data

    # Get all element siblings with same tag
    same_tag_siblings = [
        child for child in parent_dom_tree_node.children
        if isinstance(child.data, DomElement) and child.data.tag == node_element.tag
    ]

    # Find position using object identity
    for i, sibling in enumerate(same_tag_siblings, start=1):
        if sibling is dom_tree_node:  # Direct object comparison!
            return i

    return 1
