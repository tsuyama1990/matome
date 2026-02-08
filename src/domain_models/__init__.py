"""
Core domain models and configuration schemas for the Matome project.
This package contains Pydantic definitions used throughout the system.
"""

from .config import ProcessingConfig
from .manifest import Chunk, Document

__all__ = ["Chunk", "Document", "ProcessingConfig"]
