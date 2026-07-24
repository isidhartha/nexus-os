"""NexusOS core package."""

from pathlib import Path as _Path
from dotenv import load_dotenv as _load_dotenv
_load_dotenv(_Path(__file__).parent.parent / ".env")

from .nexus import NexusOS, get_nexus

__all__ = ["NexusOS", "get_nexus"]
