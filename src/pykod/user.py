"""User account and user service configuration."""

from dataclasses import dataclass, field

from pykod.common import execute_chroot, execute_command
from pykod.core import File
from pykod.repositories.base import PackageList
from pykod.service import Service


@dataclass
class OpenSSH:
    """OpenSSH placeholder for user dependency."""

    keys: list[str] = field(default_factory=list)


class ConfigManagerBase:
    """Configuration manager placeholder for user dependency."""

    def install(self, _config) -> list[str]: ...
    def rebuild(self, _config) -> list[str]: ...


@dataclass
class Stow(ConfigManagerBase):
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
        cmd = f"cd {self.source} && stow {program_name} || echo 'Stow failed for {program_name}'"
        print(f"Executing: {cmd}")
        return [cmd]


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
    dotfile_manager: ConfigManagerBase | None = None
    programs: dict[str, Program] | None = None
    deploy_configs: list[str] | None = None
    services: dict[str, Service] | None = None
    home_config: dict | None = None
    extra_shell_init: str | None = None
    environment_vars: dict | None = None
    file: File | None = None
    _config = None

    def install(self, config):
        """Creating a user."""
        self._config = config
        cmds = self._create()
        for cmd in cmds:
            execute_chroot(cmd, mount_point=config._mount_point)

        print(
            f"\n[install] User: {self.username} {self.dotfile_manager} {type(self.dotfile_manager)}"
        )

        # Apply environment variables and shell init before dotfiles/programs
        env_cmds = self._apply_environment_vars()
        for cmd in env_cmds:
            cmd = f"runuser -u {self.username} -- " + cmd
            execute_chroot(cmd, mount_point=config._mount_point)

        shell_cmds = self._apply_extra_shell_init()
        for cmd in shell_cmds:
            cmd = f"runuser -u {self.username} -- " + cmd
            execute_chroot(cmd, mount_point=config._mount_point)

        if self.dotfile_manager:
            print(
                f"[install] dotfile manager for user {self.username}: {self.dotfile_manager}",
            )
            cmds = self.dotfile_manager.install(config)
            for cmd in cmds:
                cmd = cmd.replace("~", f"/home/{self.username}")
                cmd = f"runuser -u {self.username} -- " + cmd
                execute_chroot(cmd, mount_point=config._mount_point)

            # Process user programs
            print(f"\n[install] User Programs for: {self.username}")
            cmds = self._programs()
            for cmd in cmds:
                cmd = f"runuser -u {self.username} -- " + cmd
                execute_chroot(cmd, mount_point=config._mount_point)

            if self.file:
                print(f"\n[install] User Files for: {self.username}")
                # cmds = self.file.install(config)
                if cmds := self.file.build_command():
                    for cmd in cmds:
                        cmd = f"runuser -u {self.username} -- " + cmd
                        execute_chroot(cmd, mount_point=config._mount_point)

            # enable user services
            # TODO: Fix service enabling for users
            print(f"\n[install] User Services for: {self.username}")
            cmds = self._services()
            for cmd in cmds:
                cmd = f"runuser -u {self.username} -- " + cmd
                execute_chroot(cmd, mount_point=config._mount_point)

    def rebuild(self):
        print("[rebuild] Updating user:")
        print(f"\n[install] User: {self.username}")
        print(f" name: {self.name}")
        print(f" shell: {self.shell}")
        print(f" groups: {self.groups}")

        # Re-apply env and shell init (idempotent blocks)
        for cmd in self._apply_environment_vars():
            print(f"Executing rebuild env command: {cmd}")
            execute_command(cmd)
        for cmd in self._apply_extra_shell_init():
            print(f"Executing rebuild shell-init command: {cmd}")
            execute_command(cmd)

        if self.dotfile_manager:
            print(
                f"[rebuild] dotfile manager for user {self.username}: {self.dotfile_manager}"
            )
            cmds = self.dotfile_manager.rebuild(None)
            for cmd in cmds:
                cmd = cmd.replace("~", f"/home/{self.username}")
                print(f"Executing rebuild dotfile command: {cmd}")
                execute_command(cmd)

        # Check and update user configuration differences
        print(f"[rebuild] Checking user configuration differences for: {self.username}")

        # Check shell differences
        # from pykod.common import execute_command

        try:
            current_shell = (
                execute_command(f"getent passwd {self.username}").strip().split(":")[-1]
            )
            expected_shell = self.shell or "/bin/bash"
            if current_shell != expected_shell:
                print(
                    f"Shell mismatch: current={current_shell}, expected={expected_shell}"
                )
                cmd = f"usermod -s {expected_shell} {self.username}"
                # print(f"Executing: usermod -s {expected_shell} {self.username}")
                execute_command(cmd)
        except Exception:
            print(f"Could not get current shell for user {self.username}")

        # Check group membership differences
        if self.groups:
            try:
                current_groups = (
                    execute_command(f"groups {self.username}")
                    .strip()
                    .split(":")[-1]
                    .split()
                )
                expected_groups = set(self.groups)
                if self.allow_sudo:
                    expected_groups.add("wheel")
                current_groups_set = set(current_groups)

                missing_groups = expected_groups - current_groups_set
                for group in missing_groups:
                    print(f"Adding user {self.username} to missing group: {group}")
                    cmd = f"usermod -aG {group} {self.username}"
                    execute_command(cmd)
                    # print(f"Executing: usermod -aG {group} {self.username}")

            except Exception:
                print(f"Could not get current groups for user {self.username}")

        # Re-apply programs configuration
        if self.programs:
            print(f"[rebuild] User Programs for: {self.username}")
            cmds = self._programs()
            for cmd in cmds:
                print(f"Executing rebuild program command: {cmd}")
                execute_command(cmd)

        # Re-apply file configurations
        if self.file:
            print(f"[rebuild] User Files for: {self.username}")
            if cmds := self.file.build_command():
                for cmd in cmds:
                    print(f"Executing rebuild file command: {cmd}")
                    execute_command(cmd)

        # Re-apply user services
        print(f"[rebuild] User Services for: {self.username}")

        # Check for services that need to be stopped because they are disabled
        if self.services:
            for service_name, serv in self.services.items():
                if not serv.enable:
                    try:
                        # Check if service is currently active
                        result = execute_command(
                            f"systemctl --user is-active {service_name}"
                        )
                        if result.strip() == "active":  # Service is active
                            print(f"Stopping disabled service: {service_name}")
                            stop_cmd = f"systemctl --user stop {service_name}"
                            print(f"Executing rebuild service command: {stop_cmd}")
                            execute_command(stop_cmd)

                        # Check if service is enabled and disable it
                        result = execute_command(
                            f"systemctl --user is-enabled {service_name}"
                        )
                        if result.strip() == "enabled":  # Service is enabled
                            print(f"Disabling service: {service_name}")
                            disable_cmd = f"systemctl --user disable {service_name}"
                            print(f"Executing rebuild service command: {disable_cmd}")
                            execute_command(disable_cmd)

                    except Exception:
                        print(f"Could not check status of service {service_name}")

        cmds = self._services()
        for cmd in cmds:
            print(f"Executing rebuild service command: {cmd}")
            execute_command(cmd)

    def _create(self) -> list[str]:
        """Create the user in the system."""
        user = self.username
        name = self.name or user
        shell = self.shell or "/bin/bash"
        groups: list = self.groups or []
        cmds = []
        base = self._config._base
        # Normal users (no root)
        if user != "root":
            # print(f"Creating user {user}")
            cmd = base.exec_command("add_user", username=user, fullname=name, shell=shell)
            cmds.append(cmd)
            # cmds.append(f"useradd -m {user} -c '{name}'")
            if groups:
                # TODO: Implement group creation
                if self.allow_sudo:
                    groups.append(base.commands["admin_group"]) #"wheel")
                    cmds.append(
                        "sed -i 's/# %wheel ALL=(ALL:ALL) ALL/%wheel ALL=(ALL:ALL) ALL/' /etc/sudoers",
                    )
                    cmds.append(
                        "sed -i 's/# auth       required   pam_wheel.so/auth       required   pam_wheel.so/' /etc/pam.d/su",
                    )

                for group in set(groups):
                    try:
                        cmd = base.exec_command("mod_user", options=f"-aG {group}", username=user)
                        cmds.append(cmd)
                        # cmds.append(f"usermod -aG {group} {user}")
                    except Exception:
                        print(f"Group {group} does not exist")

        # Shell
        # cmds.append(f"usermod -s {shell} {user}")

        # Password
        no_password = self.no_password == True
        if not no_password:
            if isinstance(self.hashed_password, str):
                # print("Assign the provided password")
                cmd = base.exec_command("mod_user", options=f"-p {self.hashed_password}", username=user)
                cmds.append(cmd)
            elif isinstance(self.password, str):
                # print("Assign the provided password after encryption")
                hash_passwd = base.hash_passwd(self.password)
                cmd = base.exec_command("mod_user", options=f"-p {hash_passwd}", username=user)
                cmds.append(cmd)
                # cmds.append(f"usermod -p `mkpasswd -m sha-512 {self.password}` {user}")
            else:
                cmds.append(f"passwd {user}")

        return cmds

    def _shell_rc_path(self) -> str:
        """Determine the user's shell init file path."""
        shell = (self.shell or "/bin/bash").split("/")[-1]
        home = f"/home/{self.username}"
        if shell == "zsh":
            return f"{home}/.zshrc"
        elif shell == "fish":
            return f"{home}/.config/fish/config.fish"
        else:
            return f"{home}/.bashrc"

    def _apply_extra_shell_init(self) -> list[str]:
        """Return commands to idempotently append extra shell initialization."""
        cmds = []
        if not self.extra_shell_init or self.username == "root":
            return cmds

        rc_path = self._shell_rc_path()
        marker_start = "# === pykod: extra_shell_init start ==="
        marker_end = "# === pykod: extra_shell_init end ==="
        payload = self.extra_shell_init.strip()

        cmds.append(f"mkdir -p $(dirname {rc_path})")
        cmds.append(f"touch {rc_path}")

        # Remove existing block if present
        cmds.append(f"sed -i '/^{marker_start}$/,/^{marker_end}$/d' {rc_path}")
        # Append the new block
        processed_payload = "\n".join(line.lstrip() for line in payload.split("\n"))
        cmds.append(
            f"cat >> {rc_path} << 'EOF'\n{marker_start}\n{processed_payload}\n{marker_end}\nEOF"
        )
        return cmds

    def _apply_environment_vars(self) -> list[str]:
        """Return commands to idempotently export environment variables in ~/.profile."""
        cmds = []
        if not self.environment_vars or self.username == "root":
            return cmds

        profile_path = f"/home/{self.username}/.profile"
        cmds.append(f"touch {profile_path}")

        for key, value in self.environment_vars.items():
            marker = f"# pykod: env {key}"
            export_line = f'export {key}="{value}"'
            cmd = (
                f"grep -F '{marker}' {profile_path} >/dev/null || "
                f"printf '\\n{marker}\\n{export_line}\\n' >> {profile_path}"
            )
            cmds.append(cmd)

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
                        cmds.extend(self.dotfile_manager.deploy(prog_name))
        if self.deploy_configs:
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
