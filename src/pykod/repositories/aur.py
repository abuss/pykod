"""AUR (Arch User Repository) configuration."""

from pykod.common import exec_chroot

from .base import Repository


class AUR(Repository):
    def __init__(self, **kwargs):
        self.helper = kwargs.get("helper", "yay")
        self.helper_url = kwargs.get("helper_url", "https://aur.archlinux.org/yay.git")
        self.helper_installed = False

    def build(self, mount_point):
        name = self.helper
        url = self.helper_url
        build_cmd = "makepkg -si --noconfirm"

        # TODO: Check if git and base-devel are installed before installing them
        exec_chroot(
            "pacman -S --needed --noconfirm git base-devel", mount_point=mount_point
        )
        exec_chroot(
            f"runuser -u kod -- /bin/bash -c 'cd && git clone {url} {name} && cd {name} && {build_cmd}'",
            mount_point=mount_point,
        )

    def prepare(self, mount_point: str) -> None:
        """Prepare the AUR helper inside the given chroot mount point."""
        if not self.helper_installed:
            self.build(mount_point=mount_point)
            self.helper_installed = True

    def install_package(self, package_name):
        pkgs = " ".join(package_name)
        cmd = f"runuser -u kod -- {self.helper} -S --needed --noconfirm {pkgs}"
        return cmd

    def remove_package(self, package_name):
        pkgs = " ".join(package_name)
        cmd = f"runuser -u kod -- {self.helper} -R --noconfirm {pkgs}"
        return cmd

    def update_installed_packages(self, packages: tuple) -> str:
        if len(packages) == 0:
            return ""
        pkgs = " ".join(packages)
        cmd = f"runuser -u kod -- {self.helper} -Syu --noconfirm {pkgs}"
        return cmd

    def update_database(self) -> str:
        cmd = f"{self.helper} -Sy"
        return cmd
