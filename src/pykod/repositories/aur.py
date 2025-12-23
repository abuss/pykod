"""AUR (Arch User Repository) configuration."""

# from pykod.config import Install, Rebuild
from .base import Repository


class AUR(Repository):
    def __init__(self, **kwargs):
        self.helper = kwargs.get("helper", "yay")
        self.helper_url = kwargs.get("helper_url", "https://aur.archlinux.org/yay.git")
        self.installed = False

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
        build_cmd = (build_cmd or "makepkg -si --noconfirm",)

        # TODO: Generalize this code to support other distros
        # exec_chroot("pacman -S --needed --noconfirm git base-devel")
        exec_chroot(
            f"runuser -u kod -- /bin/bash -c 'cd && git clone {url} {name} && cd {name} && {build_cmd}'",
            mount_point=mount_point,
        )

    def install_package(self, package_name, mount_point):
        cmd = f"{self.helper} -S --needed --noconfirm {package_name}"
        exec_chroot(cmd, mount_point=mount_point)

    def remove_package(self, package_name, mount_point):
        cmd = f"{self.helper} -R --noconfirm {package_name}"
        exec_chroot(cmd, mount_point=mount_point)

    def update_package_list(self, mount_point):
        cmd = f"{self.helper} -Syu --noconfirm"
        exec_chroot(cmd, mount_point=mount_point)

    def update_database(self, mount_point):
        cmd = f"{self.helper} -Sy"
        exec_chroot(cmd, mount_point=mount_point)
