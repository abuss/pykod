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

        # TODO: Generalize this code to support other distros
        # exec_chroot("pacman -S --needed --noconfirm git base-devel")
        exec_chroot(
            f"runuser -u kod -- /bin/bash -c 'cd && git clone {url} {name} && cd {name} && {build_cmd}'",
            mount_point=mount_point,
        )

    def install_package(self, package_name):
        if not self.helper_installed:
            self.build(mount_point="/mnt")
            self.helper_installed = True
        pkgs = " ".join(package_name)
        cmd = f"runuser -u kod -- {self.helper} -S --needed --noconfirm {pkgs}"
        return cmd

    def remove_package(self, package_name):
        pkgs = " ".join(package_name)
        cmd = f"runuser -u kod -- {self.helper} -R --noconfirm {pkgs}"
        return cmd

    def update_installed_packages(self) -> str:
        cmd = f"runuser -u kod -- {self.helper} -Syu --noconfirm"
        return cmd

    def update_database(self) -> str:
        cmd = f"{self.helper} -Sy"
        return cmd
