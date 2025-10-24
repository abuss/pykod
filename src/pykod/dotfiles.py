"""Dotfile management for pykod - three distinct deployment strategies."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
import subprocess
from pathlib import Path
import shutil


@dataclass
class GitRepository:
    """Git repository management for dotfiles.

    Handles cloning, updating, and status checking of Git repositories.

    Args:
        url: Git repository URL
        local_path: Local path where repository should be stored
    """

    url: str
    local_path: str

    def __post_init__(self):
        """Initialize paths."""
        self.local_path = str(Path(self.local_path).expanduser())

    def clone(self) -> bool:
        """Clone the repository.

        Returns:
            True if successful, False otherwise
        """
        if Path(self.local_path).exists():
            return self.update()

        try:
            subprocess.run(
                ["git", "clone", self.url, self.local_path],
                check=True,
                capture_output=True,
                text=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def update(self) -> bool:
        """Update the repository.

        Returns:
            True if successful, False otherwise
        """
        if not (Path(self.local_path) / ".git").exists():
            return False

        try:
            subprocess.run(
                ["git", "-C", self.local_path, "pull"],
                check=True,
                capture_output=True,
                text=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def get_status(self) -> dict[str, Any]:
        """Get repository status information.

        Returns:
            Dictionary with repository status information
        """
        status = {
            "exists": False,
            "is_git": False,
            "branch": "",
            "remote": "",
            "dirty": False,
            "ahead": 0,
            "behind": 0,
        }

        if not Path(self.local_path).exists():
            return status

        status["exists"] = True
        git_dir = Path(self.local_path) / ".git"

        if not git_dir.exists():
            return status

        status["is_git"] = True

        try:
            # Get current branch
            result = subprocess.run(
                ["git", "-C", self.local_path, "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=True,
            )
            status["branch"] = result.stdout.strip()

            # Get remote URL
            result = subprocess.run(
                ["git", "-C", self.local_path, "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                check=True,
            )
            status["remote"] = result.stdout.strip()

            # Check if working directory is dirty
            result = subprocess.run(
                ["git", "-C", self.local_path, "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True,
            )
            status["dirty"] = bool(result.stdout.strip())

        except subprocess.CalledProcessError:
            pass

        return status

    def is_available(self) -> bool:
        """Check if Git is available on the system.

        Returns:
            True if Git is available, False otherwise
        """
        try:
            subprocess.run(["git", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False


class DotfileStrategy(ABC):
    """Abstract base class for dotfile deployment strategies."""

    @abstractmethod
    def deploy(self) -> bool:
        """Deploy dotfiles using this strategy.

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this strategy is available on the system."""
        pass

    @abstractmethod
    def validate_configuration(self) -> dict[str, bool]:
        """Validate the strategy configuration."""
        pass


@dataclass
class StowStrategy(DotfileStrategy):
    """GNU Stow deployment strategy with Git repository support.

    This strategy clones a Git repository and uses GNU Stow to deploy
    the dotfiles from the repository.

    Args:
        repo_url: Git repository URL containing dotfiles
        source_dir: Local directory to clone repository to
        target_dir: Target directory for deployment (usually home directory)
        auto_update: Whether to automatically update repository before deployment

    Example Usage:
        stow = StowStrategy(
            repo_url="https://github.com/user/dotfiles.git",
            source_dir="~/.dotfiles",
            target_dir="~/"
        )
        stow.deploy()
    """

    repo_url: str
    source_dir: str
    target_dir: str = "~/"
    auto_update: bool = True

    def __post_init__(self):
        """Initialize paths and Git repository."""
        self.source_dir = str(Path(self.source_dir).expanduser())
        self.target_dir = str(Path(self.target_dir).expanduser())
        self._git_repo = GitRepository(self.repo_url, self.source_dir)

    def deploy(self) -> bool:
        """Deploy dotfiles using Git + GNU Stow."""
        # Clone or update repository
        if not Path(self.source_dir).exists():
            if not self._git_repo.clone():
                return False
        elif self.auto_update:
            if not self._git_repo.update():
                return False

        # Use Stow to deploy
        try:
            subprocess.run(
                [
                    "stow",
                    "-d",
                    str(Path(self.source_dir).parent),
                    "-t",
                    self.target_dir,
                    Path(self.source_dir).name,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def is_available(self) -> bool:
        """Check if Git and GNU Stow are available."""
        try:
            subprocess.run(["stow", "--version"], capture_output=True, check=True)
            return self._git_repo.is_available()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def validate_configuration(self) -> dict[str, bool]:
        """Validate the Stow strategy configuration."""
        return {
            "git_available": self._git_repo.is_available(),
            "stow_available": self.is_available(),
            "target_dir_exists": Path(self.target_dir).exists(),
            "target_dir_writable": Path(self.target_dir).is_dir() and Path(self.target_dir).exists()
            if Path(self.target_dir).exists()
            else False,
            "repo_url_valid": bool(self.repo_url.strip()),
        }

    @property
    def git_repository(self) -> GitRepository:
        """Access to the Git repository component."""
        return self._git_repo


@dataclass
class GitSymlinkStrategy(DotfileStrategy):
    """Git repository with symbolic link deployment strategy.

    This strategy clones a Git repository and creates symbolic links
    from the repository files to the target directory.

    Args:
        repo_url: Git repository URL containing dotfiles
        source_dir: Local directory to clone repository to
        target_dir: Target directory for deployment
        auto_update: Whether to automatically update repository before deployment
        backup_existing: Whether to backup existing files before deployment

    Example Usage:
        git_symlink = GitSymlinkStrategy(
            repo_url="https://github.com/user/dotfiles.git",
            source_dir="~/.dotfiles",
            target_dir="~/",
            backup_existing=True
        )
        git_symlink.deploy()
    """

    repo_url: str
    source_dir: str
    target_dir: str = "~/"
    auto_update: bool = True
    backup_existing: bool = False
    backup_suffix: str = ".backup"

    def __post_init__(self):
        """Initialize paths and Git repository."""
        self.source_dir = str(Path(self.source_dir).expanduser())
        self.target_dir = str(Path(self.target_dir).expanduser())
        self._git_repo = GitRepository(self.repo_url, self.source_dir)

    def deploy(self) -> bool:
        """Deploy dotfiles using Git + symbolic links."""
        # Clone or update repository
        if not Path(self.source_dir).exists():
            if not self._git_repo.clone():
                return False
        elif self.auto_update:
            if not self._git_repo.update():
                return False

        # Backup existing files if requested
        if self.backup_existing:
            self._backup_existing_files()

        # Create symbolic links
        return self._create_symlinks()

    def is_available(self) -> bool:
        """Git and symlinks are available on all Unix-like systems."""
        return self._git_repo.is_available()

    def validate_configuration(self) -> dict[str, bool]:
        """Validate the Git+symlink strategy configuration."""
        return {
            "git_available": self._git_repo.is_available(),
            "target_dir_exists": Path(self.target_dir).exists(),
            "target_dir_writable": Path(self.target_dir).is_dir() and Path(self.target_dir).exists()
            if Path(self.target_dir).exists()
            else False,
            "repo_url_valid": bool(self.repo_url.strip()),
        }

    def _backup_existing_files(self) -> list[str]:
        """Backup existing files that would be overwritten."""
        backed_up = []
        source_path = Path(self.source_dir)
        target_path = Path(self.target_dir)

        if not source_path.exists():
            return backed_up

        for item in source_path.rglob("*"):
            if item.is_file() and not self._should_ignore(item):
                relative_path = item.relative_to(source_path)
                target_file = target_path / relative_path

                if target_file.exists():
                    backup_file = target_file.with_suffix(
                        target_file.suffix + self.backup_suffix
                    )
                    try:
                        target_file.rename(backup_file)
                        backed_up.append(str(target_file))
                    except OSError:
                        pass

        return backed_up

    def _create_symlinks(self) -> bool:
        """Create symbolic links from source to target directory."""
        source_path = Path(self.source_dir)
        target_path = Path(self.target_dir)

        try:
            for item in source_path.rglob("*"):
                if item.is_file() and not self._should_ignore(item):
                    relative_path = item.relative_to(source_path)
                    target_file = target_path / relative_path

                    # Create parent directories
                    target_file.parent.mkdir(parents=True, exist_ok=True)

                    # Remove existing file/link
                    if target_file.exists() or target_file.is_symlink():
                        target_file.unlink()

                    # Create symlink
                    target_file.symlink_to(item)

            return True
        except OSError:
            return False

    def _should_ignore(self, path: Path) -> bool:
        """Check if a file should be ignored during deployment."""
        ignore_patterns = {".git", ".gitignore", "README.md", "README.rst", ".DS_Store"}
        return any(pattern in str(path) for pattern in ignore_patterns)

    @property
    def git_repository(self) -> GitRepository:
        """Access to the Git repository component."""
        return self._git_repo


@dataclass
class CopyStrategy(DotfileStrategy):
    """File copy deployment strategy.

    This strategy copies files from a source directory to a target directory.
    No Git repository management is involved.

    Args:
        source_dir: Source directory containing dotfiles
        target_dir: Target directory for deployment
        backup_existing: Whether to backup existing files before deployment
        preserve_permissions: Whether to preserve file permissions during copy

    Example Usage:
        copy = CopyStrategy(
            source_dir="/etc/skel",
            target_dir="/home/newuser",
            backup_existing=True
        )
        copy.deploy()
    """

    source_dir: str
    target_dir: str
    backup_existing: bool = False
    backup_suffix: str = ".backup"
    preserve_permissions: bool = True

    def __post_init__(self):
        """Initialize paths and Git repository."""
        self.source_dir = str(Path(self.source_dir).expanduser())
        self.target_dir = str(Path(self.target_dir).expanduser())

    def deploy(self) -> bool:
        """Deploy dotfiles using file copying."""
        if not Path(self.source_dir).exists():
            return False

        # Backup existing files if requested
        if self.backup_existing:
            self._backup_existing_files()

        # Copy files
        return self._copy_files()

    def is_available(self) -> bool:
        """File copying is always available."""
        return True

    def validate_configuration(self) -> dict[str, bool]:
        """Validate the copy strategy configuration."""
        return {
            "source_dir_exists": Path(self.source_dir).exists(),
            "target_dir_exists": Path(self.target_dir).exists(),
            "target_dir_writable": Path(self.target_dir).is_dir() and Path(self.target_dir).exists()
            if Path(self.target_dir).exists()
            else False,
            "source_dir_readable": Path(self.source_dir).is_dir() and Path(self.source_dir).exists()
            if Path(self.source_dir).exists()
            else False,
        }

    def _backup_existing_files(self) -> list[str]:
        """Backup existing files that would be overwritten."""
        backed_up = []
        source_path = Path(self.source_dir)
        target_path = Path(self.target_dir)

        if not source_path.exists():
            return backed_up

        for item in source_path.rglob("*"):
            if item.is_file() and not self._should_ignore(item):
                relative_path = item.relative_to(source_path)
                target_file = target_path / relative_path

                if target_file.exists():
                    backup_file = target_file.with_suffix(
                        target_file.suffix + self.backup_suffix
                    )
                    try:
                        target_file.rename(backup_file)
                        backed_up.append(str(target_file))
                    except OSError:
                        pass

        return backed_up

    def _copy_files(self) -> bool:
        """Copy files from source to target directory."""
        source_path = Path(self.source_dir)
        target_path = Path(self.target_dir)

        try:
            for item in source_path.rglob("*"):
                if item.is_file() and not self._should_ignore(item):
                    relative_path = item.relative_to(source_path)
                    target_file = target_path / relative_path

                    # Create parent directories
                    target_file.parent.mkdir(parents=True, exist_ok=True)

                    # Copy file
                    if self.preserve_permissions:
                        shutil.copy2(item, target_file)
                    else:
                        shutil.copy(item, target_file)

            return True
        except OSError:
            return False

    def _should_ignore(self, path: Path) -> bool:
        """Check if a file should be ignored during deployment."""
        ignore_patterns = {".git", ".gitignore", "README.md", "README.rst", ".DS_Store"}
        return any(pattern in str(path) for pattern in ignore_patterns)


# Convenient aliases for direct import
Stow = StowStrategy
GitSymlink = GitSymlinkStrategy
Copy = CopyStrategy
