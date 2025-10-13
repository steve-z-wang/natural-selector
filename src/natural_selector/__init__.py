"""Natural-Selector: Natural language browser automation."""

from .api import NaturalSelector
from .interfaces import Embedder, LLM
from . import utils

__version__ = "0.1.0"
__all__ = ["NaturalSelector", "Embedder", "LLM", "utils"]
