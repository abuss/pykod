"""Flatpak repository configuration."""

# from pykod.config import Install, Rebuild
from .base import Repository


class Flatpak(Repository):
    def __init__(self, **kwargs):
        self.hub_url = kwargs.get(
            "hub_url", "https://flathub.org/repo/flathub.flatpakrepo"
        )

    # def install(self, items) -> None:
    #     print("[install] Flatpak repo:", self)
    #     for item in items:
    #         print(f"  - {item}")

    # def remove(self, items) -> None:
    #     print("[remove] Flatpak repo:", self)
    #     for item in items:
    #         print(f"  - {item}")

    def install_package(self, package_name, mount_point):
        cmd = f"flatpak install -y flathub {package_name}"
        exec_chroot(cmd, mount_point=mount_point)

    def remove_package(self, package_name, mount_point):
        cmd = f"flatpak uninstall -y flathub {package_name}"
        exec_chroot(cmd, mount_point=mount_point)

    def update_package_list(self, package_name, mount_point):
        cmd = f"flatpak update -y {package_name}"
        exec_chroot(cmd, mount_point=mount_point)
