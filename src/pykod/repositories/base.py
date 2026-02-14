"""Base repository configuration classes."""

from abc import ABC, abstractmethod


class PackageList:
    def __init__(self) -> None:
        self._pkgs = {}  # (Repository, [])

    def new(self, repo, items) -> "PackageList":
        self._pkgs = {repo: items}  # (Repository, [])
        return self

    def __add__(self, other_pkgs):
        new_list = PackageList()
        for repo, items in self._pkgs.items():
            if repo in new_list._pkgs:
                new_list._pkgs[repo] += items
            else:
                new_list._pkgs[repo] = items
        for repo, items in other_pkgs._pkgs.items():
            if repo in new_list._pkgs:
                new_list._pkgs[repo] += items
            else:
                new_list._pkgs[repo] = items

        return new_list

    def __len__(self) -> int:
        total = 0
        for items in self._pkgs.values():
            total += len(items)
        return total

    def __iadd__(self, other_pkgs):
        """In-place addition operator (+=) for PackageList.

        Args:
            other_pkgs: Another PackageList to merge into this one

        Returns:
            self: The modified PackageList object
        """
        for repo, items in other_pkgs._pkgs.items():
            if repo in self._pkgs:
                # Merge items from the same repository
                self._pkgs[repo] += items
            else:
                # Add new repository entry
                self._pkgs[repo] = items

        return self

    def __repr__(self) -> str:
        res = "PKGS["
        for repo, pkgs in self._pkgs.items():
            res += f"\n   => {repo.__class__.__name__}: {pkgs}"
        res += "\n]"
        return res

    def items(self):
        for repo, items in self._pkgs.items():
            yield repo, items

    def to_list(self):
        all_items = []
        for items in self._pkgs.values():
            all_items.extend(items)
        return all_items


class Repository(ABC):
    """Abstract base class for all repository types.

    This provides common functionality for package management.
    Subclasses must implement the package management methods.
    """

    def __init__(self):
        self._pkgs = {}

    def __getitem__(self, items) -> PackageList:
        if isinstance(items, (list, tuple)):
            return PackageList().new(self, items)
        return PackageList().new(self, (items,))

    def __repr__(self) -> str:
        return f"{self.__dict__}"

    def packages(self):
        return self._pkgs

    # Abstract methods for package management (ALL repositories)

    @abstractmethod
    def install_packages(self, package_name: set | list) -> str:
        """Return command to install packages.

        Args:
            package_name: Set or list of package names

        Returns:
            str: Command to execute for package installation
        """
        pass

    @abstractmethod
    def remove_packages(self, packages_name: set | list) -> str:
        """Return command to remove packages.

        Args:
            packages_name: Set or list of package names

        Returns:
            str: Command to execute for package removal
        """
        pass

    @abstractmethod
    def update_installed_packages(self, packages: tuple) -> str:
        """Return command to upgrade installed packages.

        Args:
            packages: Tuple of package names to upgrade

        Returns:
            str: Command to execute for package upgrade
        """
        pass

    @abstractmethod
    def is_valid_packages(self, pkgs: list) -> list:
        """Check if packages exist in repository.

        Args:
            pkgs: List of package names to validate

        Returns:
            list: List of validation commands to execute
        """
        pass


class BaseSystemRepository(Repository):
    """Abstract base class for distribution base system repositories.

    Repositories that can perform base system installation (Arch, Debian, etc.)
    must inherit from this class and implement all abstract methods.

    Auxiliary repositories (AUR, Flatpak) should inherit from Repository directly.
    """

    # Abstract methods for base system installation (ONLY base system repos)

    @abstractmethod
    def install_base(self, mount_point: str, packages: PackageList) -> None:
        """Install base system using distribution bootstrap tool.

        Examples:
            - Arch: pacstrap
            - Debian: debootstrap

        Args:
            mount_point: Target installation directory
            packages: PackageList containing base packages to install
        """
        pass

    @abstractmethod
    def get_base_packages(self, conf) -> dict:
        """Get base packages required for this distribution.

        Args:
            conf: Configuration object with system settings

        Returns:
            dict with keys: "kernel" (PackageList), "base" (PackageList)
        """
        pass

    @abstractmethod
    def get_kernel_info(self, mount_point: str, package) -> tuple[str, str]:
        """Retrieve kernel file path and version from package.

        Args:
            mount_point: Installation mount point
            package: Kernel package object

        Returns:
            tuple: (kernel_file_path, kernel_version)
            Example Arch: ("/usr/lib/modules/6.1.0/vmlinuz", "6.1.0")
            Example Debian: ("/boot/vmlinuz-6.1.0-18-amd64", "6.1.0-18-amd64")
        """
        pass

    @abstractmethod
    def setup_linux(self, mount_point: str, kernel_package) -> str:
        """Setup kernel in boot directory.

        Args:
            mount_point: Installation mount point
            kernel_package: Kernel package object

        Returns:
            str: Kernel version string
        """
        pass

    @abstractmethod
    def generate_initramfs(self, mount_point: str, kver: str) -> None:
        """Generate initial ramdisk for kernel.

        Args:
            mount_point: Installation mount point (for chroot execution)
            kver: Kernel version string
        """
        pass

    @abstractmethod
    def update_database(self) -> str:
        """Return command to update package database.

        Returns:
            str: Command to execute for database update
        """
        pass
