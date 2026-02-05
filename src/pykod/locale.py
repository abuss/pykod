"""Locale configuration."""

from dataclasses import dataclass, field

from pykod.common import execute_chroot as exec_chroot
from pykod.common import open_with_dry_run


@dataclass
class Locale:
    """Represents a disk device with partitions."""

    default: str
    keymap: str
    additional_locales: list[str] = field(default_factory=list)
    extra_settings: dict[str, str] = field(default_factory=dict)
    timezone: str = "GMT"

    # def __init__(self, **kwargs):
    #     """Initialize Disk with device and partitions."""
    #     super().__init__(**kwargs)

    def install(self, config):
        """Creates locales files."""
        print("\n\n[install] Default locale:")

        exec_chroot(f"ln -sf /usr/share/zoneinfo/{self.timezone} /etc/localtime")
        exec_chroot("hwclock --systohc")

        locale_to_generate = self.default + "\n"
        locale_to_generate += "\n".join(list(self.additional_locales))

        mount_point = config._mount_point

        with open_with_dry_run(f"{mount_point}/etc/locale.gen", "w") as locale_file:
            locale_file.write(locale_to_generate + "\n")
        exec_chroot("locale-gen")

        locale_name = self.default.split()[0]
        locale_extra = locale_name + "\n"
        for k, v in self.extra_settings.items():
            locale_extra += f"{k}={v}\n"

        with open_with_dry_run(f"{mount_point}/etc/locale.conf", "w") as locale_file:
            locale_file.write(f"LANG={locale_extra}\n")
