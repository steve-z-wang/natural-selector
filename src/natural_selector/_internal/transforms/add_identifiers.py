"""Add LLM-friendly identifiers to Semantic IR.

Assigns tag_id numbers to each ElementNode for easy LLM reference.
Example: button-1, button-2, div-1, div-2, etc.
"""

from typing import Dict
from ..ir.nodes import ElementNode, TextNode, IR


def add_identifiers_pass(semantic_ir: IR) -> IR:
    """
    Add tag_id to each ElementNode for LLM-friendly identifiers.

    Assigns sequential numbers per tag type:
    - First button gets tag_id=1 (button-1)
    - Second button gets tag_id=2 (button-2)
    - First div gets tag_id=1 (div-1)
    - etc.

    Args:
        semantic_ir: Semantic IR to add identifiers to

    Returns:
        IR: Same IR with tag_ids assigned (mutated in-place)
    """
    # Counter for each tag type
    tag_counters: Dict[str, int] = {}

    def assign_ids(node):
        if isinstance(node, ElementNode):
            # Get current count for this tag
            if node.tag not in tag_counters:
                tag_counters[node.tag] = 0

            # Increment and assign
            tag_counters[node.tag] += 1
            node.tag_id = tag_counters[node.tag]

            # Process children
            for child in node.children:
                assign_ids(child)

    # Start from root
    assign_ids(semantic_ir.root)

    return semantic_ir
