"""Visibility filtering: DomIR → DomIR (filtered).

Multiple passes to filter invisible elements:
1. Pass 1: Remove non-visible tags (script, style, head, etc.)
2. Pass 2: Remove CSS-hidden elements (display:none, visibility:hidden, opacity:0)
3. Pass 3: Remove zero-dimension elements that have no visible children

Key improvement: Pass 3 uses bottom-up filtering, keeping zero-dimension containers
if they have visible children (e.g., absolutely positioned popup dialogs).
"""

from typing import Optional
from ..ir.dom_ir import DomIR
from .visibility.non_visible_tags import filter_non_visible_tags_pass
from .visibility.css_hidden import filter_css_hidden_pass
from .visibility.zero_dimensions import filter_zero_dimensions_pass


def visibility_pass(dom_ir: DomIR) -> Optional[DomIR]:
    """
    Apply multiple visibility filtering passes.

    Pass 1: Remove non-visible tags
    Pass 2: Remove CSS-hidden elements
    Pass 3: Remove zero-dimension elements without visible children

    Args:
        dom_ir: DomIR with complete tree

    Returns:
        DomIR: Filtered DomIR with only visible elements, or None if empty
    """
    # Pass 1: Remove non-visible tags
    root = filter_non_visible_tags_pass(dom_ir.root)
    if root is None:
        return None

    # Pass 2: Remove CSS-hidden elements
    root = filter_css_hidden_pass(root)
    if root is None:
        return None

    # Pass 3: Remove zero-dimension elements without visible children
    root = filter_zero_dimensions_pass(root)
    if root is None:
        return None

    return DomIR(root)
