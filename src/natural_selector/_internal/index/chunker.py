"""Create chunks from Semantic IR with markdown and context."""

from typing import List, Optional
from dataclasses import dataclass
from domcontext._internal.ir.semantic_ir import SemanticIR
from domcontext._internal.chunker import chunk_semantic_ir
from domcontext.tokenizer import TiktokenTokenizer


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

    Uses domcontext's chunker implementation.

    Args:
        semantic_ir: SemanticIR with semantic elements and readable IDs
        max_tokens: Maximum tokens per chunk
        overlap_tokens: Overlap between chunks
        encoding_name: Tokenizer encoding (currently ignored, uses cl100k_base)

    Returns:
        List of Chunk objects with markdown and token count
    """
    # Use domcontext's chunker
    tokenizer = TiktokenTokenizer()
    dom_chunks = chunk_semantic_ir(
        semantic_ir,
        tokenizer=tokenizer,
        size=max_tokens,
        overlap=overlap_tokens,
        include_parent_path=True
    )

    # Convert to natural-selector's Chunk format (adds embedding field)
    return [
        Chunk(markdown=c.markdown, tokens=c.tokens, embedding=None)
        for c in dom_chunks
    ]
