import sys

sys.path.insert(0, "src")

from pykod import Configuration
from pykod.dotfiles import Stow
from pykod.openssh import OpenSSH

import cli
import development
import disk
# import pykod


def configuration():
    c = Configuration("eszkoz")
    print("Configuration module loaded.")

    c.ArchRepo("https://mirror.rackspace.com/archlinux")
    c.AURRepo("yay", "https://aur.archlinux.org/yay-bin.git")
    c.FlatpakRepo("flathub")

    c.Device(
        {
            # "disk0": disk.disk_definition("/dev/nvme0n1", "34GB"),
            "disk0": disk.disk_definition("/dev/sda", "34GB"),
        }
    )

    c.Boot(
        c.Kernel(
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
        c.Loader(
            type="systemd-boot",
            timeout=10,
            include=["memtest86+"],
        ),
    )

    c.Locale(
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

    c.Network(
        hostname="eszkoz",
        settings={"ipv6": True},
    )

    # Hardware services configuration
    c.HardwareManager(
        services={
            "sane": c.Service(enable=True, extra_packages=["sane", "sane-airscan"]),
            "pipewire": c.Service(
                enable=True,
                extra_packages=["pipewire", "pipewire-alsa", "pipewire-pulse"],
            ),
        }
    )

    # Desktop environment configuration - using DesktopManager directly
    c.DesktopManager(
        environments={
            # Traditional desktop environments
            "gnome": c.DesktopEnvironment(
                enable=True,
                display_manager="gdm",
                exclude_packages=["gnome-tour", "yelp"],
                extra_packages=[
                    "gnome-tweaks",
                    "showtime",
                    "gnome-connections",
                    "gnome-shell-extension-appindicator",
                    "aur:gnome-shell-extension-dash-to-dock",
                    "aur:gnome-shell-extension-blur-my-shell",
                    "aur:gnome-shell-extension-arc-menu-git",
                    "aur:gnome-shell-extension-gsconnect",
                    "gnome-shell-extension-weather-oclock",
                    "flatpak:com.mattjakeman.ExtensionManager",
                ],
            ),
            "plasma": c.DesktopEnvironment(
                enable=False,
                display_manager="sddm",
                extra_packages=["kde-applications"],
            ),
            "cosmic": c.DesktopEnvironment(
                enable=True, display_manager="cosmic-greeter"
            ),
            "budgie": c.DesktopEnvironment(
                enable=False,
                display_manager="lightdm",
                extra_packages=["lightdm-gtk-greeter", "network-manager-applet"],
            ),
            "cinnamon": c.DesktopEnvironment(enable=False, display_manager="gdm"),
            # Wayland compositors
            "hyprland": c.DesktopEnvironment(
                enable=False,
                display_manager="greetd",
                extra_packages=[
                    "hyprland",
                    "hyprpaper",
                    "waybar",
                    "wofi",
                    "dunst",
                    "grim",
                    "slurp",
                    "wl-clipboard",
                ],
            ),
        }
    )

    # Fonts configuration
    c.Fonts(
        font_dir=True,
        packages=[
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
            "aur:ttf-work-sans",
        ],
    )

    c.User(username="root", shell="/bin/bash")

    c.User(
        username="abuss",
        name="Antal Buss",
        shell="/usr/bin/zsh",
        groups=["audio", "input", "users", "video", "wheel"],
        allow_sudo=True,
        # TODO: Set password and SSH keys from environment variables or secure config
        hashed_password="$6$MOkGLOzXlj0lIE2d$5sxAysiDyD/7ZfntgZaN3vJ48t.BMi2qwPxqjgVxGXKXrNlFxRvnO8uCvOlHaGW2pVDrjt0JLNR9GWH.2YT5j.",
        ssh_authorized=OpenSSH(
            keys=[
                "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDOA6V+TZJ+BmBAU4FB0nbhYQ9XOFZwCHdwXTuQkb77sPi6fVcbzso5AofUc+3DhfN56ATNOOslvjutSPE8kIp3Uv91/c7DE0RHoidNl3oLre8bau2FT+9AUTZnNEtWH/qXp5+fzvGk417mSL3M5jdoRwude+AzhPNXmbdAzn08TMGAkjGrMQejXItcG1OhXKUjqeLmB0A0l3Ac8DGQ6EcSRtgPCiej8Boabn21K2OBfq64KwW/MMh/FWTHndyBF/lhfEos7tGPvrDN+5G05oGjf0fnMOxsmAUdTDbtOTTeMTvDwjJdzsGUluEDbWBYPNlg5wacbimkv51/Bm4YwsGOkkUTy6eCCS3d5j8PrMbB2oNZfByga01FohhWSX9bv35KAP4nq7no9M6nXj8rQVsF0gPndPK/pgX46tpJG+pE1Ul6sSLR2jnrN6oBKzhdZJ54a2wwFSd207Zvahdx3m9JEVhccmDxWltxjKHz+zChAHsqWC9Zcqozt0mDRJNalW8fRXKcSWPGVy1rfbwltiQzij+ChCQQlUG78zW8lU7Bz6FuyDsEFpZSat7jtbdDBY0a4F0yb4lkNvu+5heg+dhlKCFj9YeRDrnvcz94OKvAZW1Gsjbs83n6wphBipxUWku7y86iYyAAYQGKs4jihhYWrFtfZhSf1m6EUKXoWX87KQ== antal.buss@gmail.com"
            ]
        ),
        dotfile_manager=Stow(
            source_dir="~/.dotfiles",
            target_dir="~/",
            repo_url="http://git.homecloud.lan/abuss/dotconfig.git",
        ),
        programs=c.ProgramManager(
            programs={
                "git": c.Program(
                    enable=True,
                    config={
                        "user.name": "Antal Buss",
                        "user.email": "antal.buss@gmail.com",
                        "core.editor": "helix",
                    },
                ),
                "starship": c.Program(enable=True, deploy_config=True),
                "fish": c.Program(enable=True),
                "zsh": c.Program(enable=True, deploy_config=True),
                "neovim": c.Program(enable=True, deploy_config=True),
                "helix": c.Program(enable=True, deploy_config=True),
                "emacs": c.Program(
                    enable=True,
                    package="emacs-wayland",
                    deploy_config=True,
                    extra_packages=["aspell", "aspell-en"],
                ),
                "dconf": c.Program(
                    enable=True,
                    config="gnome_dconf_settings",  # Reference to gnome config
                ),
            }
        ),
        services={
            "syncthing": c.UserService(
                enable=True,
                config={
                    "service_name": "syncthing",
                    "options": "'--no-browser' '--no-restart' '--logflags=0' '--gui-address=0.0.0.0:8384'",
                },
            )
        },
        deploy_configs=[
            "home",  # General config for home directory
            "gtk",  # GTK themes
            "ghostty",  # Terminal config
        ],
    )

    # packages = cli.packages + development.packages
    c.Packages(
        [
            "iw",
            "stow",
            "mc",
            "less",
            "neovim",
            "htop",
            "libgtop",
            "power-profiles-daemon",
            "system-config-printer",
            "git",
            "ghostty",
            # "alacritty",
            # "blueman", # TODO: Maybe a better location is required
            # AUR packages
            "aur:visual-studio-code-bin",
            "aur:opera",
            # Flatpak packages
            # "flatpak:com.mattjakeman.ExtensionManager",
            # "flatpak:com.visualstudio.code",
            "distrobox",
            "podman",
            "aur:quickemu",
            "qemu-desktop",
            "spice-gtk",
            "aur:uxplay",
            "aur:megasync-bin",
            "remmina",
            "papers",
            "firefox",
            "thunderbird",
            "aur:brave-bin",
            "aur:zen-browser-bin",
            "freecad",
            "openscad",
            "prusa-slicer",
        ]
        + cli.packages
        + development.packages
    )

    # System services configuration
    c.ServiceManager(
        services={
            "fwupd": c.Service(enable=True),
            "tailscale": c.Service(enable=True),
            "networkmanager": c.Service(enable=True, service_name="NetworkManager"),
            "nix": c.Service(enable=True, service_name="nix_daemon"),
            "openssh": c.Service(
                enable=True, service_name="sshd", settings={"PermitRootLogin": False}
            ),
            "avahi": c.Service(enable=True),
            "cups": c.Service(
                enable=True, extra_packages=["gutenprint", "aur:brother-dcp-l2550dw"]
            ),
            "bluetooth": c.Service(
                enable=True, service_name="bluetooth", package="bluez"
            ),
        }
    )

    # System mount configuration (disabled by default)
    c.MountManager(
        mounts={
            "data": c.SystemdMount(
                type="cifs",
                what="//mmserver.lan/NAS1",
                where="/mnt/data",
                description="MMserverNAS1",
                options="vers=2.1,credentials=/etc/samba/mmserver-cred,iocharset=utf8,rw,x-systemd.automount,uid=1000",
                after="network.target",
                wanted_by="multi-user.target",
                automount=True,
                automount_config="TimeoutIdleSec=0",
            ),
            "library": c.SystemdMount(
                type="nfs",
                what="homenas2.lan:/data/Documents",
                where="/mnt/library/",
                description="Document library",
                options="noatime,x-systemd.automount,noauto",
                after="network.target",
                wanted_by="multi-user.target",
                automount=True,
                automount_config="TimeoutIdleSec=600",
            ),
        }
    )
    return c


print("--------------------------------------")
conf = configuration()


def install(conf):
    for i, sec in enumerate(conf.system_config, 1):
        # print(f"{i} -", type(sec).__name__)
        if hasattr(sec, "install"):
            sec.install()


install(conf)
# print(f"{conf.system_config = }")

print("--------------------------------------")
