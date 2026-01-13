#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pykod Configuration Generator

This script automatically generates a pykod configuration file based on the current running system.
It inspects hardware, packages, services, users, and other system components to create a complete
configuration that can be used to replicate the system setup.

Author: Pykod Configuration Generator
License: MIT
"""

import json
import os
import pwd
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class SystemInspector:
    """Inspects the current system to gather configuration data."""

    def __init__(self):
        self.hostname = self._get_hostname()
        self.current_user = os.getenv("USER", "root")

    def _run_command(self, command: str, capture_output: bool = True) -> str:
        """Run a shell command and return its output."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=capture_output,
                text=True,
                check=True,
            )
            return result.stdout.strip() if capture_output else ""
        except subprocess.CalledProcessError as e:
            print(f"Warning: Command failed: {command}")
            print(f"Error: {e}")
            return ""

    def _get_hostname(self) -> str:
        """Get the system hostname."""
        try:
            return self._run_command("hostname")
        except Exception:
            return "localhost"

    def get_disk_info(self) -> Dict:
        """Get disk and partition information."""
        try:
            lsblk_output = self._run_command("lsblk -f -J")
            return json.loads(lsblk_output)
        except Exception as e:
            print(f"Error getting disk info: {e}")
            return {"blockdevices": []}

    def get_locale_info(self) -> Dict:
        """Get locale and timezone information."""
        info = {}

        # Get locale information
        try:
            localectl_output = self._run_command("localectl status")
            for line in localectl_output.split("\n"):
                if "System Locale:" in line:
                    lang = line.split("LANG=")[1] if "LANG=" in line else "en_US.UTF-8"
                    info["lang"] = lang
                elif "VC Keymap:" in line:
                    keymap = line.split(":")[1].strip()
                    info["keymap"] = keymap if keymap != "(unset)" else "us"
        except Exception:
            info["lang"] = "en_US.UTF-8"
            info["keymap"] = "us"

        # Get timezone
        try:
            timedatectl_output = self._run_command("timedatectl show")
            for line in timedatectl_output.split("\n"):
                if line.startswith("Timezone="):
                    info["timezone"] = line.split("=")[1]
                    break
        except Exception:
            info["timezone"] = "UTC"

        return info

    def get_installed_packages(self) -> Dict[str, List[str]]:
        """Get lists of installed packages from different sources."""
        packages = {"arch": [], "aur": [], "flatpak": []}

        try:
            # Get all explicitly installed packages
            all_explicit_output = self._run_command("pacman -Qqe")
            all_explicit = set(
                pkg.strip() for pkg in all_explicit_output.split("\n") if pkg.strip()
            )

            # Get foreign packages (AUR packages)
            aur_output = self._run_command("pacman -Qqm")
            aur_packages = set(
                pkg.strip() for pkg in aur_output.split("\n") if pkg.strip()
            )

            # Arch packages = all explicit packages - AUR packages
            arch_packages = all_explicit - aur_packages

            packages["arch"] = sorted(list(arch_packages))
            packages["aur"] = sorted(list(aur_packages))

        except Exception:
            pass

        # Get Flatpak packages
        try:
            flatpak_output = self._run_command(
                "flatpak list --app --columns=application"
            )
            packages["flatpak"] = [
                pkg.strip() for pkg in flatpak_output.split("\n")[1:] if pkg.strip()
            ]
        except Exception:
            pass

        return packages

    def get_enabled_services(self) -> List[str]:
        """Get list of enabled systemd services."""
        try:
            services_output = self._run_command(
                "systemctl list-unit-files --state=enabled --type=service --no-pager"
            )
            services = []
            for line in services_output.split("\n"):
                if ".service" in line and "enabled" in line:
                    service_name = line.split()[0].replace(".service", "")
                    services.append(service_name)
            return services
        except Exception:
            return []

    def get_user_info(self, username: Optional[str] = None) -> Dict:
        """Get information about a specific user."""
        if username is None:
            username = self.current_user

        try:
            user_info = pwd.getpwnam(username)
            return {
                "username": user_info.pw_name,
                "name": user_info.pw_gecos.split(",")[0]
                if user_info.pw_gecos
                else user_info.pw_name,
                "home": user_info.pw_dir,
                "shell": user_info.pw_shell,
                "uid": user_info.pw_uid,
                "gid": user_info.pw_gid,
                "groups": self._get_user_groups(username),
            }
        except KeyError:
            return {}

    def _get_user_groups(self, username: str) -> List[str]:
        """Get list of groups for a user."""
        try:
            groups_output = self._run_command(f"groups {username}")
            # Format: "username : group1 group2 group3"
            groups = (
                groups_output.split(":")[1].strip().split()
                if ":" in groups_output
                else []
            )
            return groups
        except Exception:
            return []

    def get_ssh_keys(self, username: Optional[str] = None) -> List[str]:
        """Get SSH public keys for a user."""
        if username is None:
            username = self.current_user

        keys = []
        user_info = self.get_user_info(username)
        if not user_info:
            return keys

        ssh_dir = Path(user_info["home"]) / ".ssh"
        for key_file in ["id_rsa.pub", "id_ed25519.pub", "id_ecdsa.pub"]:
            key_path = ssh_dir / key_file
            try:
                if key_path.exists():
                    with open(key_path, "r") as f:
                        key_content = f.read().strip()
                        if key_content:
                            keys.append(key_content)
            except Exception:
                continue

        return keys

    def get_desktop_environments(self) -> Dict[str, bool]:
        """Detect installed desktop environments."""
        desktops = {
            "gnome": False,
            "kde": False,
            "xfce": False,
            "cosmic": False,
            "cinnamon": False,
            "budgie": False,
            "pantheon": False,
            "hyprland": False,
        }

        try:
            packages = self.get_installed_packages()
            arch_packages = packages.get("arch", [])

            # Check for desktop environments
            if any("gnome-shell" in pkg for pkg in arch_packages):
                desktops["gnome"] = True
            if any("plasma" in pkg for pkg in arch_packages):
                desktops["kde"] = True
            if any("xfce" in pkg for pkg in arch_packages):
                desktops["xfce"] = True
            if any("cosmic" in pkg for pkg in arch_packages):
                desktops["cosmic"] = True
            if any("cinnamon" in pkg for pkg in arch_packages):
                desktops["cinnamon"] = True
            if any("budgie" in pkg for pkg in arch_packages):
                desktops["budgie"] = True
            if (
                any("pantheon" in pkg for pkg in arch_packages)
                or "gala" in arch_packages
                or "wingpanel" in arch_packages
            ):
                desktops["pantheon"] = True
            if "hyprland" in arch_packages:
                desktops["hyprland"] = True

        except Exception:
            pass

        return desktops

    def get_kernel_info(self) -> str:
        """Get current kernel version."""
        try:
            return self._run_command("uname -r")
        except Exception:
            return "linux"

    def get_arch_mirror(self) -> str:
        """Get the current Arch mirror URL."""
        try:
            # Check mirrorlist for the first active mirror
            mirrorlist_output = self._run_command(
                "grep -E '^Server' /etc/pacman.d/mirrorlist | head -1"
            )
            if mirrorlist_output:
                # Extract the URL from "Server = https://example.com/$repo/os/$arch"
                mirror_line = mirrorlist_output.strip()
                if "Server = " in mirror_line:
                    full_url = mirror_line.split("Server = ")[1]
                    # Remove the $repo/os/$arch part to get base URL
                    if "/$repo/os/$arch" in full_url:
                        base_url = full_url.replace("/$repo/os/$arch", "")
                        return base_url
                    elif "/archlinux/$repo/os/$arch" in full_url:
                        # For mirrors like https://mirror.example.com/archlinux/$repo/os/$arch
                        base_url = full_url.replace("/$repo/os/$arch", "")
                        return base_url
                    else:
                        # For other formats, try to extract base URL
                        import re

                        match = re.match(
                            r"(https?://[^/]+(?:/[^/]+)*?)/?(?:\$repo|\$arch|os|core|extra)",
                            full_url,
                        )
                        if match:
                            return match.group(1)

        except Exception:
            pass

        # Default fallback
        return "https://mirror.rackspace.com/archlinux"

    def get_aur_helper(self) -> tuple[str, str]:
        """
        Get the installed AUR helper and its repository URL.
        Returns (helper_name, helper_url) tuple.
        """
        # Common AUR helpers and their repository URLs
        aur_helpers = {
            "paru": "https://aur.archlinux.org/paru.git",
            "yay": "https://aur.archlinux.org/yay.git",
            "pikaur": "https://aur.archlinux.org/pikaur.git",
            "trizen": "https://aur.archlinux.org/trizen.git",
            "pakku": "https://aur.archlinux.org/pakku.git",
            "aura": "https://aur.archlinux.org/aura-bin.git",
            "pamac": "https://aur.archlinux.org/pamac-aur.git",
        }

        # Check which AUR helper is installed
        for helper, url in aur_helpers.items():
            try:
                # Use subprocess directly to avoid error messages
                import subprocess

                result = subprocess.run(
                    ["which", helper], capture_output=True, text=True
                )
                if result.returncode == 0 and result.stdout.strip():
                    return (helper, url)
            except Exception:
                continue

        # Check if any AUR helper is installed by checking packages
        try:
            packages = self.get_installed_packages()
            aur_packages = packages.get("aur", [])
            arch_packages = packages.get("arch", [])

            # Check both AUR and arch packages for helpers
            all_packages = aur_packages + arch_packages

            for helper in aur_helpers.keys():
                if helper in all_packages or any(helper in pkg for pkg in all_packages):
                    return (helper, aur_helpers[helper])

        except Exception:
            pass

        # Default fallback
        return ("paru", "https://aur.archlinux.org/paru.git")


class ConfigurationGenerator:
    """Generates pykod configuration files from system inspection data."""

    def __init__(self, output_file: str = "system_config.py"):
        self.output_file = output_file
        self.inspector = SystemInspector()

    def generate_header(self) -> str:
        """Generate the configuration file header."""
        arch_mirror = self.inspector.get_arch_mirror()
        aur_helper, aur_helper_url = self.inspector.get_aur_helper()
        return f"""#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Pykod configuration for {self.inspector.hostname}
# ------------------------------------------------------------
# Description: Auto-generated pykod configuration representing the current system state.
# Generated by: Pykod Configuration Generator
# Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
# Host: {self.inspector.hostname}
# License: MIT
# ------------------------------------------------------------

# Import necessary modules from pykod
from pykod import *
from pykod.repositories import AUR, Arch, Flatpak
from pykod.user import (
    GitConfig,
    OpenSSH,
    Program,
    Stow,
    SyncthingConfig,
)

archpkgs = Arch(mirror_url="{arch_mirror}")
aurpkgs = AUR(helper="{aur_helper}", helper_url="{aur_helper_url}")
flatpakpkgs = Flatpak(hub_url="flathub")

conf = Configuration(base=archpkgs, dry_run=True, debug=True, verbose=True)

"""

    def generate_devices_config(self) -> str:
        """Generate devices configuration from disk information."""
        disk_info = self.inspector.get_disk_info()
        config = "# Disk and partition configuration\n"

        if not disk_info.get("blockdevices"):
            config += "# No disk information available\n"
            return config

        config += "conf.devices = Devices(\n"

        disk_count = 0
        for device in disk_info["blockdevices"]:
            device_name = device.get("name", "")
            if not device_name or not device.get("children"):
                continue

            config += f"    disk{disk_count}=Disk(\n"
            config += f'        device="/dev/{device_name}",\n'
            config += "        partitions=[\n"

            for partition in device.get("children", []):
                part_name = partition.get("name", "")
                fstype = partition.get("fstype", "")
                mountpoints = partition.get("mountpoints", [])

                if not part_name:
                    continue

                # Determine partition type and size
                if fstype == "vfat" and mountpoints and "/boot" in mountpoints:
                    config += '            Partition(name="efi", size="1G", type="esp", mountpoint="/boot"),\n'
                elif fstype == "swap":
                    config += '            Partition(name="swap", size="16G", type="linux-swap"),\n'
                elif mountpoints and "/" in mountpoints:
                    config += f'            Partition(name="root", size="100%", type="{fstype or "btrfs"}", mountpoint="/"),\n'
                elif mountpoints:
                    mount_point = mountpoints[0] if mountpoints[0] else "/unknown"
                    config += f'            Partition(name="{part_name}", size="remaining", type="{fstype or "ext4"}", mountpoint="{mount_point}"),\n'

            config += "        ],\n"
            config += "    ),\n"
            disk_count += 1

        config += ")\n\n"
        return config

    def generate_boot_config(self) -> str:
        """Generate boot configuration."""
        kernel_version = self.inspector.get_kernel_info()

        config = "# Boot configuration\n"
        config += "conf.boot = Boot(\n"
        config += "    kernel=Kernel(\n"
        config += '        package=archpkgs["linux"],\n'
        config += "        modules=[\n"

        # Add common modules based on detected hardware
        disk_info = self.inspector.get_disk_info()
        modules = set()

        for device in disk_info.get("blockdevices", []):
            device_name = device.get("name", "")
            if "nvme" in device_name:
                modules.add('"nvme"')
            if device.get("children"):
                for partition in device["children"]:
                    if partition.get("fstype") == "btrfs":
                        modules.add('"btrfs"')
                    elif partition.get("fstype") == "ext4":
                        modules.add('"ext4"')

        for module in sorted(modules):
            config += f"            {module},\n"

        config += "        ],\n"
        config += "    ),\n"
        config += "    loader=Loader(\n"
        config += '        type="systemd-boot",\n'
        config += "        timeout=10,\n"
        config += "    ),\n"
        config += ")\n\n"
        return config

    def generate_locale_config(self) -> str:
        """Generate locale configuration."""
        locale_info = self.inspector.get_locale_info()

        config = "# Locale configuration\n"
        config += "conf.locale = Locale(\n"
        config += f'    default="{locale_info.get("lang", "en_US.UTF-8")} UTF-8",\n'
        config += "    additional_locales=[\n"
        config += '        "en_US.UTF-8 UTF-8",\n'
        config += "    ],\n"
        config += f'    keymap="{locale_info.get("keymap", "us")}",\n'
        config += f'    timezone="{locale_info.get("timezone", "UTC")}",\n'
        config += ")\n\n"
        return config

    def generate_network_config(self) -> str:
        """Generate network configuration."""
        config = "# Network configuration\n"
        config += "conf.network = Network(\n"
        config += f'    hostname="{self.inspector.hostname}",\n'
        config += '    settings={"ipv6": True},\n'
        config += ")\n\n"
        return config

    def generate_desktop_config(self) -> str:
        """Generate desktop environment configuration."""
        desktops = self.inspector.get_desktop_environments()
        packages = self.inspector.get_installed_packages()
        arch_packages = packages.get("arch", [])
        aur_packages = packages.get("aur", [])

        config = "# Desktop environment configuration\n"
        config += "conf.desktop = DesktopManager(\n"

        # Detect display manager
        if "gdm" in arch_packages:
            config += '    display_manager=Service(package=archpkgs["gdm"]),\n'
        elif "cosmic-greeter" in arch_packages:
            config += (
                '    display_manager=Service(package=archpkgs["cosmic-greeter"]),\n'
            )
        elif "sddm" in arch_packages:
            config += '    display_manager=Service(package=archpkgs["sddm"]),\n'
        elif "lightdm" in arch_packages:
            config += '    display_manager=Service(package=archpkgs["lightdm"]),\n'
        else:
            config += '    display_manager=Service(package=archpkgs["gdm"]),\n'

        config += "    environments={\n"

        # Generate GNOME config if detected
        if desktops.get("gnome"):
            config += '        "gnome": DesktopEnvironment(\n'
            config += "            enable=True,\n"
            config += '            package=archpkgs["gnome-shell"],\n'
            config += "            extra_packages=archpkgs[\n"

            gnome_packages = [
                pkg for pkg in arch_packages if "gnome" in pkg and pkg != "gnome-shell"
            ]
            for pkg in sorted(gnome_packages):
                config += f'                "{pkg}",\n'

            config += "            ]\n"

            # Add AUR GNOME extensions
            gnome_aur_packages = [
                pkg for pkg in aur_packages if "gnome-shell-extension" in pkg
            ]
            if gnome_aur_packages:
                config += "            + aurpkgs[\n"
                for pkg in sorted(gnome_aur_packages):
                    config += f'                "{pkg}",\n'
                config += "            ],\n"
            else:
                config += ",\n"

            config += "        ),\n"

        # Generate Cosmic config if detected
        if desktops.get("cosmic"):
            config += '        "cosmic": DesktopEnvironment(\n'
            config += "            enable=True,\n"
            config += '            package=archpkgs["cosmic-session"],\n'
            config += "            extra_packages=archpkgs[\n"

            cosmic_packages = [
                pkg for pkg in arch_packages if pkg.startswith("cosmic-")
            ]
            for pkg in sorted(cosmic_packages):
                if pkg != "cosmic-session":
                    config += f'                "{pkg}",\n'

            config += "            ],\n"
            config += "        ),\n"

        # Generate Pantheon config if detected
        if desktops.get("pantheon"):
            config += '        "pantheon": DesktopEnvironment(\n'
            config += "            enable=True,\n"
            config += '            package=archpkgs["pantheon"],\n'
            config += "            extra_packages=archpkgs[\n"

            pantheon_packages = [
                pkg
                for pkg in arch_packages
                if pkg.startswith("pantheon-")
                or pkg
                in [
                    "gala",
                    "wingpanel",
                    "plank",
                    "switchboard",
                    "elementary-icon-theme",
                    "elementary-wallpapers",
                ]
            ]
            for pkg in sorted(pantheon_packages):
                if pkg != "pantheon":
                    config += f'                "{pkg}",\n'

            config += "            ],\n"
            config += "        ),\n"

        config += "    },\n"
        config += ")\n\n"
        return config

    def generate_fonts_config(self) -> str:
        """Generate fonts configuration."""
        packages = self.inspector.get_installed_packages()
        arch_packages = packages.get("arch", [])
        aur_packages = packages.get("aur", [])

        config = "# Font configuration\n"
        config += "conf.fonts = Fonts(\n"
        config += "    font_dir=True,\n"
        config += "    packages=archpkgs[\n"

        # Find font packages
        font_packages = [
            pkg
            for pkg in arch_packages
            if "ttf-" in pkg or "noto-fonts" in pkg or "adobe-source" in pkg
        ]
        for pkg in sorted(font_packages):
            config += f'        "{pkg}",\n'

        config += "    ]\n"

        # Add AUR font packages
        aur_font_packages = [
            pkg for pkg in aur_packages if "ttf-" in pkg or "font" in pkg
        ]
        if aur_font_packages:
            config += "    + aurpkgs[\n"
            for pkg in sorted(aur_font_packages):
                config += f'        "{pkg}",\n'
            config += "    ],\n"
        else:
            config += ",\n"

        config += ")\n\n"
        return config

    def generate_user_config(self) -> str:
        """Generate user configuration."""
        user_info = self.inspector.get_user_info()
        ssh_keys = self.inspector.get_ssh_keys()

        config = "# User configuration\n"
        config += (
            'conf.root = User(username="root", no_password=True, shell="/bin/bash")\n\n'
        )

        if not user_info:
            return config

        username = user_info["username"]
        config += f"conf.{username} = User(\n"
        config += f'    username="{username}",\n'
        config += f'    name="{user_info.get("name", username)}",\n'
        config += f'    shell="{user_info.get("shell", "/bin/bash")}",\n'

        groups = user_info.get("groups", [])
        if groups:
            # Filter to common groups
            common_groups = [
                "audio",
                "input",
                "users",
                "video",
                "wheel",
                "docker",
                "libvirt",
            ]
            user_groups = [g for g in groups if g in common_groups]
            if user_groups:
                config += f"    groups={user_groups},\n"

        if "wheel" in groups:
            config += "    allow_sudo=True,\n"

        if ssh_keys:
            config += "    ssh_authorized=OpenSSH(\n"
            config += "        keys=[\n"
            for key in ssh_keys:
                config += f'            "{key}",\n'
            config += "        ]\n"
            config += "    ),\n"

        # Add common programs
        packages = self.inspector.get_installed_packages()
        arch_packages = packages.get("arch", [])

        config += "    programs={\n"

        if "git" in arch_packages:
            config += '        "git": Program(\n'
            config += "            enable=True,\n"
            config += '            package=archpkgs["git"],\n'
            config += "            config=GitConfig({\n"
            config += (
                f'                "user.name": "{user_info.get("name", username)}",\n'
            )
            config += f'                "user.email": "{username}@example.com",\n'
            config += '                "core.editor": "nano",\n'
            config += "            }),\n"
            config += "        ),\n"

        for program in [
            "starship",
            "ghostty",
            "zsh",
            "neovim",
            "helix",
            "emacs-wayland",
        ]:
            pkg_name = program.replace("-wayland", "")
            if program in arch_packages:
                config += f'        "{pkg_name}": Program(\n'
                config += "            enable=True,\n"
                config += f'            package=archpkgs["{program}"],\n'
                config += "            deploy_config=True\n"
                config += "        ),\n"

        config += "    },\n"

        # Add services
        if "syncthing" in arch_packages:
            config += "    services={\n"
            config += '        "syncthing": Service(\n'
            config += "            enable=True,\n"
            config += '            package=archpkgs["syncthing"],\n'
            config += "        ),\n"
            config += "    },\n"

        config += ")\n\n"
        return config

    def _deduplicate_packages(
        self, packages: Dict[str, List[str]]
    ) -> Dict[str, List[str]]:
        """
        Ensure each package belongs to only one repository.
        Precedence: AUR > Arch > Flatpak (if there are any conflicts)
        """
        deduplicated = {"arch": [], "aur": [], "flatpak": []}

        # Get package names without prefixes for comparison
        def normalize_name(pkg_name):
            # Remove common flatpak prefixes for comparison
            if "." in pkg_name and len(pkg_name.split(".")) > 2:
                return pkg_name.split(".")[-1].lower()
            return pkg_name.lower()

        # Create sets for quick lookup
        aur_set = set(packages.get("aur", []))
        arch_set = set(packages.get("arch", []))
        flatpak_set = set(packages.get("flatpak", []))

        # AUR packages get highest priority - keep all
        deduplicated["aur"] = list(aur_set)

        # Arch packages - exclude any that are already in AUR
        deduplicated["arch"] = list(arch_set - aur_set)

        # Flatpak packages - keep all (they have different naming scheme)
        # But check for obvious duplicates like browser names
        flatpak_normalized = {normalize_name(pkg): pkg for pkg in flatpak_set}
        arch_aur_normalized = {normalize_name(pkg) for pkg in (aur_set | arch_set)}

        # Remove flatpak packages that have similar names to arch/aur packages
        filtered_flatpak = []
        for pkg in flatpak_set:
            normalized = normalize_name(pkg)
            # Keep flatpak unless there's an obvious duplicate in arch/aur
            if normalized not in arch_aur_normalized:
                filtered_flatpak.append(pkg)
            else:
                print(f"Skipping Flatpak package '{pkg}' - similar to existing package")

        deduplicated["flatpak"] = filtered_flatpak

        return deduplicated

    def _get_packages_declared_elsewhere(self) -> Dict[str, set]:
        """
        Extract package names that are declared in other configuration sections
        to avoid duplication in the main packages section.
        Returns a dict with 'arch', 'aur', 'flatpak' sets of package names.
        """
        declared_packages = {"arch": set(), "aur": set(), "flatpak": set()}

        # Get data from inspector
        packages = self.inspector.get_installed_packages()
        enabled_services = self.inspector.get_enabled_services()
        desktop_envs = self.inspector.get_desktop_environments()
        user_info = self.inspector.get_user_info()
        arch_packages = packages.get("arch", [])

        # Boot kernel package
        declared_packages["arch"].add("linux")

        # Desktop environment packages
        for de in desktop_envs:
            if de.lower() == "gnome":
                # Main GNOME packages
                declared_packages["arch"].update(
                    [
                        "gdm",  # Display manager
                        "gnome-shell",  # Main package
                        # Core GNOME packages declared in desktop config
                        "gnome-backgrounds",
                        "gnome-calculator",
                        "gnome-calendar",
                        "gnome-characters",
                        "gnome-clocks",
                        "gnome-color-manager",
                        "gnome-connections",
                        "gnome-console",
                        "gnome-contacts",
                        "gnome-control-center",
                        "gnome-disk-utility",
                        "gnome-font-viewer",
                        "gnome-keyring",
                        "gnome-logs",
                        "gnome-maps",
                        "gnome-menus",
                        "gnome-music",
                        "gnome-remote-desktop",
                        "gnome-session",
                        "gnome-settings-daemon",
                        "gnome-shell-extension-appindicator",
                        "gnome-software",
                        "gnome-system-monitor",
                        "gnome-text-editor",
                        "gnome-tweaks",
                        "gnome-user-share",
                        "gnome-weather",
                        "xdg-desktop-portal-gnome",
                    ]
                )

                # AUR GNOME extensions
                declared_packages["aur"].update(
                    [
                        "gnome-shell-extension-arc-menu-git",
                        "gnome-shell-extension-blur-my-shell",
                        "gnome-shell-extension-dash-to-dock",
                        "gnome-shell-extension-gsconnect",
                        "gnome-shell-extension-tailscale-qs",
                    ]
                )

            elif de.lower() == "cosmic":
                declared_packages["arch"].update(
                    [
                        "cosmic-session",
                        "cosmic-app-library",
                        "cosmic-applets",
                        "cosmic-bg",
                        "cosmic-comp",
                        "cosmic-files",
                        "cosmic-greeter",
                        "cosmic-idle",
                        "cosmic-launcher",
                        "cosmic-notifications",
                        "cosmic-osd",
                        "cosmic-panel",
                        "cosmic-randr",
                        "cosmic-screenshot",
                        "cosmic-settings",
                        "cosmic-settings-daemon",
                        "cosmic-store",
                        "cosmic-terminal",
                        "cosmic-text-editor",
                        "cosmic-wallpapers",
                        "cosmic-workspaces",
                    ]
                )

        # Font packages
        font_packages = [
            "adobe-source-serif-fonts",
            "noto-fonts-emoji",
            "ttf-fira-code",
            "ttf-fira-sans",
            "ttf-firacode-nerd",
            "ttf-liberation",
            "ttf-nerd-fonts-symbols",
            "ttf-nerd-fonts-symbols-common",
            "ttf-sourcecodepro-nerd",
            "ttf-ubuntu-font-family",
        ]
        declared_packages["arch"].update(font_packages)
        declared_packages["aur"].add("ttf-work-sans")

        # User program packages
        user_programs = {
            "git": "arch",
            "starship": "arch",
            "ghostty": "arch",
            "zsh": "arch",
            "neovim": "arch",
            "helix": "arch",
            "emacs-wayland": "arch",
        }

        for program, repo in user_programs.items():
            declared_packages[repo].add(program)

        # Service packages
        service_mapping = {
            "NetworkManager": "networkmanager",
            "bluetooth": "bluez",
            "cups": "cups",
            "gdm": "gdm",
            "sshd": "openssh",
            "tailscaled": "tailscale",
            "fwupd": "fwupd",
        }

        for service in enabled_services:
            if service in service_mapping:
                package_name = service_mapping[service]
                if package_name in arch_packages:
                    declared_packages["arch"].add(package_name)

        # User service packages
        declared_packages["arch"].add("syncthing")

        return declared_packages

    def _get_framework_base_packages(self) -> Dict[str, set]:
        """
        Get packages that are automatically installed by the pykod framework itself.
        These are defined in the repository base packages and should not be explicitly listed.
        Based on src/pykod/repositories/arch.py get_base_packages() method.
        """
        framework_packages = {"arch": set(), "aur": set(), "flatpak": set()}

        # From Arch repository get_base_packages() method (lines 54-67)
        base_packages = [
            "base",  # Core Arch Linux base package
            "base-devel",  # Development tools (also required for AUR)
            "btrfs-progs",  # Filesystem tools
            "linux-firmware",  # Hardware firmware
            "bash-completion",  # Shell completion
            "mlocate",  # File location database
            "sudo",  # Privilege escalation
            "schroot",  # Chroot management
            "whois",  # Network tools
            "dracut",  # Initramfs generator
            "git",  # Version control (also required for AUR)
        ]

        # CPU microcode packages (auto-detected by framework)
        microcode_packages = [
            "amd-ucode",  # AMD CPU microcode
            "intel-ucode",  # Intel CPU microcode
        ]

        framework_packages["arch"].update(base_packages)
        framework_packages["arch"].update(microcode_packages)

        # AUR repository also ensures git and base-devel are installed (line 55 in aur.py)
        # But these are already covered in the arch packages above

        return framework_packages

    def generate_packages_config(self) -> str:
        """Generate packages configuration with categorized comments."""
        packages = self.inspector.get_installed_packages()

        # Deduplicate packages to ensure each belongs to only one repository
        packages = self._deduplicate_packages(packages)

        # Get packages that are declared in other configuration sections
        declared_elsewhere = self._get_packages_declared_elsewhere()

        # Get packages that are automatically installed by pykod framework
        framework_base = self._get_framework_base_packages()

        # Filter out both declared elsewhere and framework base packages
        filtered_packages = {"arch": [], "aur": [], "flatpak": []}

        for repo in ["arch", "aur", "flatpak"]:
            declared_set = declared_elsewhere[repo]
            framework_set = framework_base[repo]
            combined_exclusions = declared_set | framework_set

            original_list = packages.get(repo, [])
            filtered_list = [
                pkg for pkg in original_list if pkg not in combined_exclusions
            ]
            filtered_packages[repo] = filtered_list

            # Debug output
            removed_elsewhere = len(
                [pkg for pkg in original_list if pkg in declared_set]
            )
            removed_framework = len(
                [pkg for pkg in original_list if pkg in framework_set]
            )

            if removed_elsewhere > 0:
                print(
                    f"Filtered {removed_elsewhere} {repo.upper()} packages already declared elsewhere"
                )
            if removed_framework > 0:
                print(
                    f"Filtered {removed_framework} {repo.upper()} framework base packages"
                )

        config = "# Package configuration\n"
        config += "conf.packages = Packages(\n"

        # Arch packages
        arch_packages = filtered_packages.get("arch", [])
        if arch_packages:
            config += self._generate_categorized_arch_packages(arch_packages)

        # AUR packages
        aur_packages = filtered_packages.get("aur", [])
        if aur_packages:
            config += self._generate_categorized_aur_packages(aur_packages)

        # Flatpak packages
        flatpak_packages = filtered_packages.get("flatpak", [])
        if flatpak_packages:
            config += self._generate_categorized_flatpak_packages(flatpak_packages)

        config += ")\n\n"
        return config

    def _categorize_arch_packages(self, packages: list) -> dict:
        """Categorize Arch packages by type."""
        categories = {
            "Core System": [],
            "Development Tools": [],
            "Editors & IDEs": [],
            "System Utilities": [],
            "Shell & Terminal": [],
            "Network & Communication": [],
            "Audio & Video": [],
            "Graphics & Design": [],
            "Office & Productivity": [],
            "Gaming": [],
            "Virtualization": [],
            "Desktop Environment": [],
            "Font Packages": [],
            "Security & Encryption": [],
            "File Systems": [],
            "Archive & Compression": [],
            "Database": [],
            "Languages & Runtimes": [],
            "Build Tools": [],
            "Documentation": [],
            "Drivers & Hardware": [],
            "Other": [],
        }

        # Define package patterns for categorization
        patterns = {
            "Core System": [
                "base",
                "base-devel",
                "linux",
                "linux-firmware",
                "sudo",
                "systemd",
                "pacman",
                "archlinux-keyring",
                "glibc",
                "gcc",
                "binutils",
                "coreutils",
                "util-linux",
                "filesystem",
                "systemd-sysvcompat",
            ],
            "Development Tools": [
                "git",
                "github-cli",
                "mercurial",
                "subversion",
                "gitg",
                "meld",
                "make",
                "cmake",
                "ninja",
                "autoconf",
                "automake",
                "pkgconf",
                "devtools",
                "arch-install-scripts",
                "debugedit",
                "fakeroot",
                "patch",
                "diffutils",
                "lldb",
                "gdb",
                "valgrind",
                "strace",
            ],
            "Editors & IDEs": [
                "neovim",
                "vim",
                "emacs",
                "nano",
                "helix",
                "code",
                "atom",
                "sublime-text",
                "intellij-idea",
                "pycharm",
                "eclipse",
            ],
            "System Utilities": [
                "htop",
                "btop",
                "top",
                "ps",
                "kill",
                "killall",
                "pstree",
                "mc",
                "ranger",
                "lf",
                "tree",
                "less",
                "more",
                "grep",
                "sed",
                "awk",
                "find",
                "locate",
                "which",
                "whereis",
                "man-db",
                "man-pages",
                "info",
                "help2man",
                "tldr",
                "rsync",
                "rsyncd",
                "wget",
                "curl",
                "aria2",
                "uget",
            ],
            "Shell & Terminal": [
                "bash",
                "zsh",
                "fish",
                "dash",
                "tcsh",
                "ksh",
                "bash-completion",
                "zsh-completions",
                "starship",
                "powerline",
                "ghostty",
                "alacritty",
                "kitty",
                "gnome-terminal",
                "konsole",
                "xterm",
                "terminator",
                "tilix",
                "wezterm",
                "foot",
                "st",
            ],
            "Network & Communication": [
                "networkmanager",
                "network-manager",
                "dhcpcd",
                "netctl",
                "openssh",
                "sshfs",
                "wireguard",
                "openvpn",
                "tailscale",
                "firefox",
                "chromium",
                "google-chrome",
                "opera",
                "brave",
                "thunderbird",
                "evolution",
                "mutt",
                "neomutt",
                "telegram",
                "discord",
                "slack",
                "zoom",
                "skype",
                "signal-desktop",
            ],
            "Audio & Video": [
                "pulseaudio",
                "pipewire",
                "pipewire-pulse",
                "pipewire-alsa",
                "alsa-utils",
                "alsa-plugins",
                "jack",
                "vlc",
                "mpv",
                "mplayer",
                "ffmpeg",
                "gstreamer",
                "audacity",
                "obs-studio",
                "kdenlive",
                "gimp",
                "blender",
                "inkscape",
                "krita",
                "darktable",
            ],
            "Graphics & Design": [
                "mesa",
                "vulkan",
                "nvidia",
                "nvidia-utils",
                "xf86-video",
                "gimp",
                "inkscape",
                "blender",
                "krita",
                "darktable",
                "imagemagick",
                "graphicsmagick",
                "optipng",
                "jpegoptim",
            ],
            "Office & Productivity": [
                "libreoffice",
                "calligra",
                "abiword",
                "gnumeric",
                "evince",
                "okular",
                "zathura",
                "mupdf",
                "xpdf",
                "calibre",
                "sigil",
                "scribus",
            ],
            "Gaming": [
                "steam",
                "lutris",
                "wine",
                "wine-staging",
                "winetricks",
                "gamemode",
                "mangohud",
                "discord",
                "teamspeak3",
            ],
            "Virtualization": [
                "docker",
                "podman",
                "qemu",
                "qemu-desktop",
                "libvirt",
                "virt-manager",
                "virtualbox",
                "vmware-workstation",
                "distrobox",
                "lxc",
                "lxd",
                "systemd-nspawn",
            ],
            "Desktop Environment": [
                "gnome",
                "kde",
                "xfce",
                "lxde",
                "mate",
                "cinnamon",
                "budgie",
                "cosmic",
                "pantheon",
                "enlightenment",
                "i3",
                "awesome",
                "bspwm",
                "dwm",
                "openbox",
                "fluxbox",
                "hyprland",
                "sway",
                "wayfire",
                "river",
            ],
            "Font Packages": [
                "ttf-",
                "otf-",
                "noto-fonts",
                "adobe-source",
                "font",
                "fontconfig",
                "freetype2",
            ],
            "Security & Encryption": [
                "gnupg",
                "gpg",
                "pass",
                "keepassxc",
                "bitwarden",
                "openssl",
                "gnutls",
                "ca-certificates",
                "nss",
                "encfs",
                "cryptsetup",
                "luks",
                "veracrypt",
            ],
            "File Systems": [
                "btrfs-progs",
                "e2fsprogs",
                "xfsprogs",
                "ntfs-3g",
                "exfat-utils",
                "dosfstools",
                "gvfs",
                "udisks2",
                "fuse",
                "sshfs",
                "nfs-utils",
                "cifs-utils",
            ],
            "Archive & Compression": [
                "tar",
                "gzip",
                "xz",
                "zip",
                "unzip",
                "p7zip",
                "unrar",
                "rar",
                "lz4",
                "zstd",
                "bzip2",
            ],
            "Database": [
                "postgresql",
                "mysql",
                "mariadb",
                "sqlite",
                "redis",
                "mongodb",
                "influxdb",
                "elasticsearch",
            ],
            "Languages & Runtimes": [
                "python",
                "python2",
                "python3",
                "nodejs",
                "npm",
                "yarn",
                "ruby",
                "perl",
                "php",
                "java",
                "openjdk",
                "go",
                "rust",
                "lua",
                "r",
                "julia",
                "erlang",
                "elixir",
                "haskell",
                "scala",
                "kotlin",
                "clojure",
                "racket",
                "zig",
            ],
            "Build Tools": [
                "meson",
                "scons",
                "bazel",
                "gradle",
                "maven",
                "ant",
                "cargo",
                "rustc",
                "gcc",
                "clang",
                "llvm",
            ],
            "Documentation": [
                "doxygen",
                "sphinx",
                "pandoc",
                "texlive",
                "latex",
                "markdown",
                "asciidoc",
            ],
            "Drivers & Hardware": [
                "nvidia",
                "mesa",
                "vulkan",
                "amd-ucode",
                "intel-ucode",
                "bluez",
                "bluetooth",
                "wireless-tools",
                "iw",
                "wpa_supplicant",
            ],
        }

        # Categorize packages
        for pkg in packages:
            categorized = False
            for category, pattern_list in patterns.items():
                for pattern in pattern_list:
                    if pattern in pkg or pkg.startswith(pattern):
                        categories[category].append(pkg)
                        categorized = True
                        break
                if categorized:
                    break

            if not categorized:
                categories["Other"].append(pkg)

        # Remove empty categories and sort packages within each category
        return {k: sorted(v) for k, v in categories.items() if v}

    def _generate_categorized_arch_packages(self, packages: list) -> str:
        """Generate categorized Arch packages with comments."""
        categories = self._categorize_arch_packages(packages)
        config = "    # Arch Linux packages\n"
        config += "    archpkgs[\n"

        first_category = True
        for category, pkgs in categories.items():
            if not first_category:
                config += "\n"
            config += f"        # {category}\n"
            for pkg in pkgs:
                config += f'        "{pkg}",\n'
            first_category = False

        config += "    ]\n"
        return config

    def _categorize_aur_packages(self, packages: list) -> dict:
        """Categorize AUR packages by type."""
        categories = {
            "Browsers": [],
            "Development Tools": [],
            "System Utilities": [],
            "Media & Graphics": [],
            "Gaming": [],
            "Productivity": [],
            "Fonts & Themes": [],
            "Desktop Extensions": [],
            "Drivers & Hardware": [],
            "Other": [],
        }

        patterns = {
            "Browsers": [
                "browser",
                "chrome",
                "firefox",
                "brave",
                "vivaldi",
                "opera",
                "zen-browser",
            ],
            "Development Tools": [
                "visual-studio-code",
                "code",
                "ide",
                "editor",
                "git",
                "dev",
            ],
            "System Utilities": ["manager", "tool", "util", "monitor", "fanctrl"],
            "Media & Graphics": ["slicer", "3d", "graphics", "media", "player"],
            "Gaming": ["game", "steam", "discord", "gaming"],
            "Productivity": ["office", "note", "document", "pdf", "sync"],
            "Fonts & Themes": ["ttf-", "font", "theme", "icon"],
            "Desktop Extensions": ["gnome-shell-extension", "kde", "plasma", "desktop"],
            "Drivers & Hardware": ["driver", "firmware", "hardware", "controller"],
        }

        for pkg in packages:
            categorized = False
            for category, pattern_list in patterns.items():
                for pattern in pattern_list:
                    if pattern in pkg.lower():
                        categories[category].append(pkg)
                        categorized = True
                        break
                if categorized:
                    break

            if not categorized:
                categories["Other"].append(pkg)

        return {k: sorted(v) for k, v in categories.items() if v}

    def _generate_categorized_aur_packages(self, packages: list) -> str:
        """Generate categorized AUR packages with comments."""
        categories = self._categorize_aur_packages(packages)
        config = "\n    # AUR packages\n"
        config += "    + aurpkgs[\n"

        first_category = True
        for category, pkgs in categories.items():
            if not first_category:
                config += "\n"
            config += f"        # {category}\n"
            for pkg in pkgs:
                config += f'        "{pkg}",\n'
            first_category = False

        config += "    ]\n"
        return config

    def _categorize_flatpak_packages(self, packages: list) -> dict:
        """Categorize Flatpak packages by domain/type."""
        categories = {
            "Development": [],
            "Graphics & Design": [],
            "Office & Productivity": [],
            "Communication": [],
            "Media & Entertainment": [],
            "Education & Science": [],
            "Games": [],
            "Utilities": [],
            "GNOME Applications": [],
            "Other": [],
        }

        patterns = {
            "Development": ["dev.", "code", "editor", "ide", "git"],
            "Graphics & Design": ["gimp", "inkscape", "blender", "design", "graphics"],
            "Office & Productivity": [
                "office",
                "document",
                "pdf",
                "note",
                "text",
                "writer",
                "calc",
            ],
            "Communication": [
                "chat",
                "mail",
                "message",
                "social",
                "discord",
                "telegram",
            ],
            "Media & Entertainment": [
                "media",
                "player",
                "music",
                "video",
                "audio",
                "tube",
            ],
            "Education & Science": [
                "education",
                "science",
                "math",
                "research",
                "reference",
            ],
            "Games": ["game", "gaming", "entertainment"],
            "Utilities": ["tool", "util", "manager", "system"],
            "GNOME Applications": ["org.gnome", "gnome"],
        }

        for pkg in packages:
            categorized = False
            for category, pattern_list in patterns.items():
                for pattern in pattern_list:
                    if pattern in pkg.lower():
                        categories[category].append(pkg)
                        categorized = True
                        break
                if categorized:
                    break

            if not categorized:
                categories["Other"].append(pkg)

        return {k: sorted(v) for k, v in categories.items() if v}

    def _generate_categorized_flatpak_packages(self, packages: list) -> str:
        """Generate categorized Flatpak packages with comments."""
        categories = self._categorize_flatpak_packages(packages)
        config = "\n    # Flatpak applications\n"
        config += "    + flatpakpkgs[\n"

        first_category = True
        for category, pkgs in categories.items():
            if not first_category:
                config += "\n"
            config += f"        # {category}\n"
            for pkg in pkgs:
                config += f'        "{pkg}",\n'
            first_category = False

        config += "    ]\n"
        return config

    def generate_services_config(self) -> str:
        """Generate services configuration."""
        enabled_services = self.inspector.get_enabled_services()
        packages = self.inspector.get_installed_packages()
        arch_packages = packages.get("arch", [])

        config = "# System services configuration\n"
        config += "conf.services = Services({\n"

        # Map common services to their packages and config
        service_mapping = {
            "NetworkManager": {
                "package": "networkmanager",
                "service_name": "NetworkManager",
            },
            "bluetooth": {"package": "bluez", "service_name": "bluetooth"},
            "cups": {"package": "cups"},
            "avahi-daemon": {"package": "avahi", "service_name": "avahi-daemon"},
            "sshd": {"package": "openssh", "service_name": "sshd"},
            "tailscaled": {"package": "tailscale", "service_name": "tailscaled"},
            "systemd-timesyncd": {"service_name": "systemd-timesyncd"},
            "gdm": {"package": "gdm"},
            "fwupd": {"package": "fwupd"},
        }

        for service in enabled_services:
            if service in service_mapping:
                service_config = service_mapping[service]
                package_name = service_config.get("package")

                # Check if the package is actually installed
                if package_name and package_name not in arch_packages:
                    continue

                config += f'    "{service}": Service(\n'
                config += "        enable=True,\n"

                if package_name:
                    config += f'        package=archpkgs["{package_name}"],\n'

                service_name = service_config.get("service_name")
                if service_name and service_name != service:
                    config += f'        service_name="{service_name}",\n'

                config += "    ),\n"

        config += "})\n\n"
        return config

    def generate_footer(self) -> str:
        """Generate the configuration file footer."""
        return """if __name__ == "__main__":
    from pykod.cli import run

    run(conf)
"""

    def generate_config(self) -> str:
        """Generate the complete configuration file."""
        config_parts = [
            self.generate_header(),
            self.generate_devices_config(),
            self.generate_boot_config(),
            self.generate_locale_config(),
            self.generate_network_config(),
            self.generate_desktop_config(),
            self.generate_fonts_config(),
            self.generate_user_config(),
            self.generate_packages_config(),
            self.generate_services_config(),
            self.generate_footer(),
        ]

        return "".join(config_parts)

    def write_config(self) -> None:
        """Write the generated configuration to a file."""
        config_content = self.generate_config()

        with open(self.output_file, "w") as f:
            f.write(config_content)

        print(f"Configuration generated successfully: {self.output_file}")
        print(f"Hostname: {self.inspector.hostname}")
        print(f"Current user: {self.inspector.current_user}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate a pykod configuration file from the current system"
    )
    parser.add_argument(
        "-o",
        "--output",
        default="auto_generated_config.py",
        help="Output configuration file (default: auto_generated_config.py)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without writing file",
    )

    args = parser.parse_args()

    generator = ConfigurationGenerator(args.output)

    if args.dry_run:
        print("Generated configuration (dry run):")
        print("=" * 50)
        print(generator.generate_config())
    else:
        generator.write_config()


if __name__ == "__main__":
    main()
