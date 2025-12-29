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

# from pykod._hardware import HardwareManager
from pykod.desktop import DesktopEnvironment, DesktopManager
from pykod.devices import Boot, Devices, Disk, Kernel, Loader, Partition
from pykod.fonts import Fonts
from pykod.locale import Locale
from pykod.network import Network
from pykod.packages import Packages

# from pykod.disk import Partition
from pykod.repositories import AUR, Arch, Flatpak
from pykod.service import Service, Services
from pykod.user import (
    GitConfig,
    OpenSSH,
    Program,
    Stow,
    SyncthingConfig,
    User,
    UserService,
)

# from pykod.repositories import Repository

archpkgs = Arch(mirror_url="https://mirror.rackspace.com/archlinux")
# aurpkgs = AUR(helper="yay", helper_url="https://aur.archlinux.org/yay-bin.git")
aurpkgs = AUR(helper="paru", helper_url="https://aur.archlinux.org/paru.git")
flatpakpkgs = Flatpak(hub_url="flathub")


conf = Configuration(base=archpkgs, dry_run=True, debug=True, verbose=True)
# conf = Configuration(base=archpkgs)
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
import cli
import development

conf.device = Devices(
    disk0=Disk(
        device="/dev/vda",
        partitions=[
            Partition(name="efi", size="512M", type="esp", mountpoint="/boot"),
            Partition(name="root", size="20G", type="btrfs", mountpoint="/"),
            Partition(name="swap", size="2G", type="linux-swap"),
            Partition(name="home", size="100%", type="btrfs"),
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
        package=archpkgs["linux"],
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

conf.network = Network(
    hostname="eszkoz",
    settings={"ipv6": True},
)

# Desktop environment configuration - using DesktopManager directly
conf.desktop = DesktopManager(
    display_manager=Service(package=archpkgs["gdm"]),
    environments={
        # Traditional desktop environments
        "gnome": DesktopEnvironment(
            enable=True,
            # display_manager="gdm",
            package=archpkgs["gnome"],
            exclude_packages=archpkgs["gnome-tour", "yelp"],
            extra_packages=archpkgs[
                "gnome-tweaks",
                "showtime",
                "gnome-connections",
                "gnome-shell-extension-weather-oclock",
                # "flatpak:com.mattjakeman.ExtensionManager",
                "gnome-shell-extension-appindicator",
            ]
            + aurpkgs[
                "gnome-shell-extension-dash-to-dock",
                "gnome-shell-extension-blur-my-shell",
                "gnome-shell-extension-arc-menu-git",
                "gnome-shell-extension-gsconnect",
            ],
        ),
        "plasma": DesktopEnvironment(
            enable=False,
            package=archpkgs["plasma"],
            # display_manager="sddm",
            extra_packages=archpkgs["kde-applications"],
        ),
        "cosmic": DesktopEnvironment(
            enable=True,
            package=archpkgs["cosmic"],
            # display_manager="cosmic-greeter"
        ),
        "budgie": DesktopEnvironment(
            enable=False,
            package=archpkgs["budgie"],
            # display_manager="lightdm",
            extra_packages=archpkgs["lightdm-gtk-greeter", "network-manager-applet"],
        ),
        "cinnamon": DesktopEnvironment(
            enable=False,
            package=archpkgs["cinnamon"],
            # display_manager="gdm"
        ),
        # Wayland compositors
        "hyprland": DesktopEnvironment(
            enable=False,
            package=archpkgs["hyprland"],
            # display_manager="greetd",
            extra_packages=archpkgs[
                "hyprpaper",
                "waybar",
                "wofi",
                "dunst",
                "grim",
                "slurp",
                "wl-clipboard",
            ],
        ),
    },
)

# Fonts configuration
conf.fonts = Fonts(
    font_dir=True,
    packages=archpkgs[
        "nerd-fonts",
        "ttf-firacode-nerd",
        "ttf-nerd-fonts-symbols",
        "ttf-nerd-fonts-symbols-common",
        "ttf-sourcecodepro-nerd",
        "ttf-fira-sans",
        "ttf-fira-code",
        "ttf-liberation",
        "noto-fonts-emoji",
        "adobe-source-serif-fonts",
        "ttf-ubuntu-font-family",
    ]
    + aurpkgs["ttf-work-sans"],
)

conf.root = User(username="root", no_password=True, shell="/bin/bash")

conf.abuss = User(
    username="abuss",
    name="Antal Buss",
    shell="/usr/bin/zsh",
    groups=["audio", "input", "users", "video"],
    allow_sudo=True,
    # TODO: Set password and SSH keys from environment variables or secure config
    hashed_password="$6$MOkGLOzXlj0lIE2d$5sxAysiDyD/7ZfntgZaN3vJ48t.BMi2qwPxqjgVxGXKXrNlFxRvnO8uCvOlHaGW2pVDrjt0JLNR9GWH.2YT5j.",
    # password="secure_password_here",
    ssh_authorized=OpenSSH(
        keys=[
            "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDOA6V+TZJ+BmBAU4FB0nbhYQ9XOFZwCHdwXTuQkb77sPi6fVcbzso5AofUc+3DhfN56ATNOOslvjutSPE8kIp3Uv91/c7DE0RHoidNl3oLre8bau2FT+9AUTZnNEtWH/qXp5+fzvGk417mSL3M5jdoRwude+AzhPNXmbdAzn08TMGAkjGrMQejXItcG1OhXKUjqeLmB0A0l3Ac8DGQ6EcSRtgPCiej8Boabn21K2OBfq64KwW/MMh/FWTHndyBF/lhfEos7tGPvrDN+5G05oGjf0fnMOxsmAUdTDbtOTTeMTvDwjJdzsGUluEDbWBYPNlg5wacbimkv51/Bm4YwsGOkkUTy6eCCS3d5j8PrMbB2oNZfByga01FohhWSX9bv35KAP4nq7no9M6nXj8rQVsF0gPndPK/pgX46tpJG+pE1Ul6sSLR2jnrN6oBKzhdZJ54a2wwFSd207Zvahdx3m9JEVhccmDxWltxjKHz+zChAHsqWC9Zcqozt0mDRJNalW8fRXKcSWPGVy1rfbwltiQzij+ChCQQlUG78zW8lU7Bz6FuyDsEFpZSat7jtbdDBY0a4F0yb4lkNvu+5heg+dhlKCFj9YeRDrnvcz94OKvAZW1Gsjbs83n6wphBipxUWku7y86iYyAAYQGKs4jihhYWrFtfZhSf1m6EUKXoWX87KQ== antal.buss@gmail.com"
        ]
    ),
    dotfile_manager=Stow(
        # source_dir="~/.dotfiles",
        # target_dir="~/",
        repo_url="http://git.homecloud.lan/abuss/dotconfig.git",
    ),
    # programs=Programs(
    programs={
        "git": Program(
            enable=True,
            package=archpkgs["git"],
            config=GitConfig(
                {
                    "user.name": "Antal Buss",
                    "user.email": "antal.buss@gmail.com",
                    "core.editor": "helix",
                }
            ),
        ),
        "starship": Program(
            enable=True, package=archpkgs["starship"], deploy_config=True
        ),
        "ghostty": Program(
            enable=True, package=archpkgs["ghostty"], deploy_config=True
        ),
        #         "fish": c.Program(enable=True),
        "zsh": Program(enable=True, package=archpkgs["zsh"], deploy_config=True),
        #         "neovim": c.Program(enable=True, deploy_config=True),
        #         "helix": c.Program(enable=True, deploy_config=True),
        "emacs": Program(
            enable=True,
            package=archpkgs["emacs-wayland"],
            deploy_config=True,
            extra_packages=archpkgs["aspell", "aspell-en"],
        ),
        #         "dconf": c.Program(
        #             enable=True,
        #             config="gnome_dconf_settings",  # Reference to gnome config
        #         ),
    },
    # ),
    services={
        "syncthing": UserService(
            enable=False,
            package=archpkgs["syncthing"],
            config=SyncthingConfig(
                {
                    "options": {"start-browser": "false"},
                    "gui": {
                        "enabled": "true",
                        "address": "0.0.0.0:8384",
                    },
                }
            ),
        )
    },
    deploy_configs=[
        "home",  # General config for home directory
        "gtk",  # GTK themes
    ],
)

# packages = cli.packages + development.packages
conf.packages = Packages(
    archpkgs[
        "iw",
        "stow",
        "mc",
        "less",
        "neovim",
        "htop",
        "libgtop",
        "power-profiles-daemon",
        "system-config-printer",
        # "git",
        "ghostty",
        # "alacritty",
        # "blueman", # TODO: Maybe a better location is required
        # AUR packages
        # Flatpak packages
        # "flatpak:com.mattjakeman.ExtensionManager",
        # "flatpak:com.visualstudio.code",
        "distrobox",
        "podman",
        "qemu-desktop",
        "spice-gtk",
        "remmina",
        "papers",
        "firefox",
        "thunderbird",
        "freecad",
        "openscad",
        "prusa-slicer",
    ]
    + aurpkgs[
        "visual-studio-code-bin",
        "opera",
        "quickemu",
        "uxplay",
        "megasync-bin",
        "brave-bin",
        "zen-browser-bin",
    ]
    # CLI tools
    + cli.packages(archpkgs, aurpkgs)
    # Development tools
    + development.packages(archpkgs)
    # Flatpak packages
    + flatpakpkgs[
        "freecad",
        "openscad",
        "prusa-slicer",
    ]
)

# System services configuration
conf.services = Services(
    {
        "sane": Service(
            enable=True,
            package=archpkgs["sane"],
            extra_packages=archpkgs["sane-airscan"],
        ),
        "pipewire": Service(
            enable=True,
            package=archpkgs["pipewire"],
            extra_packages=archpkgs["pipewire-alsa", "pipewire-pulse"],
        ),
        "fwupd": Service(enable=True, package=archpkgs["fwupd"]),
        "tailscale": Service(enable=True, package=archpkgs["tailscale"]),
        "networkmanager": Service(
            enable=True,
            package=archpkgs["networkmanager"],
            service_name="NetworkManager",
        ),
        # "nix": Service(enable=True, service_name="nix_daemon"),
        "openssh": Service(
            enable=True,
            package=archpkgs["openssh-server"],
            service_name="sshd",
            settings={"PermitRootLogin": False},
        ),
        "avahi": Service(enable=False, package=archpkgs["avahi-daemon"]),
        "cups": Service(
            enable=True,
            package=archpkgs["cups"],
            extra_packages=archpkgs["gutenprint"] + aurpkgs["brother-dcp-l2550dw"],
        ),
        "bluetooth": Service(
            enable=True, package=archpkgs["bluez"], service_name="bluetooth"
        ),
    }
)
conf.services["avahi"].enable = False

# System mount configuration (disabled by default)
# conf.mount = MountManager(
#     mounts={
#         "data": c.SystemdMount(
#             type="cifs",
#             what="//mmserver.lan/NAS1",
#             where="/mnt/data",
#             description="MMserverNAS1",
#             options="vers=2.1,credentials=/etc/samba/mmserver-cred,iocharset=utf8,rw,x-systemd.automount,uid=1000",
#             after="network.target",
#             wanted_by="multi-user.target",
#             automount=True,
#             automount_config="TimeoutIdleSec=0",
#         ),
#         "library": c.SystemdMount(
#             type="nfs",
#             what="homenas2.lan:/data/Documents",
#             where="/mnt/library/",
#             description="Document library",
#             options="noatime,x-systemd.automount,noauto",
#             after="network.target",
#             wanted_by="multi-user.target",
#             automount=True,
#             automount_config="TimeoutIdleSec=600",
#         ),
#     }
# )


if __name__ == "__main__":
    print("-" * 100)
    # Print all attributes from conf
    print("Configuration attributes:")

    print("\n", "-" * 80)
    conf.install()
    # print("Conf.packages:", conf.packages)
    # print("\n", "-" * 80)
    # print("-" * 100)
    # conf._list_packages()
