"""Service configuration base classes."""

from dataclasses import dataclass, field
from sqlite3.dbapi2 import Date
from typing import Any

from pykod.base import NestedDict
from pykod.common import exec_chroot
from pykod.repositories.base import PackageList


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

    package: PackageList | None = None
    enable: bool = True
    service_name: str | None = None
    extra_packages: PackageList | None = None
    settings: dict[str, Any] = field(default_factory=dict)
    service_type: str = "system"  # or "user"
    config: list[str] = field(default_factory=list)

    def __post_init__(self):
        """Post-initialization processing."""
        if self.package is not None and self.service_name is None and self.enable:
            self.service_name = self.package.to_list()[0]

    def enable_service(self, service) -> str:
        """Enable a list of services in the specified mount point."""
        if self.service_name is not None:
            service = self.service_name
        print(f"Enabling service: {service}")
        cmd = f"systemctl enable {service}"
        return cmd

    def disable_service(self, service) -> str:
        """Disable a list of services in the specified mount point."""
        print(f"Disabling service: {service}")
        cmd = f"systemctl disable {service}"
        return cmd


# class Services(NestedDict):
# @dataclass
class Services(dict):
    """Service manager configuration."""

    def __init__(self, *args, **kwargs):
        """Initialize desktop manager."""
        if len(args) > 0:
            data = args[0]
        else:
            data = kwargs

        super().__init__(data)

    def enable(self, config):
        """Creating a Service manager."""
        print("\n[ENABLE] Services:")
        for key, obj in self.items():
            if obj.enable:
                print(f"\n - {key}: {obj}")
                cmd = obj.enable_service(key)
                print("   ->", cmd)
                exec_chroot(cmd, mount_point=config._mount_point)

    # def disable(self, config):
    #     """Creating a Service manager."""
    #     print("\n[DISABLE] Services:")
    #     for key, obj in self.items():
    #         if not obj.enable:
    #             print(f"\n - {key}: {obj}")
    #             cmd = obj.disable_service(key)
    #             print("   ->", cmd)
    #             exec_chroot(cmd, mount_point=config.mount_point)

    def rebuild(self):
        print("[rebuild] Updating services:")
        for key, extra in self.items():
            print(f" - {key}: {extra}")

    def list_enabled_services(self):
        """Creating a Service manager."""
        return [key for key, obj in self.items() if obj.enable]
