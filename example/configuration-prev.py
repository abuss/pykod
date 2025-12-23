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

from pykod import Configuration, ndict
from pykod.devices import Devices, Disk, Partition

# from pykod.disk import Partition
from pykod.repositories import AUR, Arch, Flatpak, Repository

conf = Configuration()
use_virtualization = False

git_config = ndict
syncthing_config = ndict
stow_config = ndict
themes_config = ndict
mount_config = ndict

use_gnome = True
use_plasma = False
use_cosmic = True

with conf as c:
    import cli
    import development
    import pykod.disk as disk

    import pykod.openssh as openssh
    from pykod import config

    archpkgs = Arch(url="https://mirror.rackspace.com/archlinux")
    aurpkgs = AUR(helper="yay", helper_url="https://aur.archlinux.org/yay-bin.git")
    flatpakpkgs = Flatpak(hub_url="flathub")

    device = Devices(
        disk0=Disk(
            device="/dev/vda",
            partitions=[
                Partition(name="efi", params="size=512M"),
                Partition(name="root", params="size=20G"),
                Partition(name="swap", params="size=2G"),
                Partition(name="home", params="size=remaining"),
            ],
        ),
    )

    # fileSystems."/" = {
    #   device = "/dev/sda1";
    #   fsType = "ext4";
    # };

    boot = Boot(
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
    )

    # boot.loader = {
    #     "type": "systemd-boot",
    #     "timeout": 10,
    #     "include": ["memtest86+"],
    # }

    # boot.loader = {"system-boot": {"enable": True}}
    # boot.loader.type = "systemd-boot"
    # boot.loader.timeout = 30
    # boot.loader.include = ["memtest86+"]

    loader = ndict(
        type="systemd-boot",
        timeout=10,
        include=["memtest86+"],
    )

    # )

    locale = (
        Locale(
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
        ),
    )

    network = ndict(
        hostname="demo",
        settings={"ipv6": True},
    )

    network.hostname = "eszkoz"
    # network.settings = {"ipv6": True}
    # network = Network(
    #     hostname="eszkoz",
    #     settings={"ipv6": True},
    # )

    users = Users()

    users.root = User(no_password=True, shell="/bin/bash")

    users.abuss = User(
        name="Antal Buss",
        # hashed_password = "$6$q5r7h6qJ8nRats.X$twRR8mUf5y/oKae4doeb6.aXhPhh4Z1ZcAz5RJG38MtPRpyFjuN8eCt9GW.a20yZK1O8OvVPtJusVHZ9I8Nk/.";
        hashed_password="$6$MOkGLOzXlj0lIE2d$5sxAysiDyD/7ZfntgZaN3vJ48t.BMi2qwPxqjgVxGXKXrNlFxRvnO8uCvOlHaGW2pVDrjt0JLNR9GWH.2YT5j.",
        shell="/usr/bin/zsh",
        extra_groups=["audio", "input", "users", "video", "wheel"]
        + (["docker", "podman", "libvirt"] if use_virtualization else []),
        openssh_authorized=ndict(
            keys=[
                "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDOA6V+TZJ+BmBAU4FB0nbhYQ9XOFZwCHdwXTuQkb77sPi6fVcbzso5AofUc+3DhfN56ATNOOslvjutSPE8kIp3Uv91/c7DE0RHoidNl3oLre8bau2FT+9AUTZnNEtWH/qXp5+fzvGk417mSL3M5jdoRwude+AzhPNXmbdAzn08TMGAkjGrMQejXItcG1OhXKUjqeLmB0A0l3Ac8DGQ6EcSRtgPCiej8Boabn21K2OBfq64KwW/MMh/FWTHndyBF/lhfEos7tGPvrDN+5G05oGjf0fnMOxsmAUdTDbtOTTeMTvDwjJdzsGUluEDbWBYPNlg5wacbimkv51/Bm4YwsGOkkUTy6eCCS3d5j8PrMbB2oNZfByga01FohhWSX9bv35KAP4nq7no9M6nXj8rQVsF0gPndPK/pgX46tpJG+pE1Ul6sSLR2jnrN6oBKzhdZJ54a2wwFSd207Zvahdx3m9JEVhccmDxWltxjKHz+zChAHsqWC9Zcqozt0mDRJNalW8fRXKcSWPGVy1rfbwltiQzij+ChCQQlUG78zW8lU7Bz6FuyDsEFpZSat7jtbdDBY0a4F0yb4lkNvu+5heg+dhlKCFj9YeRDrnvcz94OKvAZW1Gsjbs83n6wphBipxUWku7y86iYyAAYQGKs4jihhYWrFtfZhSf1m6EUKXoWX87KQ== antal.buss@gmail.com",
            ]
        ),
        programs=ndict(
            git=ndict(
                enable=True,
                config=git_config(
                    user_name="Antal Buss",
                    user_email="antal.buss@gmail.com",
                    core_editor="helix",
                ),
            ),
            starship=ndict(enable=True, deploy_config=True),
            fish=ndict(enable=True),
            zsh=ndict(
                enable=True,
                deploy_config=True,
            ),
            #     -- extra_packages = {
            #     	-- "aur:zinit",
            # --         -- "zsh-syntax-highlighting",
            # --         "zsh-autosuggestions",
            # --         "zsh-completions",
            # --         -- "zsh-history-substring-search",
            #     -- };
            # --     -- autosuggestion = true,
            # --     -- enable_vfe_integration = true,
            # --     -- default_keymap = "emacs",
            # ),
            neovim=ndict(
                enable=True,
                deploy_config=True,
            ),
            helix=ndict(
                enable=True,
                deploy_config=True,
                # -- package = "aur:evil-helix-bin",
            ),
            emacs=ndict(
                enable=True,
                package=archpkgs["emacs-wayland"],
                # package = aurpkgs.p("emacs-pgtk-igc-git"),
                deploy_config=True,
                extra_packages=archpkgs["aspell", "aspell-en"],
            ),
            # Gnome dconf configuration
            # dconf = ndict(
            # 	enable = use_gnome,
            # 	config = configs.dconf(require("gnome")),
            # ),
        ),
    )
    # print(users.abuss.programs.emacs.extra_packages)

    users.abuss.dotfile_manager = stow_config(
        source_dir="~/.dotfiles",
        target_dir="~/",
        repo_url="http://git.homecloud.lan/abuss/dotconfig.git",
        deploy_configs=[
            "home",  # General config for home directory (face, background, etc.)
            "gtk",  # GTK themes
            "ghostty",
        ],
    )

    users.abuss.services = ndict(
        syncthing=ndict(
            enable=True,
            config=syncthing_config(
                service_name="syncthing",
                options="'--no-browser' '--no-restart' '--logflags=0' '--gui-address=0.0.0.0:8384'",
            ),
            # -- extra_packages = { "aur:syncthing-gtk" },
        )
    )

    users.abuss.home = ndict(
        colloid_theme=themes_config(
            # -- repo_url = "https://github.com/vinceliuice/Colloid-gtk-theme.git";
            repo_url="https://github.com/vinceliuice/WhiteSur-gtk-theme.git",
            # -- tweaks = "normal";
        ),
        colloid_icon_theme=themes_config(
            # -- repo_url = "https://github.com/vinceliuice/Colloid-icon-theme.git";
            repo_url="https://github.com/vinceliuice/WhiteSur-icon-theme.git",
            # -- scheme = "nord";
        ),
        # -- [".config/background"] = copy_file("background"),
        # -- [".face"] = copy_file("face.jpg"),
    )

    # user.zsh.enable = True

    desktop = ndict(
        # -- display_manager = "gdm",
        # -- display_manager = "sddm",
        # -- display_manager = "lightdm",
        desktop_manager=ndict(
            gnome=ndict(
                enable=use_gnome,
                display_manager="gdm",
                exclude_packages=archpkgs[
                    "gnome-tour",
                    "yelp",
                ],
                extra_packages=archpkgs[
                    "gnome-tweaks",
                    "showtime",
                    "gnome-connections",
                    # -- "gnome-extra",
                    # -- "gnome-themes-extra",
                    "gnome-shell-extension-appindicator",
                    "aur:gnome-shell-extension-dash-to-dock",
                    "aur:gnome-shell-extension-blur-my-shell",
                    "aur:gnome-shell-extension-arc-menu-git",
                    "aur:gnome-shell-extension-gsconnect",
                    "gnome-shell-extension-weather-oclock",
                    # -- "aur:nordic-theme",
                    # -- "aur:whitesur-gtk-theme-git",
                    # -- "aur:whitesur-icon-theme-git",
                ]
                + flatpakpkgs["flatpak:com.mattjakeman.ExtensionManager",],
            ),
            plasma=ndict(
                enable=use_plasma,
                display_manager="sddm",
                extra_packages=archpkgs[
                    "kde-applications",
                    # -- "aur:plasma5-themes-whitesur-git",
                ],
            ),
            cosmic=ndict(
                enable=use_cosmic,
                display_manager="cosmic-greeter",
            ),
            budgie=ndict(
                enable=False,  # use_budgie,
                display_manager="lightdm",
                extra_packages=archpkgs[
                    "lightdm-gtk-greeter",
                    "network-manager-applet",
                ],
            ),
            cinnamon=ndict(
                enable=False,  # use_cinnamon,
                display_manager="gdm",
            ),
        ),
    )

    fonts = ndict(
        font_dir=True,
        packages=archpkgs[
            # -- (nerdfonts.override { fonts = [ "FiraCode" "SourceCodePro" "UbuntuMono" ]; })
            "ttf-firacode-nerd",
            "ttf-nerd-fonts-symbols",
            "ttf-nerd-fonts-symbols-common",
            "ttf-sourcecodepro-nerd",
            "ttf-fira-sans",
            "ttf-fira-code",
            # -- "fira-code-symbols",
            "ttf-liberation",
            "noto-fonts-emoji",
            "adobe-source-serif-fonts",
            # -- "source-serif",
            "ttf-ubuntu-font-family",
        ]
        + aurpkgs["ttf-work-sans",],
    )

    packages = (
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
            "git",
            "ghostty",
            "distrobox",
            "podman",
            "qemu-desktop",
            "spice-gtk",
            "remmina",
            "papers",
            "firefox",
            "thunderbird",
        ]
        + aurpkgs[
            "quickemu",
            # -- "alacritty",
            # -- "blueman", -- TODO: Maybe a better location is required
            # -- AUR packages
            "visual-studio-code-bin",
            "opera",
            # -- Flatpak packages
            # -- "flatpak:com.mattjakeman.ExtensionManager",
            # -- "flatpak:com.visualstudio.code",
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

    services = ndict(
        # -- Firmware update
        fwupd={"enable": True},
        tailscale={"enable": True},
        # -- TODO: Maybe move inside network
        networkmanager=ndict(
            enable=True,
            service_name="NetworkManager",
        ),
        nix=ndict(
            enable=True,
            service_name="nix_daemon",
        ),
        openssh=ndict(
            enable=True,
            service_name="sshd",
            settings={
                "PermitRootLogin": False,
            },
        ),
        avahi=ndict(
            enable=True,
            # --     nssmdns = true,
            # --     publish = {
            # --         enable = true,
            # --         domain = true,
            # --         userServices = true
            # --     },
        ),
        cups=ndict(
            enable=True,
            extra_packages=archpkgs["gutenprint"] + aurpkgs["brother-dcp-l2550dw"],
        ),
        # -- https://wiki.archlinux.org/title/Bluetooth
        bluetooth=ndict(
            enable=True,
            service_name="bluetooth",
            package=archpkgs["bluez"],
            # -- settings = {
            # -- General = {
            # -- Enable = "Source,Sink,Media,Socket",
            # -- },
            # -- },
        ),
        systemd=ndict(
            enable=False,
            mount=mount_config(
                data=ndict(
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
                library=ndict(
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
            ),
        ),
    )


if __name__ == "__main__":
    print("-" * 100)
    # Print all attributes from conf
    print("Configuration attributes:")
    for attr_name in dir(conf):
        if not attr_name.startswith("_"):
            attr_value = getattr(conf, attr_name)
            print(f"> {attr_name}: {attr_value} :: {type(attr_value)}")
    # pprint.pp(conf)
    # print(dir(objx))

    print("\n", "-" * 100)
    # print(conf.repos)
    # for k, v in conf.get("repos", {}).items():
    #     print(k)
    #     v.install()

    for attr_name in dir(conf):
        if not attr_name.startswith("_"):
            attr_value = getattr(conf, attr_name)
            if isinstance(attr_value, Repository):
                print(f"====> {attr_name}: {attr_value} :: {type(attr_value)}")
                attr_value.install()

    # print(conf.ret)
    # print(conf.archpkgs._pkgs)
    # print(conf.aurpkgs._pkgs)
    # print(conf.packages)
    print("\n", "-" * 80)
    print(conf.device)
    print(Partition("demo", "size=45", False))
