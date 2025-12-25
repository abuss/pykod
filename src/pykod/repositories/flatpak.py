"""Flatpak repository configuration."""

from .base import Repository


class Flatpak(Repository):
    def __init__(self, **kwargs):
        self.hub_url = kwargs.get(
            "hub_url", "https://flathub.org/repo/flathub.flatpakrepo"
        )

    def install_package(self, package_name) -> str:
        pkgs = " ".join(package_name)
        cmd = f"flatpak install -y flathub {pkgs}"
        return cmd
        # exec_chroot(cmd, mount_point=mount_point)

    def remove_package(self, package_name) -> str:
        pkgs = " ".join(package_name)
        cmd = f"flatpak uninstall -y flathub {pkgs}"
        return cmd
        # exec_chroot(cmd, mount_point=mount_point)

    def update_installed_packages(self, package_name) -> str:
        pkgs = " ".join(package_name)
        cmd = f"flatpak update -y {pkgs}"
        return cmd
        # exec_chroot(cmd, mount_point=mount_point)
