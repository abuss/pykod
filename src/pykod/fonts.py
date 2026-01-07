"""Locale configuration."""

from typing import Any, override

from pykod.base import NestedDict


class Fonts(NestedDict):
    """Represents fonts."""

    def __init__(self, **kwargs):
        """Initialize fonts."""
        super().__init__(**kwargs)

    def install(self, _config):
        """Creates fonts and settings."""
        print("\n\n[install] font_dir:", self.font_dir)
        print(f"Font packages: {self.packages}")

    def rebuild(self):
        print("[rebuild] Updating fonts:", self.packages)
