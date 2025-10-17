"""Intermediate Representation (IR) for DOM trees."""

from .dom_ir import DomElement, DomText, DomTreeNode, DomIR, BoundingBox
from .semantic_ir import SemanticElement, SemanticText, SemanticTreeNode, SemanticIR

__all__ = [
    # DOM IR
    "DomElement",
    "DomText",
    "DomTreeNode",
    "DomIR",
    "BoundingBox",
    # Semantic IR
    "SemanticElement",
    "SemanticText",
    "SemanticTreeNode",
    "SemanticIR",
]
