"""Transformation passes for filtering IR trees."""

from .visibility import visibility_pass
from .semantic import semantic_pass
from .add_identifiers import add_identifiers_pass

__all__ = ["visibility_pass", "semantic_pass", "add_identifiers_pass"]
