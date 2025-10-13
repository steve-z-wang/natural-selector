"""Semantic filter passes."""

from .filter_by_tags import filter_by_tags_pass
from .filter_by_attributes import filter_by_attributes_pass
from .filter_empty_nodes import filter_empty_nodes_pass
from .collapse_wrappers import collapse_wrappers_pass

__all__ = [
    "filter_by_tags_pass",
    "filter_by_attributes_pass",
    "filter_empty_nodes_pass",
    "collapse_wrappers_pass"
]
