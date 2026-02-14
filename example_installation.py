#!/usr/bin/env python3
"""
Example KodOS installation configuration demonstrating the complete system.

This example shows how to use all the implemented section managers together
with the main KodOSInstaller orchestrator.
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from pykod.section import (
    KodOSInstaller,
    Device,
    ProgramManager,
    ServiceManager,
    HardwareManager,
    DesktopManager,
    Program,
    Service,
    DesktopEnvironment,
    User,
    Locale,
    Network,
)


def main():
    """Demonstrate a complete KodOS installation configuration."""

    # 1. Device/Partition Configuration
    device_config = Device(
        devices={
            "disk0": {
                "device": "/dev/vda",
                "efi": True,
                "type": "gpt",
                "partitions": [
                    {
                        "name": "Boot",
                        "size": "1GB",
                        "type": "esp",
                        "mountpoint": "/boot",
                    },
                    {
                        "name": "Swap",
                        "size": "4GB",
                        "type": "linux-swap",
                        "resumeDevice": True,
                    },
                    {
                        "name": "Root",
                        "size": "100%",
                        "type": "btrfs",
                        "mountpoint": "/",
                    },
                ],
            }
        }
    )

    # 2. Program Manager - User applications
    programs = ProgramManager()
    programs.add_program("git", Program(enable=True, package="git"))
    programs.add_program(
        "neovim", Program(enable=True, package="neovim", deploy_config=True)
    )
    programs.add_program("firefox", Program(enable=True, package="firefox"))
    programs.add_program("discord", Program(enable=True, package="aur:discord"))
    programs.add_program(
        "spotify", Program(enable=True, package="flatpak:com.spotify.Client")
    )

    # 3. Service Manager - System services
    services = ServiceManager()
    services.add_service(
        "openssh",
        Service(
            enable=True,
            service_name="sshd",
            package="openssh",
            settings={"PermitRootLogin": "no"},
        ),
    )
    services.add_service("tailscale", Service(enable=True, package="aur:tailscale"))

    # 4. Hardware Manager - Hardware-specific services
    hardware = HardwareManager()
    hardware.add_service(
        "pipewire",
        Service(
            enable=True, extra_packages=["pipewire", "pipewire-alsa", "pipewire-pulse"]
        ),
    )
    hardware.add_service(
        "bluetooth",
        Service(enable=True, package="bluez", extra_packages=["bluez-utils"]),
    )

    # 5. Desktop Manager - Desktop environments
    desktop = DesktopManager()
    desktop.add_environment(
        "gnome",
        DesktopEnvironment(
            enable=True, display_manager="gdm", extra_packages=["gnome-tweaks"]
        ),
    )

    # 6. User Configuration
    user_programs = ProgramManager()
    user_programs.add_program(
        "tmux", Program(enable=True, package="tmux", deploy_config=True)
    )

    main_user = User(
        username="johndoe",
        name="John Doe",
        shell="/bin/zsh",
        allow_sudo=True,
        programs=user_programs,
    )

    # 7. System Configuration
    locale_config = Locale(
        default="en_US.UTF-8 UTF-8", keymap="us", timezone="America/New_York"
    )

    network_config = Network(hostname="kodbox", settings={"ipv6": True})

    # 8. Main Installation Orchestrator
    installer = KodOSInstaller(
        device=device_config,
        programs=programs,
        services=services,
        hardware=hardware,
        desktop=desktop,
        users=[main_user],
        locale=locale_config,
        network=network_config,
    )

    # 9. Demonstrate package collection
    print("=== Package Collection Demo ===")
    packages = installer.collect_packages()

    print(f"Regular packages ({len(packages['packages'])}): {packages['packages']}")
    print(f"AUR packages ({len(packages['aur_packages'])}): {packages['aur_packages']}")
    print(
        f"Flatpak packages ({len(packages['flatpak_packages'])}): {packages['flatpak_packages']}"
    )
    print(
        f"Services to enable ({len(packages['enabled_services'])}): {packages['enabled_services']}"
    )

    # 10. Demonstrate full installation (dry-run)
    print("\n=== Full Installation Demo (Dry-run) ===")
    installation = installer.install(mount_point="/mnt", execute_commands=False)

    print("Partition info:", installation["partitions"].get("created_partitions", []))
    print("Total packages to install:", len(installation["packages"]["packages"]))
    print("Services to enable:", installation["services"])
    print("Users to create:", [u["username"] for u in installation["users"]])

    return installer


if __name__ == "__main__":
    installer = main()
    print("✅ KodOS installation configuration created successfully!")
