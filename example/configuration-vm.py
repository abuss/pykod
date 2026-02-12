# VM Configuration

from pykod import *
from pykod.core import File, Source
from pykod.repositories import AUR, Arch, Flatpak
from pykod.repositories.arch import GPU_PACKAGES
from pykod.user import (
    GitConfig,
    OpenSSH,
    Program,
    Stow,
    SyncthingConfig,
)

arch = Arch(mirror_url="https://mirror.cpsc.ucalgary.ca/mirror/archlinux.org/")
aur = AUR(helper="yay", helper_url="https://aur.archlinux.org/yay-bin.git")
# aur = AUR(helper="paru", helper_url="https://aur.archlinux.org/paru-bin.git", skip_debug=True)
flatpak = Flatpak(hub_url="flathub")

# conf = Configuration(base=arch, dry_run=True, debug=True, verbose=True)
conf = Configuration(base=arch, verbose=True)

import cli
import development

conf.devices = Devices(
    disk0=Disk(
        device="/dev/sda",
        partitions=[
            Partition(name="efi", size="512M", type="esp", mountpoint="/boot"),
            # Partition(name="swap", size="2G", type="linux-swap"),
            Partition(name="root", size="100%", type="btrfs", mountpoint="/"),
            # Partition(name="home", size="100%", type="btrfs"),
        ],
    ),
    # disk1=Disk(
    #     device="/dev/vdb",
    #     partitions=[
    #         Partition(
    #             name="scratch", size="remaining", type="btrfs", mountpoint="/scratch"
    #         ),
    #     ],
    # ),
)

conf.boot = Boot(
    kernel=Kernel(
        package=arch["linux"],
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

conf.hardware = Hardware(
    # cpu_microcode=arch["intel-ucode"],
    # graphics=arch["xf86-video-intel"],
    # gpu="auto",  # Automatically detect GPU vendor
    # gpu=arch["xf86-video-amdgpu", "mesa", "vulkan-radeon"],
    gpu=arch[GPU_PACKAGES["amd"]["base"]],
    audio=arch["pipewire", "pipewire-alsa", "pipewire-pulse"],
    sane=arch["sane", "sane-airscan"],
)

# Desktop environment configuration - using DesktopManager directly
conf.desktop = DesktopManager(
    # display_manager=Service(package=arch["gdm"]),
    display_manager=Service(package=arch["cosmic-greeter"]),
    environments={
        # Traditional desktop environments
        "gnome": DesktopEnvironment(
            enable=False,
            # display_manager="gdm",
            package=arch["gnome"],
            exclude_packages=arch["gnome-tour", "yelp"],
            extra_packages=arch[
                "gnome-tweaks",
                "showtime",
                "gnome-connections",
                "gnome-shell-extension-weather-oclock",
                "gnome-shell-extension-appindicator",
            ]
            + aur[
                "gnome-shell-extension-dash-to-dock",
                "gnome-shell-extension-blur-my-shell",
                "gnome-shell-extension-arc-menu-git",
                "gnome-shell-extension-gsconnect",
            ]
            + flatpak["com.mattjakeman.ExtensionManager"],
        ),
        "plasma": DesktopEnvironment(
            enable=False,
            package=arch["plasma"],
            # display_manager="sddm",
            extra_packages=arch["kde-applications"],
        ),
        "cosmic": DesktopEnvironment(
            enable=True,
            package=arch["cosmic"],
            # display_manager="cosmic-greeter",
            exclude_packages=arch["cosmic-initial-setup"],
        ),
        "budgie": DesktopEnvironment(
            enable=False,
            package=arch["budgie"],
            # display_manager="lightdm",
            extra_packages=arch["lightdm-gtk-greeter", "network-manager-applet"],
        ),
        "cinnamon": DesktopEnvironment(
            enable=False,
            package=arch["cinnamon"],
            # display_manager="gdm"
        ),
        # Wayland compositors
        "hyprland": DesktopEnvironment(
            enable=False,
            package=arch["hyprland"],
            # display_manager="greetd",
            extra_packages=arch[
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
    packages=arch[
        # "nerd-fonts",
        "ttf-firacode-nerd",
        "ttf-nerd-fonts-symbols",
        "ttf-nerd-fonts-symbols-common",
        "ttf-sourcecodepro-nerd",
        "ttf-fira-sans",
        "ttf-fira-code",
        # "ttf-liberation",
        # "noto-fonts-emoji",
        # "adobe-source-serif-fonts",
        # "ttf-ubuntu-font-family",
    ]
    + aur["ttf-work-sans"],
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
    # password="changeme",
    ssh_authorized=OpenSSH(
        keys=[
            "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDOA6V+TZJ+BmBAU4FB0nbhYQ9XOFZwCHdwXTuQkb77sPi6fVcbzso5AofUc+3DhfN56ATNOOslvjutSPE8kIp3Uv91/c7DE0RHoidNl3oLre8bau2FT+9AUTZnNEtWH/qXp5+fzvGk417mSL3M5jdoRwude+AzhPNXmbdAzn08TMGAkjGrMQejXItcG1OhXKUjqeLmB0A0l3Ac8DGQ6EcSRtgPCiej8Boabn21K2OBfq64KwW/MMh/FWTHndyBF/lhfEos7tGPvrDN+5G05oGjf0fnMOxsmAUdTDbtOTTeMTvDwjJdzsGUluEDbWBYPNlg5wacbimkv51/Bm4YwsGOkkUTy6eCCS3d5j8PrMbB2oNZfByga01FohhWSX9bv35KAP4nq7no9M6nXj8rQVsF0gPndPK/pgX46tpJG+pE1Ul6sSLR2jnrN6oBKzhdZJ54a2wwFSd207Zvahdx3m9JEVhccmDxWltxjKHz+zChAHsqWC9Zcqozt0mDRJNalW8fRXKcSWPGVy1rfbwltiQzij+ChCQQlUG78zW8lU7Bz6FuyDsEFpZSat7jtbdDBY0a4F0yb4lkNvu+5heg+dhlKCFj9YeRDrnvcz94OKvAZW1Gsjbs83n6wphBipxUWku7y86iYyAAYQGKs4jihhYWrFtfZhSf1m6EUKXoWX87KQ== antal.buss@gmail.com"
        ]
    ),
    extra_shell_init="""
        alias ls=lsd
        export EDITOR=nvim
    """,
    environment_vars={
        "PATH": "$HOME/.local/bin:$PATH",
    },
    dotfile_manager=Stow(
        # source_dir="~/.dotfiles",
        # target_dir="~/",
        repo_url="https://github.com/abuss/dotconfig",
    ),
    # programs=Programs(
    programs={
        "git": Program(
            enable=True,
            package=arch["git"],
            config=GitConfig(
                {
                    "user.name": "Antal Buss",
                    "user.email": "antal.buss@gmail.com",
                    "core.editor": "nvim",
                }
            ),
        ),
        "starship": Program(enable=True, package=arch["starship"], deploy_config=True),
        "ghostty": Program(enable=True, package=arch["ghostty"], deploy_config=True),
        #         "fish": c.Program(enable=True),
        "zsh": Program(enable=True, package=arch["zsh"], deploy_config=True),
        "neovim": Program(enable=True, package=arch["neovim"], deploy_config=True),
        "helix": Program(enable=True, package=arch["helix"], deploy_config=True),
        "emacs": Program(
            enable=False,
            package=arch["emacs-wayland"],
            deploy_config=True,
            extra_packages=arch["aspell", "aspell-en"],
        ),
        #         "dconf": c.Program(
        #             enable=True,
        #             config="gnome_dconf_settings",  # Reference to gnome config
        #         ),
    },
    file=File(
        {
            "~/.face": Source("example/assets/face"),
            "~/.config/backgound.png": Source("example/assets/background.png"),
        },
    ),
    services={
        "syncthing": Service(
            enable=False,
            package=arch["syncthing"],
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
        # "gtk",  # GTK themes
    ],
)

# packages = cli.packages + development.packages
conf.packages = Packages(
    arch[
        "iw",
        "stow",
        "mc",
        "less",
        "neovim",
        "htop",
        "libgtop",
        "zsh",
        # "power-profiles-daemon",
        "system-config-printer",
        # "git",
        # "ghostty",
        # "alacritty",
        # "blueman", # TODO: Maybe a better location is required
        # AUR packages
        # Flatpak packages
        # "flatpak:com.visualstudio.code",
        # "distrobox",
        # "podman",
        # "qemu-desktop",
        # "spice-gtk",
        # "remmina",
        # "papers",
        "firefox",
        # "thunderbird",
        # "freecad",
        # "openscad",
        # "prusa-slicer",
    ]
    + aur[
        # "visual-studio-code-bin",
        # "opera",
        # "quickemu",
        # "uxplay",
        # "megasync-bin",
        "brave-bin",
        # "zen-browser-bin",
    ]
    # CLI tools
    + cli.packages(arch, aur)
    # Development tools
    # + development.packages(arch)
    # Flatpak packages
    + flatpak[
        # "com.mattjakeman.ExtensionManager",
        # "freecad",
        # "openscad",
        # "prusa-slicer",
        "net.nokyan.Resources",
        "dev.edfloreshz.CosmicTweaks",
    ]
)

# System services configuration
conf.services = Services(
    {
        "fwupd": Service(enable=False, package=arch["fwupd"]),
        "tailscale": Service(enable=False, package=arch["tailscale"]),
        "networkmanager": Service(
            enable=True,
            package=arch["networkmanager"],
            service_name="NetworkManager",
        ),
        "openssh": Service(
            enable=True,
            package=arch["openssh"],
            service_name="sshd",
            settings={"PermitRootLogin": False},
        ),
        "avahi": Service(enable=False, package=arch["avahi"]),
        "cups": Service(
            enable=False,
            package=arch["cups"],
            extra_packages=arch["gutenprint"] + aur["brother-dcp-l2550dw"],
        ),
        "bluetooth": Service(
            enable=False, package=arch["bluez"], service_name="bluetooth"
        ),
    }
)
# conf.services["avahi"].enable = False

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
    from pykod.cli import run

    run(conf)
