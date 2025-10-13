"""Create mapping from readable IDs to UUIDs."""

from typing import Dict
from ..ir.nodes import ElementNode, IR


def create_id_mapping(semantic_ir: IR) -> Dict[str, str]:
    """
    Create mapping from readable IDs (tag-id) to UUIDs.

    Args:
        semantic_ir: Semantic IR with tag_ids assigned

    Returns:
        Dict mapping "tag-id" -> node.id (UUID)
        Example: {"button-1": "uuid-123", "input-2": "uuid-456"}
    """
    id_mapping = {}

    def traverse(node):
        if isinstance(node, ElementNode):
            # Create readable ID
            if node.tag_id is not None:
                readable_id = f"{node.tag}-{node.tag_id}"
                id_mapping[readable_id] = node.id

            # Traverse children
            for child in node.children:
                traverse(child)

    traverse(semantic_ir.root)
    return id_mapping
