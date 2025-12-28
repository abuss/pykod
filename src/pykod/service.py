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

    package: PackageList
    enable: bool = True
    service_name: str | None = None
    extra_packages: PackageList | None = None
    settings: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Post-initialization processing."""
        if self.service_name is None and self.enable:
            self.service_name = self.package.to_list()[0]

    # if not self.service_name:
    #     self.service_name = sel
    #     self.extra_packages = None

    # def install(self, _config):
    #     status = "Enabled" if self.enable else "Disabled"
    #     print(
    #         "[install] "
    #         f"Service: {status}, Name: {self.service_name}, Package: {self.package}, "
    #         f"Extra Packages: {self.extra_packages}, Settings: {self.settings}"
    #     )

    # def rebuild(self, _config):
    #     status = "Enabled" if self.enable else "Disabled"
    #     print(
    #         "[rebuild] "
    #         f"Service: {status}, Name: {self.service_name}, Package: {self.package}, "
    #         f"Extra Packages: {self.extra_packages}, Settings: {self.settings}"
    # )

    def enable_service(self, service) -> str:
        """Enable a list of services in the specified mount point."""
        if self.service_name is not None:
            service = self.service_name
        print(f"Enabling service: {service}")
        cmd = f"systemctl enable {service}"
        return cmd

    def disable_services(self, service) -> str:
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
                exec_chroot(cmd, mount_point=config.mount_point)

    def rebuild(self):
        print("[rebuild] Updating services:")
        for key, extra in self.items():
            print(f" - {key}: {extra}")

    def list_enabled_services(self):
        """Creating a Service manager."""
        return [key for key, obj in self.items() if obj.enable]

    # def __getattr__(self, name) -> Service:
    #     if name in self._data:
    #         return self[name]
    #     else:
    #         self._data[name] = None
    #         return self._data[name]


# class Services(NestedDict):
#     """Service manager configuration."""

#     def __init__(self, **kwargs):
#         """Initialize desktop manager."""
#         super().__init__(**kwargs)

#     def install(self, _config):
#         """Creating a Service manager."""
#         print("\n[install] Services:")
#         for key, extra in self.services.items():
#             print(f" - {key}: {extra}")

#     def rebuild(self):
#         print("[rebuild] Updating services:")
#         for key, extra in self.services.items():
#             print(f" - {key}: {extra}")
