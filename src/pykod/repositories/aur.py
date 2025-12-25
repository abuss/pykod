"""AUR (Arch User Repository) configuration."""

from pykod.utils.chroot import exec_chroot

from .base import Repository


class AUR(Repository):
    def __init__(self, **kwargs):
        self.helper = kwargs.get("helper", "yay")
        self.helper_url = kwargs.get("helper_url", "https://aur.archlinux.org/yay.git")
        self.helper_installed = False

    # def install(self, items) -> None:
    #     print("[install] AUR repo:", self)
    #     for item in items:
    #         print(f"  - {item}")

    # def remove(self, items) -> None:
    #     print("[remove] AUR repo:", self)
    #     for item in items:
    #         print(f"  - {item}")

    def build(self, mount_point):
        name = (self.helper,)
        url = (self.helper_url,)
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
        cmd = f"{self.helper} -S --needed --noconfirm {pkgs}"
        return cmd
        # exec_chroot(cmd, mount_point=mount_point)

    def remove_package(self, package_name):
        pkgs = " ".join(package_name)
        cmd = f"{self.helper} -R --noconfirm {pkgs}"
        return cmd
        # exec_chroot(cmd, mount_point=mount_point)

    def update_installed_packages(self) -> str:
        cmd = f"{self.helper} -Syu --noconfirm"
        return cmd
        # exec_chroot(cmd, mount_point=mount_point)

    def update_database(self) -> str:
        cmd = f"{self.helper} -Sy"
        return cmd
        # exec_chroot(cmd, mount_point=mount_point)
