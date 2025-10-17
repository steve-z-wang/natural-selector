"""Create chunks from Semantic IR with markdown and context."""

from typing import List, Optional
from dataclasses import dataclass
import tiktoken
from ..ir.semantic_ir import SemanticIR


@dataclass
class Chunk:
    """A chunk of markdown text with optional embedding."""
    markdown: str
    tokens: int
    embedding: Optional[List[float]] = None


def create_chunks(
    semantic_ir: SemanticIR,
    max_tokens: int = 500,
    overlap_tokens: int = 50,
    encoding_name: str = "cl100k_base"
) -> List[Chunk]:
    """
    Create chunks from SemanticIR with markdown and path context.

    Directly uses SemanticIR.dfs(with_path=True) - no intermediate flattening.

    Args:
        semantic_ir: SemanticIR with semantic elements and readable IDs
        max_tokens: Maximum tokens per chunk
        overlap_tokens: Overlap between chunks
        encoding_name: Tokenizer encoding

    Returns:
        List of Chunk objects with markdown and token count
    """
    # Collect all items from DFS traversal
    items = []
    for node, depth, path in semantic_ir.dfs(with_path=True):
        indent = "  " * depth
        markdown = f"{indent}- {node.data.to_markdown()}"
        items.append((node, depth, path, markdown))

    encoding = tiktoken.get_encoding(encoding_name)
    chunks = []
    start = 0

    while start < len(items):
        end = start
        tokens = 0

        # Walk until near limit
        while end < len(items):
            _, _, _, markdown = items[end]
            line_tokens = len(encoding.encode(markdown))
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
            _, _, first_path, _ = chunk_items[0]
            for i, ancestor_id in enumerate(first_path):
                indent = "  " * i
                lines.append(f"{indent}- [{ancestor_id} ...]")

        # Add actual content
        lines.extend([markdown for _, _, _, markdown in chunk_items])

        # Add continuation indicator if not at end
        if end < len(items):
            _, last_depth, _, _ = chunk_items[-1]
            indent = "  " * last_depth
            lines.append(f"{indent}- [... content continues ...]")

        markdown_text = "\n".join(lines)

        chunks.append(Chunk(
            markdown=markdown_text,
            tokens=tokens
        ))

        # Move pointer with overlap
        if end >= len(items):
            break

        overlap_count = 0
        overlap_tok = 0
        for i in range(end - 1, start - 1, -1):
            _, _, _, markdown = items[i]
            item_tokens = len(encoding.encode(markdown))
            if overlap_tok + item_tokens > overlap_tokens:
                break
            overlap_tok += item_tokens
            overlap_count += 1

        start = end - max(overlap_count, 1)

    return chunks
