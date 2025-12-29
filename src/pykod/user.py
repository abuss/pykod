"""User account and user service configuration."""

from dataclasses import dataclass, field

from pykod.common import exec_chroot
from pykod.repositories.base import PackageList

# from typing import Any, KeysView, Optional
from pykod.service import Service

# @dataclass
# class ProgramManager:
#     """Program manager placeholder for user dependency."""

#     programs: dict = field(default_factory=dict)


@dataclass
class OpenSSH:
    """OpenSSH placeholder for user dependency."""

    keys: list[str] = field(default_factory=list)


class ConfigManagerBaee:
    """Configuration manager placeholder for user dependency."""

    def install(self, _config) -> list[str]: ...
    def rebuild(self, _config) -> list[str]: ...

    # def fetch(self, action) -> str: ...


@dataclass
class Stow(ConfigManagerBaee):
    """Stow Dotfile manager."""

    repo_url: str
    target_dir: str | None = None
    source_dir: str | None = None

    def __post_init__(self):
        """Post-initialization processing."""
        if self.target_dir is None:
            self.target_dir = "~/"
        if self.source_dir:
            self.source = self.source_dir
        else:
            self.source = "~/.dotfiles"

    def install(self, _config) -> list[str]:
        """Installing stow ."""
        print("\n[install] Stow:")
        print(f" source_dir: {self.source_dir}")
        print(f" target_dir: {self.target_dir}")
        print(f" repository: {self.repo_url}")
        return self._fetch("init")

    def rebuild(self, _config) -> list[str]:
        print("[rebuild] Updating stow:")
        print("Pull, and re-stow dotfiles.")
        return self._fetch("update")

    def _fetch(self, action) -> list[str]:
        print("[fetch] Fetching dotfiles from repository.")
        cmds = []
        if self.repo_url:
            match action:
                case "init":
                    git_cmd = f"git clone {self.repo_url} {self.source}"
                case "update":
                    git_cmd = f"cd {self.source} && git pull"
                case _:
                    git_cmd = None
            if git_cmd:
                cmds.append(git_cmd)
            print(f"Executing: {git_cmd}")
            return cmds
        else:
            print("No repository URL provided; skipping fetch.")
            return []

    def deploy(self, program_name) -> list[str]:
        print(f"[deploy] Deploying configuration for program: {program_name}")
        cmd = f"stow -d {self.source} -t {self.target_dir} {program_name}"
        print(f"Executing: {cmd}")
        return [cmd]
        # exec_chroot(cmd, mount_point=_config.mount_point)


@dataclass
class UserService:
    """User-level service configuration.

    Args:
        enable: Whether to enable this service for the user
        config: Service-specific configuration
        extra_packages: Additional packages required
    """

    enable: bool
    package: PackageList | None
    config: dict | None = None
    extra_packages: PackageList | None = None

    def __post_init__(self):
        """Post-initialization processing."""
        if not self.enable:
            self.package = None
            self.extra_packages = None


@dataclass
class Program:
    """User program configuration."""

    enable: bool
    package: PackageList | None
    config: dict | list | None = None
    deploy_config: bool = False
    extra_packages: PackageList | None = None

    def __post_init__(self):
        """Post-initialization processing."""
        if not self.enable:
            self.package = None
            self.extra_packages = None


def GitConfig(vars=None, **kwargs):
    config_vargs = vars or kwargs
    cmds = []
    for key, value in config_vargs.items():
        cmd = f'git config --global {key} "{value}"'
        cmds.append(cmd)
    return cmds


def SyncthingConfig(vars=None, **kwargs):
    config_vargs = vars or kwargs
    cmds = []
    for key, value in config_vargs.items():
        if isinstance(value, dict):
            for subkey, subvalue in value.items():
                cmd = f"syncthing cli config {key} {subkey} set {subvalue}"
                cmds.append(cmd)
        else:
            cmd = f"syncthing cli config {key} set {value}"
            cmds.append(cmd)
    return cmds


@dataclass
class User:
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

    username: str
    password: str | None = None
    hashed_password: str | None = None
    groups: list[str] | None = None
    name: str | None = None
    shell: str | None = None
    home: str | None = None
    allow_sudo: bool = False
    ssh_keys: list[str] | None = None
    no_password: bool | None = None
    ssh_authorized: OpenSSH | None = None
    dotfile_manager: ConfigManagerBaee | None = None
    programs: dict[str, Program] | None = None
    deploy_configs: list[str] | None = None
    services: dict[str, Service] | None = None
    home_config: dict | None = None

    # def __init__(self, **kwargs):
    #     """Initialize User."""
    #     super().__init__(**kwargs)

    def install(self, config):
        """Creating a user."""
        # print(f"\n[install] User: {self.username}")
        cmds = self._create()
        for cmd in cmds:
            exec_chroot(cmd, mount_point=config.mount_point)

        print(
            f"\n[install] User: {self.username} {self.dotfile_manager} {type(self.dotfile_manager)}"
        )
        if self.dotfile_manager:
            # if hasattr(self, "dotfile_manager") and self.dotfile_manager is not None:
            # if not isinstance(self.dotfile_manager, NestedDict):
            print(
                f"[install] dotfile manager for user {self.username}: {self.dotfile_manager}",
            )
            cmds = self.dotfile_manager.install(config)
            for cmd in cmds:
                cmd = f"runuser -u {self.username} -- " + cmd
                exec_chroot(cmd, mount_point=config.mount_point)

            # Process user programs
            print(f"\n[install] User Programs for: {self.username}")
            cmds = self._programs()
            for cmd in cmds:
                cmd = f"runuser -u {self.username} -- " + cmd
                exec_chroot(cmd, mount_point=config.mount_point)

            # enable user services
            # TODO: Fix service enabling for users
            print(f"\n[install] User Services for: {self.username}")
            cmds = self._services()
            for cmd in cmds:
                cmd = f"runuser -u {self.username} -- " + cmd
                exec_chroot(cmd, mount_point=config.mount_point)

    def rebuild(self):
        print("[rebuild] Updating user:")
        print(f"\n[install] User: {self.username}")
        print(f" name: {self.name}")
        print(f" shell: {self.shell}")
        print(f" groups: {self.groups}")

    def _create(self) -> list[str]:
        """Create the user in the system."""
        user = self.username
        name = self.name or user
        shell = self.shell or "/bin/bash"
        groups: list = self.groups or []
        cmds = []
        # print(f">>> Creating user {user}")
        # print(
        #     f"Creating user {user} with name '{name}', shell '{shell}', groups {groups}"
        # )
        # Normal users (no root)
        if user != "root":
            # print(f"Creating user {user}")
            cmds.append(f"useradd -m {user} -c '{name}'")
            if groups:
                # TODO: Implement group creation
                if self.allow_sudo:
                    groups.append("wheel")
                    cmds.append(
                        "sed -i 's/# %wheel ALL=(ALL:ALL) ALL/%wheel ALL=(ALL:ALL) ALL/' /etc/sudoers",
                    )
                    cmds.append(
                        "sed -i 's/# auth       required   pam_wheel.so/auth       required   pam_wheel.so/' /etc/pam.d/su",
                    )

                for group in set(groups):
                    try:
                        cmds.append(f"usermod -aG {group} {user}")
                    except Exception:
                        print(f"Group {group} does not exist")

        # Shell
        cmds.append(f"usermod -s {shell} {user}")

        # Password
        no_password = self.no_password == True
        if not no_password:
            if isinstance(self.hashed_password, str):
                # print("Assign the provided password")
                cmds.append(f"usermod -p '{self.hashed_password}' {user}")
            elif isinstance(self.password, str):
                # print("Assign the provided password after encryption")
                cmds.append(f"usermod -p `mkpasswd -m sha-512 {self.password}` {user}")
            else:
                cmds.append(f"passwd {user}")

        # for cmd in cmds:
        #     print(f"Executing: {cmd}")
        #     # ctx.execute(cmd)
        return cmds

    def _programs(self) -> list[str]:
        """Install user programs."""
        cmds = []
        if self.programs:
            for prog_name, prog in self.programs.items():
                if prog.enable:
                    if prog.config:
                        cmds.extend(prog.config)
                    if prog.deploy_config:
                        # print(f"Deploying configuration for program {prog_name}")
                        cmds.extend(self.dotfile_manager.deploy(prog_name))
        if self.deploy_configs:
            # print(f"Deploying user config: {self.deploy_configs}")
            for config in self.deploy_configs:
                cmds.extend(self.dotfile_manager.deploy(config))

        for cmd in cmds:
            print(f"Executing program command: {cmd}")
        return cmds

    def _services(self) -> list[str]:
        """Install user services."""
        cmds = []
        if self.services:
            for service_name, serv in self.services.items():
                if serv.enable:
                    cmd = f"systemctl --user enable {service_name}"
                    cmds.append(cmd)
                    if serv.config:
                        cmds.extend(serv.config)

        for cmd in cmds:
            print(f"Executing program command: {cmd}")
        return cmds


def proc_users(ctx, conf) -> None:
    """
    Process all users in the given configuration.

    For each user, this function creates the user, configures their dotfile manager,
    configures their programs, and enables their services.

    Args:
        ctx (Context): The context object used for executing commands.
        conf (dict): The configuration dictionary containing user information.
    """
    users = conf.users
    # For each user: create user, configure dotfile manager, configure user programs
    for user, info in users.items():
        create_user(ctx, user, info)

        dotfile_mngrs = user_dotfile_manager(info)
        user_configs_def = user_configs(user, info)

        configure_user_dotfiles(ctx, user, user_configs_def, dotfile_mngrs)
        configure_user_scripts(ctx, user, user_configs_def)

        proc_user_home(ctx, user, info)

        services_to_enable = user_services(user, info)
        print(f"User services to enable: {services_to_enable}")
        enable_user_services(ctx, user, services_to_enable)
