"""Desktop environment manager."""

from dataclasses import dataclass, field
from pickletools import dis
from typing import Optional

from pykod.base import NestedDict
from pykod.repositories.base import PackageList
from pykod.service import Service


@dataclass
class DesktopEnvironment:
    """Desktop environment configuration.

    Args:
        enable: Whether to enable this desktop environment
        display_manager: Display manager to use (e.g., 'gdm', 'sddm')
        extra_packages: Additional packages to install
        exclude_packages: Packages to exclude from default installation
    """

    enable: bool
    package: PackageList | None
    display_manager: str | None = None
    extra_packages: PackageList = field(default_factory=PackageList)
    exclude_packages: PackageList = field(default_factory=PackageList)

    def __post_init__(self):
        """Post-initialization processing."""
        if not self.enable:
            self.package = None
            self.extra_packages = None
            self.exclude_packages = None


# class DesktopManager(NestedDict):
@dataclass
class DesktopManager:
    """Desktop environment manager configuration.

    This class provides a flexible way to configure multiple desktop environments
    and window managers using a dynamic environments dictionary.

    Args:
        environments: Dictionary of environment name to DesktopEnvironment configuration
        default_display_manager: Default display manager to use if not specified per environment

    Example Usage:
        # Traditional desktop environments
        DesktopManager(environments={
            'gnome': DesktopEnvironment(enable=True, display_manager="gdm"),
            'plasma': DesktopEnvironment(enable=False, display_manager="sddm"),
            'cosmic': DesktopEnvironment(enable=True, display_manager="cosmic-greeter")
        })

        # Modern window managers and compositors
        DesktopManager(environments={
            'hyprland': DesktopEnvironment(enable=True, display_manager="greetd"),
            'sway': DesktopEnvironment(enable=False, display_manager="greetd"),
            'i3': DesktopEnvironment(enable=False, display_manager="lightdm")
        })
    """

    display_manager: Service
    environments: dict[str, DesktopEnvironment] = field(default_factory=dict)

    # def __init__(self, **kwargs):
    #     """Initialize desktop manager."""
    #     super().__init__(**kwargs)
    #     self.environments: dict[str, DesktopEnvironment]
    #     self.display_manager: Service | None = kwargs.get("display_manager", None)

    def install(self, _config):
        """Creating a Desktop manager."""
        print("\n[install] Environments:")
        for key, extra in self.environments.items():
            print(f" - {key}: {extra}")

    def rebuild(self):
        print("[rebuild] Updating environments:")
        for key, extra in self.environments.items():
            print(f" - {key}: {extra}")
