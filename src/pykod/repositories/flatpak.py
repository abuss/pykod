"""Flatpak repository configuration."""

from pykod.common import exec_chroot

from .base import Repository


class Flatpak(Repository):
    def __init__(self, **kwargs):
        self.hub_url = kwargs.get(
            "hub_url", "https://flathub.org/repo/flathub.flatpakrepo"
        )
        self.flatpak_installed = False

    def build(self, mount_point):
        # Install flatpak if not installed
        if not self.flatpak_installed:
            cmd_install_flatpak = "pacman -S flatpak"
            exec_chroot(cmd_install_flatpak, mount_point=mount_point)
            self.flatpak_installed = True

        # Add flathub repository
        cmd_add_repo = f"flatpak remote-add --if-not-exists flathub {self.hub_url}"
        exec_chroot(cmd_add_repo, mount_point=mount_point)
        self.flatpak_installed = True

    def install_package(self, package_name) -> str:
        if not self.flatpak_installed:
            self.build(mount_point="/mnt")
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
