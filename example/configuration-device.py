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

from pykod.devices import Devices, Disk, Partition

# from pykod.disk import Partition
# from pykod.repositories import AUR, Arch, Flatpak
from pykod import Configuration, ndict
# from pykod.repositories import Repository


conf = Configuration()
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

# archpkgs = Arch(url="https://mirror.rackspace.com/archlinux")
# aurpkgs = AUR(helper="yay", helper_url="https://aur.archlinux.org/yay-bin.git")
# flatpakpkgs = Flatpak(hub_url="flathub")

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

# conf.demo = ndict(x=5, enable=True)
# conf.demo.foo.bar = 66


if __name__ == "__main__":
    print("-" * 100)
    # Print all attributes from conf
    print("Configuration attributes:")

    print("\n", "-" * 80)
    print(conf.install())
    # print(conf.demo)
