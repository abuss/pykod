"""Package repository configurations.

This module provides repository configuration classes for different package systems
including Arch Linux, Debian/Ubuntu, and auxiliary package sources (AUR, Flatpak,
PPA, Snap).

Repository Types:
----------------
Base System Repositories (can bootstrap OS):
- Arch: Arch Linux official repositories
- Debian: Debian/Ubuntu repositories (variant-aware)

Auxiliary Repositories (package-only):
- AUR: Arch User Repository (Arch-specific)
- Flatpak: Cross-distribution flatpak packages
- PPA: Ubuntu Personal Package Archives (Ubuntu-specific)
- Snap: Universal snap packages (Canonical)

Usage:
-----
Mix and match repositories as needed:
    >>> from pykod.repositories import Debian, PPA, Snap, Flatpak
    >>>
    >>> ubuntu = Debian(release="noble", variant="ubuntu")
    >>> ppa = PPA(repo="ppa:graphics-drivers/ppa")
    >>> snap = Snap()
    >>> flatpak = Flatpak(hub_url="flathub")
    >>>
    >>> conf.packages = Packages(
    >>>     ubuntu["git", "vim"],
    >>>     ppa["nvidia-driver-550"],
    >>>     snap["spotify"],
    >>>     flatpak["org.gimp.GIMP"]
    >>> )
"""

from .arch import Arch
from .aur import AUR
from .base import BaseSystemRepository, Repository
from .debian import Debian
from .flatpak import Flatpak
from .ppa import PPA
from .snap import Snap

__all__ = [
    "Repository",
    "BaseSystemRepository",
    "Arch",
    "Debian",
    "AUR",
    "Flatpak",
    "PPA",
    "Snap",
]
