"""Debian/Ubuntu repository configuration."""

import logging
from pathlib import Path

from pykod.common import execute_chroot as exec_chroot
from pykod.common import execute_command as exec
from pykod.common import get_dry_run

from .base import BaseSystemRepository

logger = logging.getLogger("pykod.config")

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


def block_grub_installation(mount_point: str) -> None:
    """Prevent GRUB from being installed via APT preferences.

    Creates APT pinning configuration before any package installation
    to ensure GRUB cannot be pulled in as a dependency or recommendation.

    Args:
        mount_point: Installation mount point

    Raises:
        OSError: If preferences directory cannot be created or file cannot be written
    """
    logger.info("Creating APT preferences to block GRUB installation...")

    try:
        # Create preferences directory if it doesn't exist
        prefs_dir = Path(mount_point) / "etc/apt/preferences.d"
        prefs_dir.mkdir(parents=True, exist_ok=True)

        # APT pinning configuration to block all grub packages
        grub_block_config = """# pykod: Block GRUB installation for systemd-boot compatibility
# This prevents GRUB from being installed as a dependency or recommendation
Package: grub*
Pin: release *
Pin-Priority: -1

Package: grub-common
Pin: release *
Pin-Priority: -1

Package: grub2-common
Pin: release *
Pin-Priority: -1

Package: grub-efi-amd64
Pin: release *
Pin-Priority: -1

Package: grub-efi-amd64-bin
Pin: release *
Pin-Priority: -1
"""

        prefs_file = prefs_dir / "99-no-grub"
        with open(prefs_file, "w") as f:
            f.write(grub_block_config)

        # Verify the file was created successfully
        if not prefs_file.exists():
            raise OSError(f"Failed to create GRUB preferences file at {prefs_file}")

        logger.debug(f"GRUB blocking preferences created at {prefs_file}")
        logger.info("✓ GRUB installation blocked via APT preferences")

    except Exception as e:
        logger.error(f"Failed to create GRUB blocking preferences: {e}")
        raise


def disable_grub_kernel_hooks(mount_point: str) -> None:
    """Disable kernel hooks that expect GRUB to be present.

    Uses dpkg-divert to prevent kernel post-install/remove scripts
    from trying to update GRUB configuration.

    Args:
        mount_point: Installation mount point

    Note:
        This function does not raise exceptions - hook diversion failures
        are logged as warnings since the APT preferences should prevent
        GRUB installation regardless.
    """
    logger.info("Disabling GRUB-related kernel hooks...")

    hooks_to_disable = [
        "/etc/kernel/postinst.d/zz-update-grub",
        "/etc/kernel/postrm.d/zz-update-grub",
    ]

    diverted_count = 0
    for hook in hooks_to_disable:
        try:
            # Check if hook exists
            hook_path = Path(mount_point) / hook.lstrip("/")
            if hook_path.exists():
                # Divert the hook (disable it)
                exec_chroot(
                    f"dpkg-divert --add --rename --divert {hook}.dpkg-divert {hook}",
                    mount_point=mount_point,
                )
                logger.debug(f"Diverted hook: {hook}")
                diverted_count += 1
            else:
                logger.debug(f"Hook not present, skipping: {hook}")
        except Exception as e:
            # Warn but continue - not critical if APT preferences work
            logger.warning(f"Failed to divert {hook}: {e}")

    if diverted_count > 0:
        logger.info(f"✓ Diverted {diverted_count} GRUB kernel hook(s)")
    else:
        logger.info(
            "No GRUB kernel hooks found to divert (this is normal for minimal installs)"
        )


def verify_grub_not_installed_debian(mount_point: str) -> None:
    """Verify that GRUB was not installed during package installation.

    This is a safety check to ensure the APT preferences worked correctly.

    Args:
        mount_point: Installation mount point

    Raises:
        RuntimeError: If GRUB packages are found installed
    """
    logger.info("Verifying GRUB was not installed...")

    try:
        # Check for any installed GRUB packages
        result = exec_chroot(
            "dpkg -l 2>/dev/null | grep -i '^ii.*grub' || true",
            mount_point=mount_point,
            get_output=True,
        )

        if result and result.strip():
            # GRUB packages found - this is a critical error
            installed_packages = result.strip().split("\n")
            logger.error("GRUB packages were installed despite APT preferences!")
            logger.error("Installed GRUB packages:")
            for pkg in installed_packages:
                logger.error(f"  {pkg}")
            raise RuntimeError(
                "GRUB packages found installed. APT preferences failed to block installation. "
                "This will cause conflicts with systemd-boot."
            )

        logger.info("✓ Verified: No GRUB packages installed")

    except RuntimeError:
        # Re-raise RuntimeError from GRUB detection
        raise
    except Exception as e:
        # Other errors during verification - warn but don't fail
        logger.warning(f"Could not verify GRUB absence: {e}")
        logger.warning("Continuing anyway - check manually if issues occur")


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
        logger.debug(f"Packages to install: {list_pkgs}")
        pkgs_str = " ".join(list_pkgs)
        components_str = ",".join(self.components)

        # Step 1: Run debootstrap (minimal base system)
        logger.info(f"Running debootstrap for {self.variant} {self.release}...")
        exec(
            f"debootstrap --components={components_str} {self.release} {mount_point} {self.mirror_url}"
        )

        # Step 2: CRITICAL - Block GRUB before installing any packages
        block_grub_installation(mount_point)

        # Step 3: Disable GRUB kernel hooks
        disable_grub_kernel_hooks(mount_point)

        # Step 4: Install packages with --no-install-recommends
        logger.info("Installing base packages (with GRUB blocked)...")
        exec_chroot(
            f"DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends {pkgs_str}",
            mount_point=mount_point,
        )

        # Step 5: Verify GRUB was not installed
        verify_grub_not_installed_debian(mount_point)

        logger.info("Base system installation completed")

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
            # Default kernel varies by distribution variant
            if self.variant == "debian":
                kernel_package = self["linux-image-amd64"]  # Debian meta-package
            else:  # Ubuntu
                kernel_package = self["linux-image-generic"]  # Ubuntu meta-package

        logger.debug(
            f"Selected kernel package for {self.variant}: {kernel_package.to_list()}"
        )

        packages = {
            "kernel": kernel_package,
            "base": self[
                # "linux-image-generic",
                # "linux-firmware",
                microcode,
                "btrfs-progs",
                "bash-completion",
                # "plocate",
                "sudo",
                "passwd",  # Provides usermod, useradd, etc. (essential user management)
                # "schroot",  # TODO: need to be removed
                "whois",  # Provides mkpasswd for password hashing
                "initramfs-tools",  # Debian's native initramfs generator
                "git",
                "systemd",
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

        Raises:
            RuntimeError: If kernel cannot be found or version cannot be extracted
        """
        logger.info(f"Detecting installed kernel from package {package}...")
        kernel_pkg = package.to_list()[0]

        # Method 1: Query package files
        kernel_file = exec_chroot(
            f"dpkg-query -L {kernel_pkg} 2>/dev/null | grep '/boot/vmlinuz-' || true",
            mount_point=mount_point,
            get_output=True,
        )

        if get_dry_run():
            kernel_file = "/boot/vmlinuz-6.1.0-18-amd64"

        kernel_file = kernel_file.strip()
        logger.debug(f"dpkg-query result: '{kernel_file}'")

        # Method 2: Fallback - search filesystem directly
        if not kernel_file:
            logger.warning(
                f"Package query failed for {kernel_pkg}, searching filesystem..."
            )
            kernel_file = exec_chroot(
                "ls -1 /boot/vmlinuz-* 2>/dev/null | head -1 || true",
                mount_point=mount_point,
                get_output=True,
            ).strip()
            logger.debug(f"Filesystem search result: '{kernel_file}'")

        # Validation: Ensure we found a kernel
        if not kernel_file:
            # Check if package is actually installed
            pkg_check = exec_chroot(
                f"dpkg -l {kernel_pkg} 2>/dev/null | grep '^ii' || true",
                mount_point=mount_point,
                get_output=True,
            ).strip()

            if not pkg_check:
                raise RuntimeError(
                    f"Kernel package '{kernel_pkg}' is not installed. "
                    f"Base package installation may have failed. "
                    f"Check logs for apt-get errors during Step 2 (Base packages)."
                )
            else:
                raise RuntimeError(
                    f"Kernel package '{kernel_pkg}' is installed but no vmlinuz file found. "
                    f"Package may be corrupted or incomplete. "
                    f"Found in dpkg: {pkg_check}"
                )

        logger.info(f"✓ Found kernel: {kernel_file}")

        # Extract version: /boot/vmlinuz-6.1.0-18-amd64 → 6.1.0-18-amd64
        kver = kernel_file.replace("/boot/vmlinuz-", "")

        if not kver:
            raise RuntimeError(
                f"Failed to extract kernel version from '{kernel_file}'. "
                f"Expected format: /boot/vmlinuz-<version>"
            )

        logger.debug(f"Extracted kernel version: {kver}")
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
        """Generate initramfs using Debian's native update-initramfs tool.

        Uses update-initramfs instead of dracut for better compatibility with
        Debian/Ubuntu kernel packages and their post-install hooks.

        Args:
            mount_point: Installation mount point (for chroot)
            kver: Kernel version string

        Raises:
            ValueError: If kver is empty
            RuntimeError: If update-initramfs command not found or generation fails
        """
        if not kver:
            raise ValueError(
                "Kernel version is empty. Cannot generate initramfs. "
                "This indicates kernel detection failed."
            )

        logger.info(f"Generating initramfs for kernel {kver} using update-initramfs...")

        # Verify update-initramfs exists
        check_cmd = exec_chroot(
            "which update-initramfs || echo 'NOT_FOUND'",
            mount_point=mount_point,
            get_output=True,
        ).strip()

        if check_cmd == "NOT_FOUND":
            raise RuntimeError(
                "update-initramfs command not found. "
                "Ensure 'initramfs-tools' package was installed during base setup."
            )

        # Generate initramfs using Debian's tool
        # -c = create, -k = kernel version
        try:
            exec_chroot(
                f"update-initramfs -c -k {kver}",
                mount_point=mount_point,
            )
        except Exception as e:
            logger.error(f"Failed to generate initramfs for kernel {kver}: {e}")
            raise RuntimeError(
                f"update-initramfs failed for kernel {kver}. "
                f"Check if kernel modules are properly installed. "
                f"Error: {e}"
            ) from e

        # Debian creates: /boot/initrd.img-{kver}
        # pykod expects: /boot/initramfs-linux-{kver}.img
        # Create symlink for compatibility
        logger.debug("Creating pykod-compatible initramfs symlink...")
        exec_chroot(
            f"ln -sf /boot/initrd.img-{kver} /boot/initramfs-linux-{kver}.img",
            mount_point=mount_point,
        )

        # Verify the initramfs was created
        verify_cmd = exec_chroot(
            f"test -f /boot/initrd.img-{kver} && echo 'OK' || echo 'MISSING'",
            mount_point=mount_point,
            get_output=True,
        ).strip()

        if verify_cmd == "MISSING":
            raise RuntimeError(
                f"Initramfs file /boot/initrd.img-{kver} not found after generation. "
                f"update-initramfs may have failed silently."
            )

        logger.info(f"✓ Initramfs generated successfully: /boot/initrd.img-{kver}")

    def install_packages(self, package_name) -> str:
        """Generate apt-get install command.

        Args:
            package_name: List or set of package names

        Returns:
            str: Command to execute
        """
        pkgs = " ".join(package_name)
        cmd = f"apt-get install -y {pkgs}"
        return cmd

    def remove_packages(self, packages_name: set | list) -> str:
        """Generate apt-get remove command.

        Args:
            packages_name: List or set of package names

        Returns:
            str: Command to execute
        """
        pkgs = " ".join(packages_name)
        cmd = f"apt-get remove -y {pkgs}"
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
        cmd = f"apt-get install --only-upgrade -y {pkgs}"
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
