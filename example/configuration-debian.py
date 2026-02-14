#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Pykod configuration for Debian system with GNOME desktop
# ------------------------------------------------------------
# Description: Debian installation with systemd-boot, BTRFS, and GNOME
# Author: Antal Buss
# Date: 2025-01-XX
# License: MIT
# Notes: This configuration uses Debian "stable" with systemd-boot and BTRFS
#        for atomic generations (same approach as Arch configuration).
# ------------------------------------------------------------

from pykod import *
from pykod.core import File, Source
from pykod.repositories import Debian, Flatpak
from pykod.repositories.debian import GPU_PACKAGES

# Initialize Debian repository
# Default: release="stable" (tracks current Debian stable)
debian = Debian()

# Or specify exact version:
# debian = Debian(release="bookworm")  # Debian 12
# debian = Debian(release="testing")   # Debian testing
#
# Repository components:
# - main:     Official Debian packages (default)
# - contrib:  Free software that depends on non-free software
# - non-free: Proprietary or non-DFSG software
#
# To enable contrib and non-free:
# debian = Debian(components=["main", "contrib", "non-free"])

flatpak = Flatpak(hub_url="flathub")

# Create configuration
conf = Configuration(base=debian, dry_run=True, debug=True, verbose=True)

# Disk configuration - same as Arch (BTRFS + generations)
conf.devices = Devices(
    disk0=Disk(
        device="/dev/vda",
        initialize=True,
        partitions=[
            Partition(name="efi", size="512M", type="esp"),
            Partition(name="root", size="100%", type="btrfs", mountpoint="/"),
        ],
    ),
)

# Boot configuration - systemd-boot (same as Arch)
conf.boot = Boot(
    kernel=Kernel(
        package=debian["linux-image-amd64"],  # Debian kernel package
        modules=[
            "xhci_pci",
            "ahci",
            "usbhid",
            "virtio_blk",
            "virtio_pci",
        ],
    ),
    loader=Loader(
        type="systemd-boot",  # Using systemd-boot on Debian
        timeout=10,
    ),
)

# Locale configuration
conf.locale = Locale(
    default="en_US.UTF-8 UTF-8",
    additional_locales=[
        "en_GB.UTF-8 UTF-8",
        "en_CA.UTF-8 UTF-8",
    ],
    extra_settings={
        "LC_TIME": "en_CA.UTF-8",
    },
    keymap="us",
    timezone="America/Edmonton",
)

# Network configuration
conf.network = Network(
    hostname="debian-box",
    settings={"ipv6": True},
)

# Hardware configuration with GPU support
conf.hardware = Hardware(
    gpu=debian[*GPU_PACKAGES["intel"]["base"]],  # Auto-detected or manual
    audio=debian["pipewire", "pipewire-alsa", "pipewire-pulse"],
)

# Desktop environment - GNOME
conf.desktop = DesktopManager(
    display_manager=Service(package=debian["gdm3"]),
    environments={
        "gnome": DesktopEnvironment(
            enable=True,
            package=debian["gnome-core"],  # Minimal GNOME
            exclude_packages=debian["gnome-games"],
            extra_packages=debian[
                "gnome-tweaks",
                "gnome-shell-extensions",
            ],
        ),
    },
)

# Fonts
conf.fonts = Fonts(
    font_dir=True,
    packages=debian[
        "fonts-noto",
        "fonts-noto-color-emoji",
        "fonts-liberation",
        "fonts-dejavu",
        "fonts-firacode",
    ],
)

# Users
conf.root = User(username="root", no_password=True, shell="/bin/bash")

conf.user = User(
    username="user",
    name="Debian User",
    shell="/usr/bin/bash",
    groups=["audio", "video", "users", "sudo"],
    allow_sudo=True,
    hashed_password="$6$MOkGLOzXlj0lIE2d$5sxAysiDyD/7ZfntgZaN3vJ48t.BMi2qwPxqjgVxGXKXrNlFxRvnO8uCvOlHaGW2pVDrjt0JLNR9GWH.2YT5j.",
)

# Packages
conf.packages = Packages(
    debian[
        "firefox-esr",  # Debian's Firefox package
        "git",
        "vim",
        "htop",
        "curl",
        "wget",
        "build-essential",  # Debian's equivalent of base-devel
        "flatpak",
        "thunderbird",
    ]
)

# System services
conf.services = Services(
    {
        "networkmanager": Service(
            enable=True,
            package=debian["network-manager"],
            service_name="NetworkManager",
        ),
        "openssh": Service(
            enable=True,
            package=debian["openssh-server"],
            service_name="ssh",  # Note: Debian uses "ssh" not "sshd"
        ),
        "bluetooth": Service(
            enable=True, package=debian["bluez"], service_name="bluetooth"
        ),
    }
)

if __name__ == "__main__":
    from pykod.cli import run

    run(conf)
