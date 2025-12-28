"""Service configuration base classes."""

from dataclasses import dataclass, field
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

    enable: bool
    package: PackageList | None
    service_name: str | None = None
    extra_packages: PackageList | None = None
    settings: dict[str, Any] = field(default_factory=dict)

    # def __post_init__(self):
    #     """Post-initialization processing."""
    #     # if self.service_name is None and self.enable:
    #     # self.service_name = self.
    #     if not self.enable:
    #         self.package = None
    #         self.extra_packages = None

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


class Services(NestedDict):
    """Service manager configuration."""

    def __init__(self, *args, **kwargs):
        """Initialize desktop manager."""
        super().__init__(**kwargs)
        if len(args) > 0:
            self._data: dict[str, Service] = args[0]

    def enable(self, _config):
        """Creating a Service manager."""
        print("\n[ENABLE] Services:")
        for key, obj in self._data.items():
            if obj.enable:
                print(f"\n - {key}: {obj}")
                cmd = obj.enable_service(key)
                exec_chroot(cmd, mount_point=_config.mount_point)

    def rebuild(self):
        print("[rebuild] Updating services:")
        for key, extra in self.services.items():
            print(f" - {key}: {extra}")


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
