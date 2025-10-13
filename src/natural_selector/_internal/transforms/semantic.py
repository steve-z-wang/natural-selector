"""Semantic filtering: Visible IR → Semantic IR.

Four-pass filtering:
1. filter_by_tags: Remove excluded tags (script, style, head, etc.)
2. filter_by_attributes: Remove aria-hidden/role="presentation", keep only semantic attributes
3. filter_empty_nodes: Remove nodes with no attributes and no children
4. collapse_wrappers: Collapse single-child wrappers with no attributes
"""

from typing import Optional
from ..ir.nodes import IR
from .semantic_steps import (
    filter_by_tags_pass,
    filter_by_attributes_pass,
    filter_empty_nodes_pass,
    collapse_wrappers_pass
)


def semantic_pass(visible_ir: IR) -> Optional[IR]:
    """
    Create Semantic IR from Visible IR through four passes.

    Args:
        visible_ir: Visible IR with filtered tree

    Returns:
        IR: Semantic IR (IDs preserved), or None if empty
    """
    # Pass 1: Filter by tags
    root = filter_by_tags_pass(visible_ir.root)
    if root is None:
        return None

    # Pass 2: Filter by attributes
    root = filter_by_attributes_pass(root)
    if root is None:
        return None

    # Pass 3: Filter empty nodes
    root = filter_empty_nodes_pass(root)
    if root is None:
        return None

    # Pass 4: Collapse wrappers
    root = collapse_wrappers_pass(root)
    if root is None:
        return None

    return IR(root)
