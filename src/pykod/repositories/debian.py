"""Debian/Ubuntu repository configuration."""

from pykod.common import execute_chroot as exec_chroot
from pykod.common import execute_command as exec
from pykod.common import get_dry_run

from .base import BaseSystemRepository

GPU_PACKAGES = {
    "nvidia": {
        "base": ["nvidia-driver", "nvidia-settings"],
        "32bit": ["nvidia-driver-libs:i386"],
        "extras": ["nvidia-prime"],
        "open_source": ["xserver-xorg-video-nouveau"],
    },
    "amd": {
        "base": ["xserver-xorg-video-amdgpu", "mesa-vulkan-drivers", "libgl1-mesa-dri"],
        "32bit": ["libgl1-mesa-dri:i386", "mesa-vulkan-drivers:i386"],
        "extras": [],
    },
    "intel": {
        "base": [
            "xserver-xorg-video-intel",
            "mesa-vulkan-drivers",
            "intel-media-va-driver",
        ],
        "32bit": ["libgl1-mesa-dri:i386", "mesa-vulkan-drivers:i386"],
        "extras": ["intel-gpu-tools"],
    },
}


class Debian(BaseSystemRepository):
    def __init__(self, release="stable", variant="debian", components=None, **kwargs):
        """Initialize Debian/Ubuntu repository.

        Args:
            release: Release codename or alias
                    Debian: "stable", "bookworm", "trixie", "testing"
                    Ubuntu: "noble", "jammy", "focal"
            variant: Distribution variant ("debian" or "ubuntu")
            components: Repository components to enable
                       Ubuntu: defaults to ["main", "universe"]
                       Debian: defaults to ["main"]
                       Can be overridden, e.g., ["main", "universe", "multiverse", "restricted"]
            **kwargs: Additional options (mirror_url, etc.)
        """
        self.release = release
        self.variant = variant

        # Set sensible defaults for components based on variant
        if components is None:
            # Ubuntu: enable main and universe (matches Ubuntu Desktop behavior)
            # Debian: only main (minimal, users can add contrib/non-free if needed)
            components = ["main", "universe"] if variant == "ubuntu" else ["main"]

        self.components = components

        # Set appropriate default mirror based on variant
        if variant == "ubuntu":
            default_mirror = "http://archive.ubuntu.com/ubuntu/"
        else:
            default_mirror = "http://deb.debian.org/debian/"

        self.mirror_url = kwargs.get("mirror_url", default_mirror)

    def install_base(self, mount_point, packages):
        """Install base system using debootstrap.

        Args:
            mount_point: Target installation directory
            packages: PackageList containing packages to install
        """
        list_pkgs = packages._pkgs[self]
        print(f"{list_pkgs=}")
        pkgs_str = ",".join(list_pkgs)
        components_str = ",".join(self.components)

        exec(
            f"debootstrap --components={components_str} --include={pkgs_str} {self.release} {mount_point} {self.mirror_url}"
        )

    def install(self, items) -> None:
        print(f"[install] {self.variant.capitalize()} repo:", self)
        for item in items:
            print(f"  - {item}")

    def remove(self, items) -> None:
        print(f"[remove] {self.variant.capitalize()} repo:", self)
        for item in items:
            print(f"  - {item}")

    def get_base_packages(self, conf) -> dict:
        """Get base packages for Debian/Ubuntu.

        Args:
            conf: Configuration object

        Returns:
            dict: Dictionary with "kernel" and "base" PackageLists
        """
        # CPU microcode detection (same logic as Arch, different package names)
        with open("/proc/cpuinfo") as f:
            while True:
                line = f.readline()
                if "AuthenticAMD" in line:
                    microcode = "amd64-microcode"
                    break
                if "GenuineIntel" in line:
                    microcode = "intel-microcode"
                    break

        if conf.boot and conf.boot.kernel and conf.boot.kernel.package:
            kernel_package = conf.boot.kernel.package
        else:
            # Default kernel for Debian/Ubuntu
            kernel_package = self["linux-image-generic"]

        packages = {
            "kernel": kernel_package,
            "base": self[
                "linux-image-generic",
                "linux-firmware",
                microcode,
                "btrfs-progs",
                "bash-completion",
                "plocate",
                "sudo",
                "schroot",
                "whois",
                "dracut",  # For initramfs generation (consistent with Arch)
                "git",
                "systemd-boot",  # For systemd-boot bootloader support
            ],
        }
        return packages

    def get_kernel_info(self, mount_point: str, package):
        """Retrieve the kernel file path and version from the package.

        Debian kernels are located in /boot/vmlinuz-<version> format.

        Args:
            mount_point: Installation mount point
            package: Kernel package object

        Returns:
            tuple: (kernel_file_path, kernel_version)
        """
        print(f"[get_kernel_info] mount_point={mount_point}, package={package}")
        kernel_pkg = package.to_list()[0]

        # Debian: kernel is in /boot/vmlinuz-<version>
        kernel_file = exec_chroot(
            f"dpkg-query -L {kernel_pkg} | grep '/boot/vmlinuz-'",
            mount_point=mount_point,
            get_output=True,
        )

        if get_dry_run():
            kernel_file = "/boot/vmlinuz-6.1.0-18-amd64"

        kernel_file = kernel_file.strip()
        print(f"[get_kernel_info] kernel_file={kernel_file}")

        # Extract version: /boot/vmlinuz-6.1.0-18-amd64 → 6.1.0-18-amd64
        kver = kernel_file.replace("/boot/vmlinuz-", "")
        return kernel_file, kver

    def setup_linux(self, mount_point, kernel_package):
        """Setup Linux kernel for Debian.

        Debian kernels are already installed in /boot by the package manager,
        so we just need to ensure initramfs is generated.

        Args:
            mount_point: Installation mount point
            kernel_package: Kernel package object

        Returns:
            str: Kernel version
        """
        kernel_file, kver = self.get_kernel_info(
            mount_point=mount_point, package=kernel_package
        )
        # Debian kernel already in /boot, just generate initramfs
        self.generate_initramfs(mount_point, kver)
        return kver

    def generate_initramfs(self, mount_point: str, kver: str) -> None:
        """Generate initramfs using dracut.

        Using dracut for consistency with Arch and better compatibility
        with systemd-boot and BTRFS.

        Args:
            mount_point: Installation mount point (for chroot)
            kver: Kernel version string
        """
        exec_chroot(
            f"dracut --kver {kver} --hostonly /boot/initramfs-linux-{kver}.img",
            mount_point=mount_point,
        )

    def install_packages(self, package_name) -> str:
        """Generate apt-get install command.

        Args:
            package_name: List or set of package names

        Returns:
            str: Command to execute
        """
        pkgs = " ".join(package_name)
        cmd = f"DEBIAN_FRONTEND=noninteractive apt-get install -y {pkgs}"
        return cmd

    def remove_packages(self, packages_name: set | list) -> str:
        """Generate apt-get remove command.

        Args:
            packages_name: List or set of package names

        Returns:
            str: Command to execute
        """
        pkgs = " ".join(packages_name)
        cmd = f"DEBIAN_FRONTEND=noninteractive apt-get remove -y {pkgs}"
        return cmd

    def update_installed_packages(self, packages: tuple) -> str:
        """Generate command to upgrade specific packages.

        Args:
            packages: Tuple of package names

        Returns:
            str: Command to execute
        """
        if len(packages) == 0:
            return ""
        pkgs = " ".join(packages)
        cmd = f"DEBIAN_FRONTEND=noninteractive apt-get install --only-upgrade -y {pkgs}"
        return cmd

    def update_database(self) -> str:
        """Generate command to update package database.

        Returns:
            str: Command to execute
        """
        cmd = "apt-get update"
        return cmd

    def list_installed_packages(self):
        """Generate command to list installed packages and versions.

        Returns:
            str: Command to execute
        """
        cmd = "dpkg-query -W -f='${Package} ${Version}\\n'"
        return cmd

    def is_valid_packages(self, pkgs):
        """Check if the given packages exist in apt repositories.

        Returns list of validation commands. If packages don't exist,
        apt-cache will fail with clear error messages at install time.

        Args:
            pkgs: List of package names to validate

        Returns:
            list: List of validation commands to execute
        """
        cmds = []
        for pkg in pkgs:
            cmd_check = f"apt-cache show {pkg}"
            cmds.append(cmd_check)
        return cmds
