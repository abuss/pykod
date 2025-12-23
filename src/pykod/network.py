"""Locale configuration."""

from typing import Any

from pykod.base import NestedDict
from pykod.common import open_with_dry_run


class Network(NestedDict):
    """Represents a disk device with partitions."""

    def __init__(self, **kwargs):
        """Initialize Network."""
        super().__init__(**kwargs)

    def install(self, config):
        """Configure and install network related."""
        print("\n\n[install] Hostname:", self.hostname)
        print("Extra setings")
        for key, extra in self.settings.items():
            print(f"  {key}: {extra}")

        # network_conf = conf.network

        # hostname
        mount_point = config.mount_point
        hostname = self.hostname
        with open_with_dry_run(f"{mount_point}/etc/hostname", "w") as f:
            f.write(hostname + "\n")

        use_ipv4 = self.ipv4 if hasattr(self, "ipv4") else True
        use_ipv6 = self.ipv6 if hasattr(self, "ipv6") else True
        eth0_network = """[Match]
Name=*
[Network]
"""
        if use_ipv4:
            eth0_network += "DHCP=ipv4\n"
        if use_ipv6:
            eth0_network += "DHCP=ipv6\n"
        with open_with_dry_run(
            f"{mount_point}/etc/systemd/network/10-eth0.network", "w"
        ) as f:
            f.write(eth0_network)

        # hosts
        with open_with_dry_run(f"{mount_point}/etc/hosts", "w") as f:
            f.write("127.0.0.1 localhost\n::1 localhost\n")

    def rebuild(self):
        print("\n\n[rebuild] Hostname:", self.hostname)
        print("[rebuild] updating network settings:", self.settings)
