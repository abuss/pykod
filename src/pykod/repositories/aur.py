"""AUR (Arch User Repository) configuration."""

from math import e

from _typeshed import ExcInfo

from pykod.common import execute_chroot as exec_chroot
from pykod.common import execute_command

from .base import Repository


class AUR(Repository):
    def __init__(self, **kwargs):
        self.helper = kwargs.get("helper", "yay")
        self.helper_url = kwargs.get("helper_url", "https://aur.archlinux.org/yay.git")
        self.helper_installed = False
        self.skip_debug = kwargs.get("skip_debug", True)

    def build(self, mount_point):
        name = self.helper
        url = self.helper_url
        build_cmd = "makepkg -si --noconfirm"

        # Check if helper is already installed
        helper_check_result = exec_chroot(
            f"runuser -u kod -- /bin/bash -c 'command -v {name}'",
            mount_point=mount_point,
        )

        # If command -v succeeds, it returns the path, so non-empty means it exists
        helper_exists = helper_check_result is not None and bool(
            helper_check_result.strip()
        )

        if helper_exists:
            # Check if helper requires update by checking for newer commits
            update_check_result = exec_chroot(
                f"runuser -u kod -- /bin/bash -c 'cd ~/{name} && git fetch && [ $(git rev-parse HEAD) != $(git rev-parse @{{u}}) ] 2>/dev/null && echo needs_update || echo up_to_date'",
                mount_point=mount_point,
            )
            # If the command outputs "needs_update", then an update is needed
            needs_update = "needs_update" in update_check_result

            if not needs_update:
                return  # Helper is installed and up to date

            # Update existing helper
            exec_chroot(
                f"runuser -u kod -- /bin/bash -c 'cd ~/{name} && git pull && {build_cmd}'",
                mount_point=mount_point,
            )
        else:
            # Install helper for the first time
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

    def install_packages(self, package_name: list) -> str:
        if len(package_name) == 0:
            return ""
        pkgs = " ".join(set(package_name))
        debug_flag = ""
        if self.skip_debug:
            if self.helper in ["paru", "yay"]:
                debug_flag = "--nodebug"
            # For other helpers, we could add more logic here

        cmd = f"runuser -u kod -- {self.helper} -S --needed --noconfirm {debug_flag} {pkgs}".strip()
        return cmd

    def remove_packages(self, package_name: list) -> str:
        if len(package_name) == 0:
            return ""
        pkgs = " ".join(set(package_name))
        cmd = f"runuser -u kod -- {self.helper} -R --noconfirm {pkgs}"
        return cmd

    def cleanup_debug_packages(self, mount_point: str) -> None:
        """Remove any installed debug packages to free up space."""
        if self.skip_debug:
            # Find and remove debug packages
            exec_chroot(
                'runuser -u kod -- /bin/bash -c \'pacman -Q | grep -E "-debug$" | cut -d" " -f1 | xargs -r pacman -R --noconfirm\'',
                mount_point=mount_point,
            )

    def update_installed_packages(self, packages: list) -> str:
        if len(packages) == 0:
            return ""
        pkgs = " ".join(set(packages))
        debug_flag = ""
        if self.skip_debug:
            if self.helper in ["paru", "yay"]:
                debug_flag = "--nodebug"

        cmd = f"runuser -u kod -- {self.helper} -Syu --noconfirm {debug_flag} {pkgs}".strip()
        return cmd

    def update_database(self) -> str:
        cmd = f"{self.helper} -Sy"
        return cmd

    def is_valid_packages(self, pkgs: list) -> list | None:
        """Check if the given package is valid."""

        cmds = []
        try:
            execute_command(f"{self.helper} -h")
            for pkg in pkgs:
                cmd_check = f"{self.helper} -Ss {pkg}"
                cmds.append(cmd_check)
            return cmds
        except Exception as e:
            print(f"{self.helper} is not installed")
            return None
