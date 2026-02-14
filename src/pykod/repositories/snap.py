"""Snap package repository configuration.

Snap is a universal Linux package management system developed by Canonical,
working as an auxiliary package source similar to how Flatpak works cross-distro.

Design Pattern:
--------------
Each Snap instance represents a configuration (classic mode, channel, etc.).
Different configurations require separate instances.

Architecture:
------------
- Inherits from Repository (not BaseSystemRepository)
- Cannot bootstrap base system (base comes from Debian/Arch classes)
- Provides snap package installation from snapcraft.io store
- Auto-installs snapd during preparation (matches AUR/Flatpak pattern)

Usage:
-----
    >>> from pykod.repositories import Debian, Snap
    >>>
    >>> ubuntu = Debian(release="noble", variant="ubuntu")
    >>> snap = Snap()  # Regular snaps
    >>> snap_classic = Snap(classic=True)  # Classic confinement
    >>> snap_beta = Snap(channel="beta")  # Beta channel
    >>>
    >>> conf = Configuration(base=ubuntu)
    >>> conf.packages = Packages(
    >>>     ubuntu["git", "vim"],
    >>>     snap["spotify", "discord"],
    >>>     snap_classic["pycharm-professional", "code"]
    >>> )

Preparation:
-----------
During prepare() phase:
1. Installs snapd package via APT
2. Enables snapd.socket systemd service
3. Enables snapd.apparmor service (for confinement)

Confinement Modes:
-----------------
- Regular (default): Confined apps with limited system access
- Classic (classic=True): Full system access (for IDEs, dev tools)
- Devmode: Development mode with relaxed security (not implemented)

Channels:
--------
- stable (default): Production-ready releases
- candidate: Release candidates
- beta: Beta testing releases
- edge: Bleeding-edge development builds
"""

import logging
from pykod.common import execute_chroot as exec_chroot
from .base import Repository

logger = logging.getLogger("pykod.repositories.snap")


class Snap(Repository):
    def __init__(self, **kwargs):
        """Initialize Snap repository.

        Args:
            classic: Allow classic confinement (default: False)
                    Classic snaps have full system access.
                    Use for IDEs, development tools, etc.
            channel: Snap channel to install from (default: "stable")
                    Options: "stable", "candidate", "beta", "edge"

        Examples:
            >>> snap = Snap()  # Regular snaps, stable channel
            >>> snap_classic = Snap(classic=True)  # Classic confinement
            >>> snap_beta = Snap(channel="beta")  # Beta channel
            >>> snap_edge = Snap(classic=True, channel="edge")  # Both
        """
        super().__init__()
        self.classic = kwargs.get("classic", False)
        self.channel = kwargs.get("channel", "stable")
        self._prepared = False

    def prepare(self, mount_point: str) -> None:
        """Prepare Snap support (install and enable snapd).

        This method is called automatically during the package installation
        flow, similar to how Flatpak.prepare() adds remotes.

        Steps:
        1. Install snapd package via APT
        2. Enable snapd.socket systemd service (required for snap to work)
        3. Enable snapd.apparmor service (for snap confinement/security)

        Args:
            mount_point: Installation mount point for chroot execution

        Raises:
            RuntimeError: If snapd installation or service enablement fails

        Note:
            This method is idempotent - safe to call multiple times.
        """
        if self._prepared:
            logger.debug("Snap support already prepared, skipping")
            return

        logger.info("Preparing Snap support...")

        # Step 1: Install snapd package
        logger.debug("Installing snapd package...")
        try:
            exec_chroot(
                "apt-get install -y --no-install-recommends snapd",
                mount_point=mount_point,
            )
            logger.debug("✓ snapd package installed")
        except Exception as e:
            logger.error(f"Failed to install snapd: {e}")
            raise RuntimeError(
                f"Cannot prepare Snap: snapd installation failed. Error: {e}"
            )

        # Step 2: Enable snapd.socket
        logger.debug("Enabling snapd.socket service...")
        try:
            exec_chroot(
                "systemctl enable snapd.socket",
                mount_point=mount_point,
            )
            logger.debug("✓ snapd.socket enabled")
        except Exception as e:
            logger.error(f"Failed to enable snapd.socket: {e}")
            raise RuntimeError(
                f"Cannot prepare Snap: snapd.socket enablement failed. Error: {e}"
            )

        # Step 3: Enable snapd.apparmor (for confinement)
        logger.debug("Enabling snapd.apparmor service...")
        try:
            exec_chroot(
                "systemctl enable snapd.apparmor.service",
                mount_point=mount_point,
            )
            logger.debug("✓ snapd.apparmor enabled")
        except Exception as e:
            # Don't fail on apparmor - some systems might not have it
            logger.warning(f"Could not enable snapd.apparmor: {e}")

        self._prepared = True
        logger.info("✓ Snap support ready")

    def install_packages(self, package_name: set | list) -> str:
        """Generate command to install snap packages.

        Args:
            package_name: Set or list of snap names to install

        Returns:
            str: snap install command with appropriate flags

        Note:
            All packages in one call get the same flags (classic, channel).
            For different configurations, use separate Snap instances.
        """
        pkgs = " ".join(package_name)

        # Build flags based on configuration
        flags = []
        if self.classic:
            flags.append("--classic")
        if self.channel != "stable":
            flags.append(f"--channel={self.channel}")

        flags_str = " ".join(flags) if flags else ""
        return f"snap install {flags_str} {pkgs}".strip()

    def remove_packages(self, packages_name: set | list) -> str:
        """Generate command to remove snap packages.

        Args:
            packages_name: Set or list of snap names to remove

        Returns:
            str: snap remove command string
        """
        pkgs = " ".join(packages_name)
        return f"snap remove {pkgs}"

    def update_installed_packages(self, packages: tuple) -> str:
        """Generate command to refresh (update) snap packages.

        Args:
            packages: Tuple of snap names to refresh
                     If empty, refreshes all installed snaps

        Returns:
            str: snap refresh command string
        """
        if len(packages) == 0:
            return "snap refresh"  # Refresh all

        pkgs = " ".join(packages)
        return f"snap refresh {pkgs}"

    def is_valid_packages(self, pkgs: list) -> list:
        """Generate commands to validate snap existence in store.

        Args:
            pkgs: List of snap names to validate

        Returns:
            list: List of snap info commands to execute
        """
        cmds = []
        for pkg in pkgs:
            cmds.append(f"snap info {pkg}")
        return cmds

    def __repr__(self) -> str:
        """String representation for debugging."""
        classic_str = ", classic=True" if self.classic else ""
        channel_str = f", channel='{self.channel}'" if self.channel != "stable" else ""
        return f"Snap(prepared={self._prepared}{classic_str}{channel_str})"
