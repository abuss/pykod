"""Service configuration base classes."""

from dataclasses import dataclass, field
from typing import Any, Optional

from pykod.base import NestedDict


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

    def install(self, _config):
        status = "Enabled" if self.enable else "Disabled"
        print(
            "[install] "
            f"Service: {status}, Name: {self.service_name}, Package: {self.package}, "
            f"Extra Packages: {self.extra_packages}, Settings: {self.settings}"
        )

    def rebuild(self, _config):
        status = "Enabled" if self.enable else "Disabled"
        print(
            "[rebuild] "
            f"Service: {status}, Name: {self.service_name}, Package: {self.package}, "
            f"Extra Packages: {self.extra_packages}, Settings: {self.settings}"
        )


class ServiceManager(NestedDict):
    """Service manager configuration."""

    def __init__(self, **kwargs):
        """Initialize desktop manager."""
        super().__init__(**kwargs)

    def install(self, _config):
        """Creating a Service manager."""
        print("\n[install] Services:")
        for key, extra in self.services.items():
            print(f" - {key}: {extra}")

    def rebuild(self):
        print("[rebuild] Updating services:")
        for key, extra in self.services.items():
            print(f" - {key}: {extra}")
