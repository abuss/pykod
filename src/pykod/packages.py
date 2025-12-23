"""Locale configuration."""

from typing import Any, override

from pykod.base import NestedDict


def Packages(pkgs):
    """Factory function for Packages."""
    # print("Creating Packages with:", pkgs)
    return pkgs


# class Packages(NestedDict):
#     """Represents fonts."""

#     def __init__(self, **kwargs):
#         """Initialize fonts."""
#         super().__init__(**kwargs)

#     def install(self, _config):
#         """Creates fonts and settings."""
#         print("\n\n[install] font_dir:", self.font_dir)
#         print("Font packages:")
#         for key, extra in self.packages.items():
#             print(f"  {key}: {extra}")

#     def rebuild(self):
#         print("[rebuild] Updating fonts:", self.packages)
