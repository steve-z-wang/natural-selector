"""Natural-Selector: Natural language browser automation."""

from .session import Session
from .page import Page
from .element import SelectedElement
from .interfaces import Embedder, LLM
from . import utils

__version__ = "0.1.0"
__all__ = ["Session", "Page", "SelectedElement", "Embedder", "LLM", "utils"]
