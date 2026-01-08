"""Locale configuration."""

from pykod.common import exec_chroot, open_with_dry_run
from pykod.core import NestedDict


class Locale(NestedDict):
    """Represents a disk device with partitions."""

    def __init__(self, **kwargs):
        """Initialize Disk with device and partitions."""
        super().__init__(**kwargs)

    def install(self, config):
        """Creates locales files."""
        print("\n\n[install] Default locale:")
        # print(f"Additiona locales: {self.additional_locales}")
        # print("Extra setings")
        # for key, extra in self.extra_settings.items():
        #     print(f"  {key}: {extra}")

        # print(f"{self.__dict__=}")
        if not hasattr(self, "timezone"):
            time_zone = "GMT"
        else:
            time_zone = self.timezone
        exec_chroot(f"ln -sf /usr/share/zoneinfo/{time_zone} /etc/localtime")
        exec_chroot("hwclock --systohc")

        # locale_spec = self.locale
        # locale_default = self.default
        locale_to_generate = self.default + "\n"
        # if "extra_generate" in locale_spec and locale_spec.extra_generate:
        locale_to_generate += "\n".join(list(self.additional_locales))

        mount_point = config._mount_point

        with open_with_dry_run(f"{mount_point}/etc/locale.gen", "w") as locale_file:
            locale_file.write(locale_to_generate + "\n")
        exec_chroot("locale-gen")

        locale_name = self.default.split()[0]
        locale_extra = locale_name + "\n"
        if hasattr(self, "extra_settings"):
            for k, v in self.extra_settings.items():
                locale_extra += f"{k}={v}\n"
        with open_with_dry_run(f"{mount_point}/etc/locale.conf", "w") as locale_file:
            locale_file.write(f"LANG={locale_extra}\n")
