"""Serialize Semantic IR to tab-indented markdown format."""

from typing import Dict, Tuple
from ..ir.nodes import ElementNode, TextNode, IR


def serialize_to_markdown(ir: IR) -> Tuple[str, Dict[str, str]]:
    """
    Serialize Semantic IR to pure markdown bullet format.

    Format:
        - body-1
          - div-1 (role="navigation")
            - a-1
              - "About"
            - a-2
              - "Store"
          - button-1 (aria-label="close")

    Args:
        ir: Semantic IR with tag_ids assigned

    Returns:
        Tuple of (markdown_text, id_mapping)
        where id_mapping maps "tag-id" -> node.id (UUID)
    """
    lines = []
    id_mapping = {}  # "button-1" -> node.id (UUID)

    def serialize_node(node, depth: int):
        if isinstance(node, TextNode):
            # Text node: quoted string as bullet
            indent = "  " * depth  # 2 spaces per level
            text_line = f'{indent}- "{node.text.strip()}"'
            lines.append(text_line)

        elif isinstance(node, ElementNode):
            # Element node: - tag-id (attributes)
            indent = "  " * depth  # 2 spaces per level

            # Generate readable ID
            if node.tag_id is not None:
                readable_id = f"{node.tag}-{node.tag_id}"
            else:
                # Fallback if tag_id not assigned
                readable_id = node.tag

            # Format attributes
            if node.attributes:
                attrs_str = " ".join(f'{k}="{v}"' for k, v in node.attributes.items())
                node_line = f"{indent}- {readable_id} ({attrs_str})"
            else:
                node_line = f"{indent}- {readable_id}"

            lines.append(node_line)

            # Store mapping
            if node.tag_id is not None:
                id_mapping[readable_id] = node.id

            # Serialize children
            for child in node.children:
                serialize_node(child, depth + 1)

    # Start serialization from root
    serialize_node(ir.root, depth=0)

    markdown_text = "\n".join(lines)
    return markdown_text, id_mapping
