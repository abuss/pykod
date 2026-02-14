#!/usr/bin/env python3
"""
Enhanced Desktop Configuration Examples
======================================

This file demonstrates the dynamic desktop environment capabilities
in pykod, showing how to configure modern window managers and Wayland
compositors using DesktopManager directly.

Key Features:
- Direct DesktopManager usage (no wrapper classes)
- Unified environments dictionary for all desktop environments
- Support for Wayland compositors (Hyprland, Sway, River)
- Support for X11 window managers (i3, BSPWM, Awesome, DWM)
- Flexible display manager configuration per environment
- Dynamic runtime environment management
- Clean, consistent API for all desktop environments
"""

import sys

sys.path.insert(0, "src")

from pykod.section import DesktopManager, DesktopEnvironment


def example_modern_wayland_setup():
    """Example: Modern Wayland compositor setup with Hyprland."""

    print("=== Modern Wayland Compositor Setup ===")

    desktop_manager = DesktopManager(
        environments={
            "hyprland": DesktopEnvironment(
                enable=True,
                display_manager="greetd",
                extra_packages=[
                    "hyprland",  # The compositor itself
                    "hyprpaper",  # Wallpaper daemon
                    "waybar",  # Status bar
                    "wofi",  # Application launcher
                    "dunst",  # Notification daemon
                    "grim",  # Screenshot tool
                    "slurp",  # Screen selection
                    "wl-clipboard",  # Clipboard manager
                    "swaylock",  # Screen locker
                    "swayidle",  # Idle daemon
                    "foot",  # Terminal emulator
                    "thunar",  # File manager
                ],
            )
        }
    )

    return desktop_manager


def example_tiling_window_manager():
    """Example: Traditional X11 tiling window manager setup."""

    print("=== X11 Tiling Window Manager Setup ===")

    desktop_manager = DesktopManager(
        environments={
            "i3": DesktopEnvironment(
                enable=True,
                display_manager="lightdm",
                extra_packages=[
                    "i3-wm",  # Window manager
                    "i3lock",  # Screen locker
                    "i3status",  # Status bar
                    "dmenu",  # Application launcher
                    "rofi",  # Alternative launcher
                    "feh",  # Wallpaper setter
                    "scrot",  # Screenshot tool
                    "picom",  # Compositor for effects
                    "alacritty",  # Terminal emulator
                    "ranger",  # File manager
                ],
            ),
            "bspwm": DesktopEnvironment(
                enable=False,  # Available but not active
                display_manager="lightdm",
                extra_packages=[
                    "bspwm",  # Window manager
                    "sxhkd",  # Hotkey daemon
                    "polybar",  # Status bar
                    "rofi",  # Application launcher
                    "feh",  # Wallpaper setter
                    "scrot",  # Screenshot tool
                    "picom",  # Compositor
                    "alacritty",  # Terminal
                ],
            ),
        }
    )

    return desktop_manager


def example_multi_environment_setup():
    """Example: Multiple environments for different use cases."""

    print("=== Multi-Environment Setup ===")

    desktop_manager = DesktopManager(
        environments={
            # Traditional desktop for productivity
            "gnome": DesktopEnvironment(
                enable=True,
                display_manager="gdm",
                extra_packages=[
                    "gnome-tweaks",
                    "gnome-shell-extension-appindicator",
                    "aur:gnome-shell-extension-dash-to-dock",
                ],
            ),
            # Gaming setup with minimal overhead
            "gaming": DesktopEnvironment(
                enable=False,
                display_manager="ly",
                extra_packages=[
                    "openbox",  # Lightweight WM
                    "tint2",  # Minimal panel
                    "steam",  # Gaming platform
                    "gamemode",  # Gaming optimizations
                    "mangohud",  # Performance overlay
                ],
            ),
            # Development environment with tiling
            "development": DesktopEnvironment(
                enable=False,
                display_manager="greetd",
                extra_packages=[
                    "sway",  # Wayland compositor
                    "waybar",  # Status bar
                    "foot",  # Terminal
                    "emacs-wayland",  # Editor
                    "firefox-wayland",  # Browser
                    "wl-clipboard",  # Clipboard
                ],
            ),
            # Kiosk mode for dedicated applications
            "kiosk": DesktopEnvironment(
                enable=False,
                display_manager="nodm",  # Auto-login
                extra_packages=[
                    "cage",  # Wayland kiosk compositor
                    "firefox",  # Kiosk application
                ],
            ),
        }
    )

    return desktop_manager


def example_mixed_compatibility():
    """Example: Using the new dictionary-only configuration approach."""

    print("=== Dictionary-Only Configuration Example ===")

    # All desktop environments now use the environments dictionary
    desktop_manager = DesktopManager(
        environments={
            # Traditional desktop environments
            "gnome": DesktopEnvironment(enable=True, display_manager="gdm"),
            "plasma": DesktopEnvironment(enable=False, display_manager="sddm"),
            # Modern Wayland compositors
            "hyprland": DesktopEnvironment(
                enable=False,
                display_manager="greetd",
                extra_packages=["hyprland", "waybar", "wofi"],
            ),
            "river": DesktopEnvironment(
                enable=False,
                display_manager="greetd",
                extra_packages=["river", "rivertile", "waybar"],
            ),
        }
    )

    # You can manipulate environments programmatically
    dm = desktop_manager

    # Add a new environment dynamically
    dm.add_environment(
        "dwm",
        DesktopEnvironment(
            enable=False,
            display_manager="startx",
            extra_packages=["dwm", "dmenu", "st"],
        ),
    )

    # Access via the environments dictionary
    print(f"GNOME enabled: {dm.environments['gnome'].enable}")
    print(f"Hyprland enabled: {dm.environments['hyprland'].enable}")
    print(f"Available environments: {list(dm.environments.keys())}")

    return desktop_manager


def demonstrate_dynamic_methods():
    """Demonstrate the new dynamic methods available."""

    print("=== Dynamic Methods Demonstration ===")

    dm = DesktopManager()

    # Add environments dynamically
    print("1. Adding environments...")
    dm.add_environment(
        "herbstluftwm",
        DesktopEnvironment(
            enable=True,
            display_manager="lightdm",
            extra_packages=["herbstluftwm", "polybar", "rofi"],
        ),
    )

    dm.add_environment(
        "qtile",
        DesktopEnvironment(
            enable=False,
            display_manager="lightdm",
            extra_packages=["qtile", "python-psutil"],
        ),
    )

    print(f"All environments: {list(dm.environments.keys())}")

    # Get only enabled environments
    print("2. Getting enabled environments...")
    enabled = dm.get_enabled_environments()
    print(f"Enabled environments: {list(enabled.keys())}")

    # Remove an environment
    print("3. Removing an environment...")
    dm.remove_environment("qtile")
    print(f"After removal: {list(dm.environments.keys())}")

    return dm


if __name__ == "__main__":
    print("Enhanced Desktop Configuration Examples")
    print("=====================================\\n")

    # Run all examples
    example_modern_wayland_setup()
    print()

    example_tiling_window_manager()
    print()

    example_multi_environment_setup()
    print()

    example_mixed_compatibility()
    print()

    demonstrate_dynamic_methods()
    print()

    print("✅ All examples completed successfully!")
    print("\nKey Benefits:")
    print("- Clean, unified dictionary-based API")
    print("- Support for any desktop environment or window manager")
    print("- Dynamic runtime environment management")
    print("- Flexible display manager configuration")
    print("- Consistent and maintainable configuration approach")
