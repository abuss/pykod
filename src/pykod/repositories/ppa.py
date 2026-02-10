"""Ubuntu PPA (Personal Package Archive) repository configuration.

PPAs are Ubuntu-specific package repositories hosted on Launchpad that work
as auxiliary package sources, similar to how AUR works for Arch Linux.

Design Pattern:
--------------
Each PPA instance represents one PPA repository. Multiple PPAs require
multiple instances. This provides clarity about package sources.

Architecture:
------------
- Inherits from Repository (not BaseSystemRepository)
- Cannot bootstrap base system (Ubuntu base comes from Debian class)
- Provides package installation from specific PPA
- Auto-prepares during installation flow (matches AUR/Flatpak pattern)

Usage:
-----
    >>> from pykod.repositories import Debian, PPA
    >>>
    >>> ubuntu = Debian(release="noble", variant="ubuntu")
    >>> ppa_graphics = PPA(repo="ppa:graphics-drivers/ppa")
    >>> ppa_python = PPA(repo="ppa:deadsnakes/ppa")
    >>>
    >>> conf = Configuration(base=ubuntu)
    >>> conf.packages = Packages(
    >>>     ubuntu["git", "vim", "build-essential"],
    >>>     ppa_graphics["nvidia-driver-550"],
    >>>     ppa_python["python3.12", "python3.13"]
    >>> )

Preparation:
-----------
During prepare() phase:
1. Installs software-properties-common (provides add-apt-repository)
2. Adds PPA to system sources
3. Updates APT package cache

Package Installation:
--------------------
Standard APT commands used (same as base Ubuntu packages).
"""

import logging
from pykod.common import execute_chroot as exec_chroot
from .base import Repository

logger = logging.getLogger("pykod.repositories.ppa")


class PPA(Repository):
    def __init__(self, repo: str = None, **kwargs):
        """Initialize PPA repository.

        Args:
            repo: PPA identifier in format "ppa:user/repo" or "user/repo"
                 The "ppa:" prefix is added automatically if missing.
            auto_accept_keys: Auto-accept PPA GPG keys (default: True)
                             Set to False to require manual key acceptance.

        Raises:
            ValueError: During prepare() if repo is None

        Examples:
            >>> ppa = PPA(repo="ppa:graphics-drivers/ppa")
            >>> ppa = PPA(repo="deadsnakes/ppa")  # 'ppa:' added automatically
            >>> ppa = PPA(repo="ppa:user/repo", auto_accept_keys=False)
        """
        super().__init__()

        # Normalize PPA name (add ppa: prefix if missing)
        if repo and not repo.startswith("ppa:"):
            repo = f"ppa:{repo}"

        self.repo = repo
        self.auto_accept_keys = kwargs.get("auto_accept_keys", True)
        self._prepared = False

    def prepare(self, mount_point: str) -> None:
        """Prepare PPA repository (install prerequisites and add PPA).

        This method is called automatically during the package installation
        flow, similar to how AUR.prepare() builds the helper.

        Steps:
        1. Install software-properties-common (provides add-apt-repository)
        2. Add PPA to system using add-apt-repository
        3. Update APT package cache

        Args:
            mount_point: Installation mount point for chroot execution

        Raises:
            ValueError: If repo was not specified during __init__
            RuntimeError: If add-apt-repository fails

        Note:
            This method is idempotent - safe to call multiple times.
        """
        if self._prepared:
            logger.debug(f"PPA {self.repo} already prepared, skipping")
            return

        # Validate repository was specified
        if not self.repo:
            raise ValueError(
                "PPA repository not specified. "
                "Initialize with PPA(repo='ppa:user/repo'). "
                "Example: PPA(repo='ppa:graphics-drivers/ppa')"
            )

        logger.info(f"Preparing PPA repository: {self.repo}")

        # Step 1: Install software-properties-common
        logger.debug("Installing software-properties-common...")
        try:
            exec_chroot(
                "apt-get install -y --no-install-recommends software-properties-common",
                mount_point=mount_point,
            )
            logger.debug("✓ software-properties-common installed")
        except Exception as e:
            logger.error(f"Failed to install software-properties-common: {e}")
            raise RuntimeError(
                f"Cannot prepare PPA: software-properties-common installation failed. "
                f"Error: {e}"
            )

        # Step 2: Add PPA repository
        accept_flag = "-y" if self.auto_accept_keys else ""
        logger.debug(f"Adding PPA: {self.repo}")
        try:
            exec_chroot(
                f"add-apt-repository {accept_flag} {self.repo}",
                mount_point=mount_point,
            )
            logger.debug(f"✓ PPA added: {self.repo}")
        except Exception as e:
            logger.error(f"Failed to add PPA {self.repo}: {e}")
            raise RuntimeError(
                f"Failed to add PPA {self.repo}. "
                f"Verify PPA exists and network is available. "
                f"Error: {e}"
            )

        # Step 3: Update APT cache
        logger.debug("Updating APT package cache...")
        try:
            exec_chroot("apt-get update", mount_point=mount_point)
            logger.debug("✓ APT cache updated")
        except Exception as e:
            logger.warning(f"APT cache update failed: {e}")
            # Don't raise - package installation might still work

        self._prepared = True
        logger.info(f"✓ PPA ready: {self.repo}")

    def install_packages(self, package_name: set | list) -> str:
        """Generate command to install packages from PPA.

        Args:
            package_name: Set or list of package names to install

        Returns:
            str: apt-get install command string

        Note:
            The PPA must be prepared (via prepare()) before this command
            will successfully install packages.
        """
        pkgs = " ".join(package_name)
        return f"apt-get install -y --no-install-recommends {pkgs}"

    def remove_packages(self, packages_name: set | list) -> str:
        """Generate command to remove packages.

        Args:
            packages_name: Set or list of package names to remove

        Returns:
            str: apt-get remove command string
        """
        pkgs = " ".join(packages_name)
        return f"apt-get remove -y {pkgs}"

    def update_installed_packages(self, packages: tuple) -> str:
        """Generate command to upgrade packages.

        Args:
            packages: Tuple of package names to upgrade
                     If empty, upgrades all packages

        Returns:
            str: apt-get upgrade command string
        """
        if len(packages) == 0:
            return "apt-get upgrade -y"

        pkgs = " ".join(packages)
        return f"apt-get install -y --only-upgrade {pkgs}"

    def is_valid_packages(self, pkgs: list) -> list:
        """Generate commands to validate package existence.

        Args:
            pkgs: List of package names to validate

        Returns:
            list: List of apt-cache show commands to execute
        """
        cmds = []
        for pkg in pkgs:
            cmds.append(f"apt-cache show {pkg}")
        return cmds

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"PPA(repo='{self.repo}', prepared={self._prepared})"
