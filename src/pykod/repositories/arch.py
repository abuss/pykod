"""Arch Linux repository configuration."""

from pykod.common import execute_chroot as exec_chroot
from pykod.common import execute_command as exec
from pykod.common import get_dry_run

from .base import BaseSystemRepository

GPU_PACKAGES = {
    "nvidia": {
        "base": ["nvidia", "nvidia-utils", "nvidia-settings"],
        "32bit": ["lib32-nvidia-utils"],
        "extras": ["nvidia-prime"],  # For hybrid graphics
        "open_source": ["nouveau"],  # Alternative open-source driver
    },
    "amd": {
        "base": ["xf86-video-amdgpu", "mesa", "vulkan-radeon"],
        "32bit": ["lib32-mesa", "lib32-vulkan-radeon"],
        "extras": [],
    },
    "intel": {
        "base": ["xf86-video-intel", "mesa", "vulkan-intel"],
        "32bit": ["lib32-mesa", "lib32-vulkan-intel"],
        "extras": ["intel-media-driver"],
    },
}


class Arch(BaseSystemRepository):
    def __init__(self, repos=["base", "contrib"], **kwargs):
        # super().__init__(repos=repos, **kwargs)
        self.repos = repos
        self.mirror_url = kwargs.get(
            "mirror_url", "https://mirror.rackspace.com/archlinux/"
        )
        # self.url = f"{self.mirror_url}core/os/x86_64/"

    def install_base(self, mount_point, packages):
        list_pkgs = packages._pkgs[self]
        print(f"{list_pkgs=}")
        exec(f"pacstrap -K {mount_point} {' '.join(list_pkgs)}")

    def install(self, items) -> None:
        print("[install] Arch repo:", self)
        for item in items:
            print(f"  - {item}")

    def remove(self, items) -> None:
        print("[remove] Arch repo:", self)
        for item in items:
            print(f"  - {item}")

    def get_base_packages(self, conf) -> dict:
        """Get the base packages to install for the given configuration."""
        # CPU microcode
        with open("/proc/cpuinfo") as f:
            while True:
                line = f.readline()
                if "AuthenticAMD" in line:
                    microcode = "amd-ucode"
                    break
                if "GenuineIntel" in line:
                    microcode = "intel-ucode"
                    break

        if conf.boot and conf.boot.kernel and conf.boot.kernel.package:
            kernel_package = conf.boot.kernel.package
        else:
            kernel_package = self["linux"]

        packages = {
            "kernel": kernel_package,
            "base": self[
                "base",
                "base-devel",
                microcode,
                "btrfs-progs",
                "linux-firmware",
                "bash-completion",
                "mlocate",
                "sudo",
                "schroot",
                "whois",
                "dracut",
                "git",
            ],
        }
        return packages

    def get_kernel_info(self, mount_point: str, package):
        """Retrieve the kernel file path and version from the specified mount point."""
        print(f"[get_kernel_info] mount_point={mount_point}, package={package}")
        kernel_pkg = package.to_list()[0]
        kernel_file = exec_chroot(
            f"pacman -Ql {kernel_pkg} | grep vmlinuz",
            mount_point=mount_point,
            get_output=True,
        )
        if get_dry_run():
            kernel_file = "linux /usr/lib/modules/6.18.1-kodos1-2/vmlinuz"
        kernel_file = kernel_file.split(" ")[-1].strip()
        print(f"[get_kernel_info] kernel_file={kernel_file}")
        kver = kernel_file.split("/")[-2]
        return kernel_file, kver

    def setup_linux(self, mount_point, kernel_package):
        kernel_file, kver = self.get_kernel_info(
            mount_point=mount_point, package=kernel_package
        )
        exec_chroot(
            f"cp {kernel_file} /boot/efi/vmlinuz-{kver}", mount_point=mount_point
        )
        return kver

    def generate_initramfs(self, mount_point: str, kver: str) -> None:
        """Generate initramfs using dracut (Arch's initramfs generator).

        Args:
            mount_point: Installation mount point for chroot
            kver: Kernel version to generate initramfs for
        """
        exec_chroot(
            f"dracut --kver {kver} --hostonly /boot/efi/initramfs-linux-{kver}.img",
            mount_point=mount_point,
        )

    def install_packages(self, package_name) -> str:
        pkgs = " ".join(package_name)
        cmd = f"pacman -S --needed --noconfirm {pkgs}"
        return cmd

    def remove_packages(self, packages_name: set | list) -> str:
        pkgs = " ".join(packages_name)
        cmd = f"pacman -Rnsc --noconfirm {pkgs}"
        return cmd

    def update_installed_packages(self, packages: tuple) -> str:
        if len(packages) == 0:
            return ""
        pkgs = " ".join(packages)
        cmd = f"pacman -Syu --noconfirm {pkgs}"
        return cmd

    def update_database(self) -> str:
        cmd = "pacman -Syy"
        return cmd

    def list_installed_packages(self):
        """Generate a file containing the list of installed packages and their versions."""
        cmd = "pacman -Q --noconfirm"
        return cmd

    def is_valid_packages(self, pkgs):
        """Check if the given package is valid."""
        cmds = []
        for pkg in pkgs:
            cmd_check = f"pacman -Ss {pkg}"
            cmds.append(cmd_check)
        return cmds

    # def is_valid_packages(self, pkgs):
    #     """Generate a list of packages that do not exist in the repository."""
    #     invalid_pkgs = []
    #     for pkg in pkgs:
    #         output = exec(f"pacman -Ss {pkg}", get_output=True)
    #         if not output.strip():
    #             invalid_pkgs.append(pkg)
    #     return invalid_pkgs
