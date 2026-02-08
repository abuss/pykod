"""Package repository configurations.

This module provides repository configuration classes for different package systems
including Arch Linux repositories, Debian/Ubuntu, AUR, and Flatpak.
"""

from .arch import Arch
from .aur import AUR
from .base import BaseSystemRepository, Repository
from .debian import Debian
from .flatpak import Flatpak

__all__ = [
    "Repository",
    "BaseSystemRepository",
    "Arch",
    "Debian",
    "AUR",
    "Flatpak",
]
