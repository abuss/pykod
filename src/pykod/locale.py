"""Locale configuration."""

import logging
from dataclasses import dataclass, field

from pykod.common import execute_chroot as exec_chroot
from pykod.common import open_with_dry_run

logger = logging.getLogger("pykod.config")


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
        """Creates locales files.

        Handles differences between Arch and Debian/Ubuntu:
        - Arch: /etc/locale.conf, locale-gen from glibc
        - Debian/Ubuntu: /etc/default/locale, locale-gen from locales package
        """
        from pykod.repositories.debian import Debian

        print("\n\n[install] Default locale:")
        logger.info(f"Configuring locale: {self.default}")
        logger.info(f"Timezone: {self.timezone}")

        mount_point = config._mount_point
        is_debian = isinstance(config._base, Debian)

        # Set timezone
        logger.info(f"Setting timezone to {self.timezone}...")
        try:
            exec_chroot(f"ln -sf /usr/share/zoneinfo/{self.timezone} /etc/localtime")
            logger.info("✓ Timezone symlink created")
        except Exception as e:
            logger.warning(f"Failed to set timezone: {e}")

        # Set hardware clock (may fail in chroot, which is OK)
        try:
            exec_chroot("hwclock --systohc 2>/dev/null || true")
            logger.debug("Hardware clock set (or skipped in chroot)")
        except Exception as e:
            logger.debug(f"hwclock failed (expected in chroot): {e}")

        # Generate locale.gen file
        locale_to_generate = self.default + "\n"
        locale_to_generate += "\n".join(list(self.additional_locales))

        logger.info("Creating /etc/locale.gen...")
        with open_with_dry_run(f"{mount_point}/etc/locale.gen", "w") as locale_file:
            locale_file.write(locale_to_generate + "\n")
        logger.info(f"✓ Locale.gen created with: {self.default}")

        # Generate locales
        logger.info("Generating locales...")
        try:
            exec_chroot("locale-gen", mount_point=mount_point)
            logger.info("✓ Locales generated successfully")
        except Exception as e:
            logger.error(f"locale-gen failed: {e}")
            if is_debian:
                logger.error(
                    "Make sure 'locales' package is installed in base packages"
                )
            raise RuntimeError(f"Failed to generate locales: {e}") from e

        # Set default locale in appropriate config file
        locale_name = self.default.split()[0]

        if is_debian:
            # Debian/Ubuntu: /etc/default/locale
            logger.info("Creating /etc/default/locale (Debian/Ubuntu)...")
            locale_content = f"LANG={locale_name}\n"
            for k, v in self.extra_settings.items():
                locale_content += f"{k}={v}\n"

            with open_with_dry_run(
                f"{mount_point}/etc/default/locale", "w"
            ) as locale_file:
                locale_file.write(locale_content)
            logger.info(f"✓ Default locale set to {locale_name}")
        else:
            # Arch: /etc/locale.conf
            logger.info("Creating /etc/locale.conf (Arch)...")
            locale_extra = locale_name + "\n"
            for k, v in self.extra_settings.items():
                locale_extra += f"{k}={v}\n"

            with open_with_dry_run(
                f"{mount_point}/etc/locale.conf", "w"
            ) as locale_file:
                locale_file.write(f"LANG={locale_extra}\n")
            logger.info(f"✓ Default locale set to {locale_name}")
