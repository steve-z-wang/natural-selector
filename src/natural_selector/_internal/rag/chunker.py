"""Chunk Semantic IR into markdown pieces with context."""

from typing import List, Dict, Tuple
from dataclasses import dataclass
import tiktoken
from ..ir.nodes import ElementNode, TextNode, IR, Node


@dataclass
class FlatItem:
    """Flattened representation of a node for chunking."""
    node: Node  # The actual node
    depth: int  # Indentation depth
    path: List[str]  # Ancestor node IDs (e.g., ["body-1", "div-1", "form-1"])
    markdown: str  # The markdown line for this node


def flatten_ir(ir: IR) -> List[FlatItem]:
    """
    Flatten IR tree into a list of (node, depth, path, markdown).

    Args:
        ir: Semantic IR with tag_ids assigned

    Returns:
        List of FlatItem objects
    """
    items = []

    def traverse(node: Node, depth: int, path: List[str]):
        if isinstance(node, TextNode):
            # Text node
            indent = "  " * depth
            markdown = f'{indent}- "{node.text.strip()}"'
            items.append(FlatItem(
                node=node,
                depth=depth,
                path=path.copy(),
                markdown=markdown
            ))

        elif isinstance(node, ElementNode):
            # Element node
            indent = "  " * depth

            # Generate node ID
            if node.tag_id is not None:
                node_id = f"{node.tag}-{node.tag_id}"
            else:
                node_id = node.tag

            # Format markdown
            if node.attributes:
                attrs_str = " ".join(f'{k}="{v}"' for k, v in node.attributes.items())
                markdown = f"{indent}- {node_id} ({attrs_str})"
            else:
                markdown = f"{indent}- {node_id}"

            items.append(FlatItem(
                node=node,
                depth=depth,
                path=path.copy(),
                markdown=markdown
            ))

            # Traverse children
            new_path = path + [node_id]
            for child in node.children:
                traverse(child, depth + 1, new_path)

    traverse(ir.root, depth=0, path=[])
    return items


def chunk_ir(
    ir: IR,
    max_tokens: int = 500,
    overlap_tokens: int = 50,
    encoding_name: str = "cl100k_base"
) -> List[Dict]:
    """
    Chunk IR into markdown pieces with path context.

    Args:
        ir: Semantic IR with tag_ids assigned
        max_tokens: Maximum tokens per chunk
        overlap_tokens: Overlap between chunks
        encoding_name: Tokenizer encoding

    Returns:
        List of chunk dictionaries with markdown and metadata
    """
    # Flatten IR
    items = flatten_ir(ir)
    encoding = tiktoken.get_encoding(encoding_name)

    chunks = []
    start = 0

    while start < len(items):
        end = start
        tokens = 0

        # Walk until near limit
        while end < len(items):
            line_tokens = len(encoding.encode(items[end].markdown))
            if tokens + line_tokens > max_tokens and end > start:
                break
            tokens += line_tokens
            end += 1

        # Create chunk
        chunk_items = items[start:end]

        # Build markdown with path placeholders
        lines = []

        # Add path placeholders if not at start
        if start > 0 and chunk_items:
            first_item = chunk_items[0]
            for i, ancestor_id in enumerate(first_item.path):
                indent = "  " * i
                lines.append(f"{indent}- [{ancestor_id} ...]")

        # Add actual content
        lines.extend([item.markdown for item in chunk_items])

        # Add continuation indicator if not at end
        if end < len(items):
            last_depth = chunk_items[-1].depth
            indent = "  " * last_depth
            lines.append(f"{indent}- [... content continues ...]")

        markdown_text = "\n".join(lines)

        chunks.append({
            "markdown": markdown_text,
            "tokens": tokens,
            "start_index": start,
            "end_index": end,
            "item_count": len(chunk_items)
        })

        # Move pointer with overlap
        # Calculate overlap items (approximate)
        if end >= len(items):
            break

        overlap_count = 0
        overlap_tok = 0
        for i in range(end - 1, start - 1, -1):
            item_tokens = len(encoding.encode(items[i].markdown))
            if overlap_tok + item_tokens > overlap_tokens:
                break
            overlap_tok += item_tokens
            overlap_count += 1

        start = end - max(overlap_count, 1)

    return chunks
