"""Locale configuration."""

from typing import Any, override

from pykod.core import NestedDict


class Fonts(NestedDict):
    """Represents fonts."""

    def __init__(self, **kwargs):
        """Initialize fonts."""
        super().__init__(**kwargs)
