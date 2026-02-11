"""Debian/Ubuntu repository configuration.

This module provides a unified implementation for both Debian and Ubuntu
distributions, as they share the same package management system (APT/dpkg)
and installation methodology (debootstrap).

Architecture:
------------
Debian and Ubuntu use identical tooling:
- Bootstrap: debootstrap
- Package manager: apt-get, dpkg
- Initramfs: initramfs-tools (update-initramfs)
- Boot loader: systemd-boot (via systemd-boot package)

Variant Differences:
-------------------
Only three aspects differ between Debian and Ubuntu:

1. Default Components:
   - Debian: ["main"] - Only free software
   - Ubuntu: ["main", "universe"] - Free + community packages

2. Default Mirrors:
   - Debian: http://deb.debian.org/debian/
   - Ubuntu: http://archive.ubuntu.com/ubuntu/

3. Kernel Meta-Packages:
   - Debian: linux-image-amd64 → linux-image-6.1.0-X-amd64
   - Ubuntu: linux-image-generic → linux-image-6.8.0-X-generic

All other functionality (95%+ of code) is identical.

Ubuntu-Specific Features:
------------------------
Ubuntu-specific package sources are implemented as auxiliary repositories
(following the AUR/Flatpak pattern):

- PPA (pykod.repositories.PPA): Personal Package Archives
- Snap (pykod.repositories.Snap): Snap packages

These can be mixed freely with the base Debian repository.

Examples:
--------
Debian system:
    >>> from pykod.repositories import Debian
    >>> debian = Debian(release="bookworm", variant="debian")
    >>> conf = Configuration(base=debian)

Ubuntu system:
    >>> ubuntu = Debian(release="noble", variant="ubuntu")
    >>> conf = Configuration(base=ubuntu)

Ubuntu with auxiliary repositories:
    >>> from pykod.repositories import Debian, PPA, Snap
    >>> ubuntu = Debian(release="noble", variant="ubuntu")
    >>> ppa = PPA(repo="ppa:graphics-drivers/ppa")
    >>> snap = Snap()
    >>>
    >>> conf.packages = Packages(
    >>>     ubuntu["git", "vim"],
    >>>     ppa["nvidia-driver-550"],
    >>>     snap["spotify"]
    >>> )

GRUB Prevention:
---------------
This module implements a 4-layer GRUB prevention system for systemd-boot:
1. APT preferences (pin priority -1)
2. Kernel hook diversion (dpkg-divert)
3. Post-debootstrap verification
4. Pre-bootloader verification

See block_grub_installation() and related functions for details.

Service Management During Installation:
---------------------------------------
Uses policy-rc.d to prevent services from starting during chroot installation:
- Prevents "invoke-rc.d: initscript" errors during apt operations
- Services are properly started on first boot by systemd
- policy-rc.d is removed after package installation completes

See prevent_service_start() and allow_service_start() for details.
"""

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


def prevent_service_start(mount_point: str) -> None:
    """Prevent services from starting during package installation.

    Creates a policy-rc.d file that blocks all service starts in the chroot.
    This prevents errors like "invoke-rc.d: initscript dbus" during apt installs.

    Args:
        mount_point: Installation mount point

    Note:
        This is standard practice for chroot installations. Services will be
        properly started on first boot by systemd.
    """
    logger.info("Creating policy-rc.d to prevent service starts during installation...")

    try:
        policy_file = Path(mount_point) / "usr/sbin/policy-rc.d"

        # Create the policy script that denies all service starts
        policy_content = """#!/bin/sh
# pykod: Prevent services from starting during installation
# Services will be started properly on first boot by systemd
exit 101
"""

        with open(policy_file, "w") as f:
            f.write(policy_content)

        # Make it executable
        policy_file.chmod(0o755)

        logger.info("✓ Service starts blocked via policy-rc.d")

    except Exception as e:
        # Warn but continue - not critical
        logger.warning(f"Failed to create policy-rc.d: {e}")
        logger.warning("Service start warnings may appear during installation")


def allow_service_start(mount_point: str) -> None:
    """Remove policy-rc.d to allow services to start normally.

    Removes the policy-rc.d file created by prevent_service_start().
    Should be called after all package installations are complete.

    Args:
        mount_point: Installation mount point
    """
    logger.info("Removing policy-rc.d to allow normal service management...")

    try:
        policy_file = Path(mount_point) / "usr/sbin/policy-rc.d"

        if policy_file.exists():
            policy_file.unlink()
            logger.info("✓ Service management restored")
        else:
            logger.debug("policy-rc.d not found (already removed or never created)")

    except Exception as e:
        # Warn but continue
        logger.warning(f"Failed to remove policy-rc.d: {e}")
        logger.warning("Services may not start properly on first boot")


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
            components = self._get_default_components()

        self.components = components

        # Set appropriate default mirror based on variant
        self.mirror_url = kwargs.get("mirror_url", self._get_default_mirror())

    def _get_default_components(self) -> list[str]:
        """Get default repository components for this variant.

        Returns:
            list: Repository components to enable
                - Debian: ["main"] - minimal, user adds contrib/non-free if needed
                - Ubuntu: ["main", "universe"] - matches Ubuntu Desktop behavior
        """
        return ["main", "universe"] if self.variant == "ubuntu" else ["main"]

    def _get_default_mirror(self) -> str:
        """Get default mirror URL for this variant.

        Returns:
            str: Default mirror URL
                - Debian: http://deb.debian.org/debian/
                - Ubuntu: http://archive.ubuntu.com/ubuntu/
        """
        if self.variant == "ubuntu":
            return "http://archive.ubuntu.com/ubuntu/"
        return "http://deb.debian.org/debian/"

    def _get_default_kernel_package_name(self) -> str:
        """Get default kernel meta-package name for this variant.

        Returns:
            str: Kernel package name
                - Debian: linux-image-amd64 (Debian kernel meta-package)
                - Ubuntu: linux-image-generic (Ubuntu kernel meta-package)

        Note:
            These are meta-packages that automatically pull the latest kernel.
            Actual installed kernel will be like:
            - Debian: linux-image-6.1.0-18-amd64
            - Ubuntu: linux-image-6.8.0-48-generic
        """
        if self.variant == "debian":
            return "linux-image-amd64"
        return "linux-image-generic"

    def install_base(self, mount_point, packages):
        """Install base system using debootstrap.

        Args:
            mount_point: Target installation directory
            packages: PackageList containing packages to install
        """
        list_pkgs = packages._pkgs[self]
        logger.info(f"=== Base Package Installation ===")
        logger.info(f"Total packages to install: {len(list_pkgs)}")
        logger.info(f"Package list: {', '.join(list_pkgs)}")

        # Verify kernel package is in the list
        kernel_pkgs = [pkg for pkg in list_pkgs if "linux-image" in pkg]
        if kernel_pkgs:
            logger.info(f"✓ Kernel packages found in list: {', '.join(kernel_pkgs)}")
        else:
            logger.error("✗ NO kernel package found in package list!")
            logger.error("This is a bug - kernel should be included in base packages")
            raise RuntimeError("Kernel package missing from installation list")

        pkgs_str = " ".join(list_pkgs)
        components_str = ",".join(self.components)

        # Step 1: Run debootstrap (minimal base system)
        logger.info(f"Running debootstrap for {self.variant} {self.release}...")
        # Note: debootstrap works identically for Debian and Ubuntu
        # The variant only affects package selection and mirror URL
        exec(
            f"debootstrap --components={components_str} {self.release} {mount_point} {self.mirror_url}"
        )

        # Step 2: Prevent services from starting during installation
        prevent_service_start(mount_point)

        # Step 3: CRITICAL - Block GRUB before installing any packages
        block_grub_installation(mount_point)

        # Step 4: Disable GRUB kernel hooks
        disable_grub_kernel_hooks(mount_point)

        # Step 5: Install base packages
        # Note: We allow recommended packages to ensure kernel dependencies (like linux-firmware)
        # are installed. GRUB is still blocked via APT preferences (Step 3).
        # Note: You may see "invoke-rc.d: policy-rc.d denied execution" messages - these are
        # expected and indicate that services are correctly blocked during installation.
        logger.info("Installing base packages (with GRUB blocked)...")
        try:
            exec_chroot(
                f"apt-get install -y {pkgs_str}",
                mount_point=mount_point,
            )
        except Exception as e:
            logger.error(f"apt-get install failed: {e}")
            logger.error(f"Failed to install packages: {pkgs_str}")
            logger.error("Check apt sources and network connectivity")
            raise RuntimeError(f"Base package installation failed: {e}") from e

        # Step 5.5: Complete package configuration
        # Sometimes packages are left in "half-configured" or "unpacked" state
        # This completes any pending configurations
        # Set PATH to include /sbin and /usr/sbin for ldconfig, start-stop-daemon, etc.
        logger.info("Completing package configuration...")
        try:
            result = exec_chroot(
                "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin dpkg --configure -a 2>&1",
                mount_point=mount_point,
                get_output=True,
            )
            logger.debug(f"dpkg --configure -a output:\n{result}")
            logger.info("✓ Package configuration completed")
        except Exception as e:
            logger.error(f"dpkg --configure -a failed: {e}")
            # Try to get more diagnostic information
            logger.error("Checking dpkg status...")
            try:
                dpkg_status = exec_chroot(
                    "dpkg --configure -a 2>&1 || true",
                    mount_point=mount_point,
                    get_output=True,
                )
                logger.error(f"dpkg error output:\n{dpkg_status}")
            except:
                pass
            logger.warning("Continuing anyway - this may cause issues later")

        # Step 6: Verify GRUB was not installed
        verify_grub_not_installed_debian(mount_point)

        # Step 7: Verify kernel package was installed
        logger.info("Verifying kernel package installation...")

        # First, check all installed packages
        all_packages = exec_chroot(
            "dpkg -l",
            mount_point=mount_point,
            get_output=True,
        )
        logger.debug(f"Total dpkg output length: {len(all_packages)} characters")

        # Check for linux-image packages specifically
        kernel_check = exec_chroot(
            "dpkg -l | grep '^ii.*linux-image' || true",
            mount_point=mount_point,
            get_output=True,
        ).strip()

        logger.debug(f"Kernel check result: '{kernel_check}'")
        logger.debug(f"Kernel check result length: {len(kernel_check)}")

        # Alternative check: use dpkg-query directly
        kernel_check_alt = exec_chroot(
            "dpkg-query -W -f='${Package} ${Version} ${Status}\n' 'linux-image-*' 2>/dev/null || true",
            mount_point=mount_point,
            get_output=True,
        ).strip()
        logger.debug(f"Alternative kernel check: '{kernel_check_alt}'")

        # Check for improperly configured packages
        if kernel_check_alt and "half-configured" in kernel_check_alt:
            logger.warning("Kernel packages are in 'half-configured' state!")
            logger.warning("This usually means package configuration failed")
            logger.warning("Attempting to reconfigure packages with full PATH...")
            try:
                result = exec_chroot(
                    "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin dpkg --configure -a 2>&1",
                    mount_point=mount_point,
                    get_output=True,
                )
                logger.debug(f"Reconfiguration output:\n{result}")
                # Re-check after reconfiguration
                kernel_check_alt = exec_chroot(
                    "dpkg-query -W -f='${Package} ${Version} ${Status}\n' 'linux-image-*' 2>/dev/null || true",
                    mount_point=mount_point,
                    get_output=True,
                ).strip()
                logger.info(f"After reconfiguration: {kernel_check_alt}")

                # If still half-configured, get detailed error info
                if "half-configured" in kernel_check_alt:
                    logger.error(
                        "Kernel packages STILL half-configured after reconfiguration!"
                    )
                    logger.error("Checking for package configuration errors...")
                    # Check dpkg log for errors
                    dpkg_log = exec_chroot(
                        "tail -100 /var/log/dpkg.log 2>/dev/null || echo 'No dpkg.log'",
                        mount_point=mount_point,
                        get_output=True,
                    )
                    logger.error(f"Recent dpkg log entries:\n{dpkg_log}")
            except Exception as e:
                logger.error(f"Failed to reconfigure packages: {e}")

        if not kernel_check and not kernel_check_alt:
            logger.error("No kernel package found after base installation!")
            logger.error("This likely means the kernel package installation failed.")
            logger.error("Checking what packages were actually installed...")

            # Show what WAS installed
            installed = exec_chroot(
                "dpkg -l | grep '^ii' | wc -l",
                mount_point=mount_point,
                get_output=True,
            ).strip()
            logger.error(f"Total packages installed: {installed}")

            # Check if linux-image-generic meta-package exists in repos
            available = exec_chroot(
                "apt-cache show linux-image-generic 2>&1 | head -5 || true",
                mount_point=mount_point,
                get_output=True,
            ).strip()
            logger.error(f"linux-image-generic availability:\n{available}")

            raise RuntimeError(
                "Kernel package installation failed. No linux-image package found. "
                "Review the base package installation logs for errors."
            )

        logger.info(
            f"✓ Kernel package(s) installed:\n{kernel_check or kernel_check_alt}"
        )

        # Step 8: Allow services to start on first boot
        allow_service_start(mount_point)

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
            kernel_package = self[self._get_default_kernel_package_name()]
            # Kernel package names differ between distributions:
            # - Debian: -amd64 suffix (architecture-specific)
            # - Ubuntu: -generic suffix (hardware-agnostic)
            # Both are meta-packages that track the latest stable kernel

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
