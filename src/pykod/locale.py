"""Locale configuration."""

from dataclasses import dataclass, field


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

        Delegates to the distribution-specific repository implementation.
        """
        print("\n\n[install] Default locale:")
        # Delegate to distribution-specific implementation
        config._base.configure_locale(config._mount_point, self)
