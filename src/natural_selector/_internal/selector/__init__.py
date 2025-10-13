"""Selector generation from element IDs."""

from .id_mapping import create_id_mapping
from .generator import generate_xpath

__all__ = ["create_id_mapping", "generate_xpath"]
