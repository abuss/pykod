# Structure
#
# - repository (package sources)
# - system
#   - devices (disk)
#   - boot
#       - kernel
#       - loader
#   - locale
#   - network
#   - hardware
#       - sound
#       - scanner
# - desktop
#   - windows manager (gnome, kde, cosmic, ...)
#   - desktop manager (gdm, lightdm, etc)
# - users
# - environment
#   - services
#   - fonts
#   - programs
#

from pykod import Configuration
from pykod.devices import Boot, Devices, Disk, Kernel, Loader, Partition
from pykod.locale import Locale

# from pykod.disk import Partition
from pykod.repositories import AUR, Arch, Flatpak

# from pykod.repositories import Repository


conf = Configuration(dry_run=True, debug=True, verbose=True)
# use_virtualization = False

# git_config = ndict
# syncthing_config = ndict
# stow_config = ndict
# themes_config = ndict
# mount_config = ndict

# use_gnome = True
# use_plasma = False
# use_cosmic = True

# with conf as c:
# import cli
# import development

# import pykod.disk as disk
# import pykod.openssh as openssh
# from pykod import config

conf.archpkgs = Arch(url="https://mirror.rackspace.com/archlinux")
conf.aurpkgs = AUR(helper="yay", helper_url="https://aur.archlinux.org/yay-bin.git")
conf.flatpakpkgs = Flatpak(hub_url="flathub")

conf.device = Devices(
    disk0=Disk(
        device="/dev/vda",
        partitions=[
            Partition(name="efi", size="512M", type="esp", mountpoint="/boot"),
            Partition(name="root", size="20G", type="btrfs", mountpoint="/"),
            Partition(name="swap", size="2G", type="linux-swap"),
            Partition(name="home", size="remaining", type="btrfs"),
        ],
    ),
    disk1=Disk(
        device="/dev/vdb",
        partitions=[
            Partition(
                name="scratch", size="remaining", type="btrfs", mountpoint="/scratch"
            ),
        ],
    ),
)

conf.boot = Boot(
    kernel=Kernel(
        package="linux",
        modules=[
            "xhci_pci",
            "ohci_pci",
            "ehci_pci",
            "virtio_pci",
            "ahci",
            "usbhid",
            "sr_mod",
            "virtio_blk",
        ],
    ),
    loader=Loader(
        type="systemd-boot",
        timeout=10,
        include=["memtest86+"],
    ),
)

conf.locale = Locale(
    default="en_CA.UTF-8 UTF-8",
    additional_locales=[
        "en_US.UTF-8 UTF-8",
        "en_GB.UTF-8 UTF-8",
    ],
    extra_settings={
        "LC_ADDRESS": "en_CA.UTF-8",
        "LC_IDENTIFICATION": "en_CA.UTF-8",
        "LC_MEASUREMENT": "en_CA.UTF-8",
        "LC_MONETARY": "en_CA.UTF-8",
        "LC_NAME": "en_CA.UTF-8",
        "LC_NUMERIC": "en_CA.UTF-8",
        "LC_PAPER": "en_CA.UTF-8",
        "LC_TELEPHONE": "en_CA.UTF-8",
        "LC_TIME": "en_CA.UTF-8",
    },
    keymap="us",
    timezone="America/Edmonton",
)

if __name__ == "__main__":
    print("-" * 100)
    # Print all attributes from conf
    print("Configuration attributes:")

    print("\n", "-" * 80)
    print(conf.install())
    print("Conf.packages:", conf.packages)
