#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Pykod configuration for Ubuntu system with GNOME desktop
# ------------------------------------------------------------
# Description: Ubuntu installation with systemd-boot, BTRFS, and GNOME
# Author: Antal Buss
# Date: 2025-01-XX
# License: MIT
# Notes: This configuration uses Ubuntu with systemd-boot and BTRFS
#        for atomic generations (same approach as Debian/Arch).
# ------------------------------------------------------------

from pykod import *
from pykod.core import File, Source
from pykod.repositories import Debian, Flatpak
from pykod.repositories.debian import GPU_PACKAGES

# Initialize Ubuntu repository (uses Debian class with variant="ubuntu")
ubuntu = Debian(
    release="noble",  # Ubuntu 24.04 LTS
    variant="ubuntu",
    mirror_url="http://archive.ubuntu.com/ubuntu/",
    # components=["main", "universe"]  # Default - automatically enabled
    # components=["main", "universe", "multiverse", "restricted"]  # All repos
)

# Other Ubuntu releases:
# ubuntu = Debian(release="jammy", variant="ubuntu")  # Ubuntu 22.04 LTS
# ubuntu = Debian(release="focal", variant="ubuntu")  # Ubuntu 20.04 LTS
#
# Repository components:
# - main:       Canonical-supported free software (default)
# - universe:   Community-maintained free software (default for Ubuntu)
# - multiverse: Software with copyright/legal restrictions
# - restricted: Proprietary drivers

flatpak = Flatpak(hub_url="flathub")

# Create configuration
# conf = Configuration(base=ubuntu, dry_run=True, debug=True, verbose=True)
conf = Configuration(base=ubuntu, interactive=True, verbose=True)

# Disk configuration - same as Arch/Debian (BTRFS + generations)
conf.devices = Devices(
    disk0=Disk(
        device="/dev/sda",
        initialize=True,
        partitions=[
            Partition(name="efi", size="512M", type="esp", mountpoint="/boot"),
            Partition(name="root", size="100%", type="btrfs", mountpoint="/"),
        ],
    ),
)

# Boot configuration - systemd-boot
conf.boot = Boot(
    kernel=Kernel(
        package=ubuntu["linux-image-generic"],  # Ubuntu kernel package
        modules=[
            "xhci_pci",
            "ahci",
            "usbhid",
            "virtio_blk",
            "virtio_pci",
        ],
    ),
    loader=Loader(
        type="systemd-boot",
        timeout=10,
    ),
)

# Locale configuration
conf.locale = Locale(
    default="en_US.UTF-8 UTF-8",
    additional_locales=[
        "en_GB.UTF-8 UTF-8",
    ],
    keymap="us",
    timezone="America/New_York",
)

# Network configuration
conf.network = Network(
    hostname="ubuntu-box",
    settings={"ipv6": True},
)

# Hardware configuration with GPU support
conf.hardware = Hardware(
    gpu=ubuntu[*GPU_PACKAGES["intel"]["base"]],
    audio=ubuntu["pipewire", "pipewire-alsa", "pipewire-pulse"],
)

# Desktop environment - Ubuntu Desktop (includes GNOME)
conf.desktop = DesktopManager(
    display_manager=Service(package=ubuntu["gdm3"]),
    environments={
        "gnome": DesktopEnvironment(
            enable=True,
            package=ubuntu["ubuntu-desktop-minimal"],  # Minimal Ubuntu Desktop
            extra_packages=ubuntu[
                "gnome-tweaks",
                "gnome-shell-extensions",
            ],
        ),
    },
)

# Fonts
conf.fonts = Fonts(
    font_dir=True,
    packages=ubuntu[
        "fonts-noto",
        "fonts-noto-color-emoji",
        "fonts-liberation",
        "fonts-ubuntu",
    ],
)

# Users
conf.root = User(username="root", no_password=True, shell="/bin/bash")

conf.user = User(
    username="user",
    name="Ubuntu User",
    shell="/usr/bin/bash",
    groups=["audio", "video", "users", "sudo"],
    allow_sudo=True,
    hashed_password="$6$MOkGLOzXlj0lIE2d$5sxAysiDyD/7ZfntgZaN3vJ48t.BMi2qwPxqjgVxGXKXrNlFxRvnO8uCvOlHaGW2pVDrjt0JLNR9GWH.2YT5j.",
)

# Packages
conf.packages = Packages(
    ubuntu[
        "firefox",  # Ubuntu includes Firefox
        "git",
        "vim",
        "htop",
        "curl",
        "wget",
        "build-essential",
        "flatpak",
    ]
)

# System services
conf.services = Services(
    {
        "networkmanager": Service(
            enable=True,
            package=ubuntu["network-manager"],
            service_name="NetworkManager",
        ),
        "openssh": Service(
            enable=True,
            package=ubuntu["openssh-server"],
            service_name="ssh",
        ),
        "bluetooth": Service(
            enable=True, package=ubuntu["bluez"], service_name="bluetooth"
        ),
    }
)

if __name__ == "__main__":
    from pykod.cli import run

    run(conf)
