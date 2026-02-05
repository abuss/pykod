"""Flatpak repository configuration."""

from .base import Repository


class Flatpak(Repository):
    def __init__(self, **kwargs):
        self.hub_url = kwargs.get(
            "hub_url", "https://flathub.org/repo/flathub.flatpakrepo"
        )
        self.flatpak_installed = False

    def install_packages(self, package_name) -> str:
        cmds = []

        if not self.flatpak_installed:
            # cmd_install_flatpak = "pacman -S --noconfirm flatpak"
            # cmds.append(cmd_install_flatpak)
            cmd_add_repo = f"flatpak remote-add --if-not-exists flathub {self.hub_url}"
            cmds.append(cmd_add_repo)
            self.flatpak_installed = True
        pkgs = " ".join(package_name)
        cmd = f"flatpak install -y flathub {pkgs}"
        cmds.append(cmd)
        cmds_str = " && ".join(cmds)

        return cmds_str

    def remove_packages(self, package_name) -> str:
        if package_name is None or len(package_name) == 0:
            return ""
        pkgs = " ".join(package_name)
        cmd = f"flatpak uninstall -y flathub {pkgs}"
        return cmd

    def update_installed_packages(self, packages: tuple) -> str:
        if len(packages) == 0:
            return ""
        pkgs = " ".join(packages)
        cmd = f"flatpak update -y {pkgs}"
        return cmd

    def is_valid_packages(self, pkgs):
        """Check if the given package is valid."""
        # TODO: Implement package validation for Flatpak
        return None
