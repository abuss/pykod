"""User account and user service configuration."""

from dataclasses import dataclass, field
from typing import Any, KeysView, Optional

from pykod.base import NestedDict


@dataclass
class ProgramManager:
    """Program manager placeholder for user dependency."""

    programs: dict = field(default_factory=dict)


@dataclass
class OpenSSH:
    """OpenSSH placeholder for user dependency."""

    keys: list[str] = field(default_factory=list)


class Stow(NestedDict):
    """Stow Dotfile manager."""

    def __init__(self, **kwargs):
        """Initialize Stow."""
        super().__init__(**kwargs)

    def install(self, _config):
        """Installing stow ."""
        print("\n[install] Stow:")
        print(f" source_dir: {self.source_dir}")
        print(f" target_dir: {self.target_dir}")
        print(f" repository: {self.repo_url}")

    def rebuild(self):
        print("[rebuild] Updating stow:")
        print("Pull, and re-stow dotfiles.")


@dataclass
class UserService:
    """User-level service configuration.

    Args:
        enable: Whether to enable this service for the user
        config: Service-specific configuration
        extra_packages: Additional packages required
    """

    enable: bool = False
    config: Optional[dict] = None
    extra_packages: list[str] = field(default_factory=list)


class User(NestedDict):
    """User account configuration.

    Args:
        username: User account name
        password: Plain text password (insecure, use hashed_password instead)
        groups: List of groups the user should belong to
        name: Full name of the user
        shell: Default shell for the user
        home: Home directory path
        allow_sudo: Whether to grant sudo privileges
        ssh_keys: List of SSH public keys for authentication
        hashed_password: Pre-hashed password for secure storage
        no_password: Whether to disable password authentication
        openssh_authorized: OpenSSH authorized keys configuration
        dotfile_manager: Dotfile management configuration
        programs: User programs configuration
        deploy_configs: List of configuration files to deploy
        services: User-level services configuration
        home_config: Home directory configuration settings
    """

    # username: str
    # password: str | None = None
    # groups: list[str] | None = None
    # name: str | None = None
    # shell: str | None = None
    # home: str | None = None
    # allow_sudo: bool = False
    # ssh_keys: list[str] | None = None
    # hashed_password: str | None = None
    # no_password: bool = False
    # ssh_authorized: Optional[OpenSSH] = None
    # dotfile_manager: Optional[DotfileStrategy] = None
    # programs: Optional[ProgramManager] = None
    # deploy_configs: list[str] = field(default_factory=list)
    # services: dict[str, UserService] = field(default_factory=dict)
    # home_config: dict[str, Any] = field(default_factory=dict)
    def __init__(self, **kwargs):
        """Initialize User."""
        super().__init__(**kwargs)

    def install(self, _config):
        """Creating a user."""
        print(f"\n[install] User: {self.username}")
        print(f" name: {self.name}")
        print(f" shell: {self.shell}")
        print(f" groups: {self.groups}")

    def rebuild(self):
        print("[rebuild] Updating user:")
        print(f"\n[install] User: {self.username}")
        print(f" name: {self.name}")
        print(f" shell: {self.shell}")
        print(f" groups: {self.groups}")
