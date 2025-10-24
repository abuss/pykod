from typing import NamedTuple, Optional, Any
from dataclasses import dataclass, field

# Import standalone OpenSSH and dotfile strategy classes
from pykod.openssh import OpenSSH
from pykod.dotfiles import DotfileStrategy


@dataclass
class Repository:
    """Base class for package repositories."""

    pass


@dataclass
class ArchRepo(Repository):
    """Arch Linux official repository configuration.

    Args:
        url: Mirror URL for the Arch repository
        repos: List of repository names to enable (defaults to core, extra)
    """

    url: str
    repos: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.url.startswith(("http://", "https://")):
            raise ValueError(f"Invalid URL format: {self.url}")
        self.repos = ["core", "extra"]

    def install(self):
        print(f"arch: {self.repos} {self.url}")


@dataclass
class AURRepo(Repository):
    """Arch User Repository (AUR) configuration.

    Args:
        helper: AUR helper tool name (e.g., 'yay', 'paru')
        helper_urls: URL or list of URLs for the AUR helper
    """

    helper: str
    helper_urls: str | list[str]

    def install(self):
        print(f"AUR: {self.helper} {self.helper_urls}")


@dataclass
class FlatpakRepo(Repository):
    """Flatpak repository configuration.

    Args:
        urls: Repository URL or list of URLs (e.g., Flathub)
    """

    urls: str

    def install(self):
        print(f"Flatpak: {self.urls}")


class Locale(NamedTuple):
    """System locale and timezone configuration.

    Args:
        default: Default locale (e.g., 'en_US.UTF-8 UTF-8')
        additional_locales: List of additional locales to generate
        extra_settings: Dictionary of additional locale environment variables
        keymap: Keyboard layout (e.g., 'us', 'de')
        timezone: System timezone (e.g., 'America/New_York')
    """

    default: str
    additional_locales: list[str] | None = None
    extra_settings: dict | None = None
    keymap: str | None = None
    timezone: str | None = None

    def install(self):
        print(
            f"Locale: {self.default}, Additional: {self.additional_locales}, "
            f"Settings: {self.extra_settings}, Keymap: {self.keymap}, Timezone: {self.timezone}"
        )


class Kernel(NamedTuple):
    """Kernel configuration.

    Args:
        package: Kernel package name (e.g., 'linux', 'linux-lts')
        modules: List of kernel modules to load
    """

    package: Optional[str] = None
    modules: list[str] = []

    def install(self):
        print(f"Kernel: {self.package}, Modules: {self.modules}")


class Loader(NamedTuple):
    """Boot loader configuration.

    Args:
        type: Boot loader type (e.g., 'systemd-boot', 'grub')
        timeout: Boot menu timeout in seconds
        include: Additional boot entries to include
    """

    type: Optional[Any] = None
    timeout: Optional[Any] = None
    include: list[Any] = []

    def install(self):
        print(f"Loader: {self.type}, Timeout: {self.timeout}, Include: {self.include}")


class Boot(NamedTuple):
    """System boot configuration.

    Args:
        kernel: Kernel configuration
        loader: Boot loader configuration
    """

    kernel: Optional[Kernel] = None
    loader: Optional[Loader] = None

    def install(self):
        print(f"Boot: Kernel: {self.kernel}, Loader: {self.loader}")


@dataclass
class Network:
    """Network configuration.

    Args:
        hostname: System hostname
        settings: Network configuration settings (e.g., IPv6 enabled)
    """

    hostname: str
    settings: dict[str, Any]

    def __post_init__(self):
        if not self.hostname or len(self.hostname.strip()) == 0:
            raise ValueError("Hostname cannot be empty")
        if not self.hostname.replace("-", "").replace("_", "").isalnum():
            raise ValueError(f"Invalid hostname format: {self.hostname}")

    def install(self):
        print(f"Network: Hostname: {self.hostname}, Settings: {self.settings}")


class Device(NamedTuple):
    """Hardware device configuration.

    Args:
        devices: Dictionary mapping device names to configurations
    """

    devices: dict

    def install(self):
        print(f"Device: {self.devices}")


@dataclass
class Packages:
    """Package management configuration.

    Args:
        packages: List of packages to install (supports aur: and flatpak: prefixes)
    """

    packages: list[str] = field(default_factory=list)

    def install(self):
        print(f"Packages: {self.packages}")


@dataclass
class Service:
    """Generic service configuration.

    Args:
        enable: Whether to enable the service
        service_name: Systemd service name
        package: Package providing the service
        extra_packages: Additional packages required by the service
        settings: Service-specific configuration settings
    """

    enable: bool = False
    service_name: Optional[str] = None
    package: Optional[str] = None
    extra_packages: list[str] = field(default_factory=list)
    settings: dict[str, Any] = field(default_factory=dict)

    def install(self):
        status = "Enabled" if self.enable else "Disabled"
        print(
            f"Service: {status}, Name: {self.service_name}, Package: {self.package}, "
            f"Extra Packages: {self.extra_packages}, Settings: {self.settings}"
        )


# @dataclass
# class Hardware:
#     """Hardware-related services configuration.
#
#     Args:
#         sane: Scanner and camera service (SANE)
#         pipewire: Modern audio system
#         pulseaudio: Traditional audio system
#     """
#
#     sane: Optional[Service] = None
#     pipewire: Optional[Service] = None
#     pulseaudio: Optional[Service] = None
#


@dataclass
class HardwareManager:
    """Dynamic hardware services configuration manager.

    This class provides a flexible way to configure hardware-related services
    using a dynamic services dictionary, replacing the fixed Hardware class.

    Args:
        services: Dictionary mapping service names to Service configurations

    Example Usage:
        # Audio services
        HardwareManager(services={
            'pipewire': Service(enable=True, extra_packages=['pipewire', 'pipewire-alsa']),
            'pulseaudio': Service(enable=False),
            'jack': Service(enable=False, package='jack2')
        })

        # Scanner and camera services
        HardwareManager(services={
            'sane': Service(enable=True, extra_packages=['sane', 'sane-airscan']),
            'v4l2loopback': Service(enable=True, package='v4l2loopback-dkms')
        })

        # Graphics and hardware acceleration
        HardwareManager(services={
            'nvidia': Service(enable=True, package='nvidia', extra_packages=['nvidia-utils']),
            'vulkan': Service(enable=True, extra_packages=['vulkan-icd-loader', 'mesa-vulkan-drivers'])
        })
    """

    services: dict[str, Service] = field(default_factory=dict)

    def add_service(self, name: str, service: Service) -> None:
        """Add a new hardware service.

        Args:
            name: Name of the service (e.g., 'pipewire', 'nvidia')
            service: Service configuration
        """
        self.services[name] = service

    def remove_service(self, name: str) -> None:
        """Remove a hardware service.

        Args:
            name: Name of the service to remove
        """
        self.services.pop(name, None)

    def get_enabled_services(self) -> dict[str, Service]:
        """Get all enabled hardware services.

        Returns:
            Dictionary of enabled services
        """
        return {name: svc for name, svc in self.services.items() if svc.enable}

    def enable_service(self, name: str) -> None:
        """Enable a specific hardware service.

        Args:
            name: Name of the service to enable
        """
        if name in self.services:
            self.services[name].enable = True

    def disable_service(self, name: str) -> None:
        """Disable a specific hardware service.

        Args:
            name: Name of the service to disable
        """
        if name in self.services:
            self.services[name].enable = False

    def install(self):
        for name, svc in self.services.items():
            print(name, svc.install())


@dataclass
class DesktopEnvironment:
    """Desktop environment configuration.

    Args:
        enable: Whether to enable this desktop environment
        display_manager: Display manager to use (e.g., 'gdm', 'sddm')
        extra_packages: Additional packages to install
        exclude_packages: Packages to exclude from default installation
    """

    enable: bool = False
    display_manager: str = "gdm"
    extra_packages: list[str] = field(default_factory=list)
    exclude_packages: list[str] = field(default_factory=list)


class DesktopManager:
    """Desktop environment manager configuration.

    This class provides a flexible way to configure multiple desktop environments
    and window managers using a dynamic environments dictionary.

    Args:
        environments: Dictionary of environment name to DesktopEnvironment configuration
        default_display_manager: Default display manager to use if not specified per environment

    Example Usage:
        # Traditional desktop environments
        DesktopManager(environments={
            'gnome': DesktopEnvironment(enable=True, display_manager="gdm"),
            'plasma': DesktopEnvironment(enable=False, display_manager="sddm"),
            'cosmic': DesktopEnvironment(enable=True, display_manager="cosmic-greeter")
        })

        # Modern window managers and compositors
        DesktopManager(environments={
            'hyprland': DesktopEnvironment(enable=True, display_manager="greetd"),
            'sway': DesktopEnvironment(enable=False, display_manager="greetd"),
            'i3': DesktopEnvironment(enable=False, display_manager="lightdm")
        })
    """

    def __init__(
        self,
        environments: Optional[dict[str, DesktopEnvironment]] = None,
        default_display_manager: Optional[str] = None,
    ):
        """Initialize DesktopManager with environments dictionary."""

        self.environments = environments or {}
        self.default_display_manager = default_display_manager

    def add_environment(self, name: str, environment: DesktopEnvironment) -> None:
        """Add a new desktop environment or window manager.

        Args:
            name: Name of the environment (e.g., 'hyprland', 'sway', 'i3')
            environment: DesktopEnvironment configuration
        """
        self.environments[name] = environment

    def remove_environment(self, name: str) -> None:
        """Remove a desktop environment or window manager.

        Args:
            name: Name of the environment to remove
        """
        self.environments.pop(name, None)

    def get_enabled_environments(self) -> dict[str, DesktopEnvironment]:
        """Get all enabled desktop environments.

        Returns:
            Dictionary of enabled environments
        """
        return {name: env for name, env in self.environments.items() if env.enable}


@dataclass
class Fonts:
    """Font configuration.

    Args:
        font_dir: Whether to enable system font directory
        packages: List of font packages to install
    """

    font_dir: bool = True
    packages: list[str] = field(default_factory=list)


@dataclass
class SystemdMount:
    """Systemd mount unit configuration.

    Args:
        type: Mount type (e.g., 'nfs', 'cifs')
        what: What to mount (device/path)
        where: Mount point directory
        description: Human-readable description
        options: Mount options
        after: Systemd unit dependency
        wanted_by: Systemd target that wants this mount
        automount: Whether to enable automounting
        automount_config: Additional automount configuration
    """

    type: str
    what: str
    where: str
    description: str
    options: str
    after: str = "network.target"
    wanted_by: str = "multi-user.target"
    automount: bool = False
    automount_config: Optional[str] = None

    def __post_init__(self):
        if not self.what.strip():
            raise ValueError("Mount source 'what' cannot be empty")
        if not self.where.startswith("/"):
            raise ValueError(f"Mount point must be absolute path: {self.where}")
        if not self.type.strip():
            raise ValueError("Mount type cannot be empty")


@dataclass
class ServiceManager:
    """Dynamic system service configuration manager.

    Args:
        services: Dictionary mapping service names to Service configurations
        mounts: Systemd mount configurations
    """

    services: dict[str, Service] = field(default_factory=dict)
    mounts: dict[str, SystemdMount] = field(default_factory=dict)

    def add_service(self, name: str, service: Service) -> None:
        """Add a new system service.

        Args:
            name: Name of the service (e.g., 'tailscale', 'openssh')
            service: Service configuration
        """
        self.services[name] = service

    def remove_service(self, name: str) -> None:
        """Remove a system service.

        Args:
            name: Name of the service to remove
        """
        self.services.pop(name, None)

    def get_enabled_services(self) -> dict[str, Service]:
        """Get all enabled system services.

        Returns:
            Dictionary of enabled services
        """
        return {name: svc for name, svc in self.services.items() if svc.enable}

    def enable_service(self, name: str) -> None:
        """Enable a specific system service.

        Args:
            name: Name of the service to enable
        """
        if name in self.services:
            self.services[name].enable = True

    def disable_service(self, name: str) -> None:
        """Disable a specific system service.

        Args:
            name: Name of the service to disable
        """
        if name in self.services:
            self.services[name].enable = False

    def add_mount(self, name: str, mount: SystemdMount) -> None:
        """Add a new systemd mount.

        Args:
            name: Name of the mount (e.g., 'data', 'library')
            mount: SystemdMount configuration
        """
        self.mounts[name] = mount

    def remove_mount(self, name: str) -> None:
        """Remove a systemd mount.

        Args:
            name: Name of the mount to remove
        """
        self.mounts.pop(name, None)


@dataclass
class MountManager:
    """Dynamic systemd mount configuration manager.

    Args:
        mounts: Dictionary mapping mount names to SystemdMount configurations
    """

    mounts: dict[str, SystemdMount] = field(default_factory=dict)

    def add_mount(self, name: str, mount: SystemdMount) -> None:
        """Add a new systemd mount.

        Args:
            name: Name of the mount (e.g., 'data', 'library')
            mount: SystemdMount configuration
        """
        self.mounts[name] = mount

    def remove_mount(self, name: str) -> None:
        """Remove a systemd mount.

        Args:
            name: Name of the mount to remove
        """
        self.mounts.pop(name, None)

    def get_automounts(self) -> dict[str, SystemdMount]:
        """Get all mounts with automount enabled.

        Returns:
            Dictionary of automount-enabled mounts
        """
        return {name: mount for name, mount in self.mounts.items() if mount.automount}

    def get_mounts_by_type(self, mount_type: str) -> dict[str, SystemdMount]:
        """Get all mounts of a specific type.

        Args:
            mount_type: Type of mount (e.g., 'nfs', 'cifs')

        Returns:
            Dictionary of mounts matching the specified type
        """
        return {
            name: mount
            for name, mount in self.mounts.items()
            if mount.type == mount_type
        }

    def enable_automount(self, name: str) -> None:
        """Enable automount for a specific mount.

        Args:
            name: Name of the mount
        """
        if name in self.mounts:
            self.mounts[name].automount = True

    def disable_automount(self, name: str) -> None:
        """Disable automount for a specific mount.

        Args:
            name: Name of the mount
        """
        if name in self.mounts:
            self.mounts[name].automount = False


@dataclass
class Program:
    """User program configuration.

    Args:
        enable: Whether to enable this program
        package: Package name providing the program
        deploy_config: Whether to deploy configuration files
        extra_packages: Additional packages required
        config: Program-specific configuration
    """

    enable: bool = False
    package: Optional[str] = None
    deploy_config: bool = False
    extra_packages: list[str] = field(default_factory=list)
    config: Optional[dict] = None


@dataclass
class ProgramManager:
    """Dynamic program configuration manager.

    Args:
        programs: Dictionary mapping program names to Program configurations
    """

    programs: dict[str, Program] = field(default_factory=dict)

    def add_program(self, name: str, program: Program) -> None:
        """Add a new program configuration.

        Args:
            name: Name of the program (e.g., 'git', 'neovim')
            program: Program configuration
        """
        self.programs[name] = program

    def remove_program(self, name: str) -> None:
        """Remove a program configuration.

        Args:
            name: Name of the program to remove
        """
        self.programs.pop(name, None)

    def get_enabled_programs(self) -> dict[str, Program]:
        """Get all enabled programs.

        Returns:
            Dictionary of enabled programs
        """
        return {name: prog for name, prog in self.programs.items() if prog.enable}

    def enable_program(self, name: str) -> None:
        """Enable a specific program.

        Args:
            name: Name of the program to enable
        """
        if name in self.programs:
            self.programs[name].enable = True

    def disable_program(self, name: str) -> None:
        """Disable a specific program.

        Args:
            name: Name of the program to disable
        """
        if name in self.programs:
            self.programs[name].enable = False

    def get_programs_with_config(self) -> dict[str, Program]:
        """Get all programs that have configuration files to deploy.

        Returns:
            Dictionary of programs with deploy_config=True
        """
        return {
            name: prog
            for name, prog in self.programs.items()
            if prog.enable and prog.deploy_config
        }


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
    groups: list[str] | None = None
    name: str | None = None
    shell: str | None = None
    home: str | None = None
    allow_sudo: bool = False
    ssh_keys: list[str] | None = None
    hashed_password: str | None = None
    no_password: bool = False
    ssh_authorized: Optional[OpenSSH] = None
    dotfile_manager: Optional[DotfileStrategy] = None
    programs: Optional[ProgramManager] = None
    deploy_configs: list[str] = field(default_factory=list)
    services: dict[str, UserService] = field(default_factory=dict)
    home_config: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.username or len(self.username.strip()) == 0:
            raise ValueError("Username cannot be empty")
        if not self.username.isalnum() and not all(
            c.isalnum() or c in "_-" for c in self.username
        ):
            raise ValueError(f"Invalid username format: {self.username}")
        if self.password and self.hashed_password:
            raise ValueError("Cannot specify both password and hashed_password")
        if self.shell and not self.shell.startswith("/"):
            raise ValueError(f"Shell path must be absolute: {self.shell}")
        if self.allow_sudo:
            self.groups = (self.groups or []) + ["wheel"]

        # Set default home directory unless already specified or user is root
        if self.home is None and self.username != "root":
            object.__setattr__(self, "home", f"/home/{self.username}")


# def package(packages: str | list[str]) -> None:
#     """Placeholder function for packaging tools."""
#     if isinstance(packages, str):
#         packages = [packages]
#     packages_to_install.extend(packages)
#     # for pkg in packages:
#     #     print(f"Packaging tool: {pkg}")
