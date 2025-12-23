"""Locale configuration."""

from typing import Any

from pykod.base import NestedDict


class HardwareManager(NestedDict):
    """Hardware configuration processing."""

    def __init__(self, **kwargs):
        """Initialize Hardware."""
        super().__init__(**kwargs)

    def install(self, _config):
        """Configure and install hardware related."""
        print("\n\n[install] services")
        for key, extra in self.services.items():
            print(f"  {key}: {extra}")

    def rebuild(self):
        print("[rebuild] updating hardware settings:", self.services)
