# Pykod Usage Guide

Pykod is a Python 3.12+ tool to declaratively install and rebuild an Arch Linux system (KodOS) using a Btrfs “generations” layout. It provisions disks, installs packages from multiple repositories (Arch, AUR, Flatpak), enables services, creates users, and configures boot, locale, and network.

This guide walks you through preparing a configuration, running an installation, and performing rebuilds with generations.

## Requirements

- Target OS: Arch Linux (install target). Run from an Arch ISO or an Arch system with root privileges.
- Filesystem: Btrfs for the root device (Pykod creates a generations layout). Other partitions supported as configured.
- Network access: Required for package installation (pacman, AUR helper build, optional Flatpak).
- Destructive warning: Device partitioning/formatting is destructive. Double‑check disk identifiers before running.

## Concepts

- Generations
  - Pykod manages system snapshots as “generations” under `/kod/generations/<N>/rootfs`.
  - A current generation number is tracked by `/.generation`. State files capture desired packages and services for each generation.
  - On rebuild, Pykod can snapshot the current root and apply changes in a chroot, updating the boot loader to boot the new generation.

- Chroots
  - Installation work happens under a mount point (default `/mnt`).
  - Rebuild work for a new generation happens in a temporary chroot rooted under `/kod/current/.next_current`.
  - Commands are executed via `chroot` using the configured mount point.

- Repositories
  - Arch (pacman) is the base repository.
  - Optional AUR repository builds/uses an AUR helper under the chroot (see “AUR helper preparation”).
  - Optional Flatpak repository installs applications from Flathub.

## Quick Start

1) Clone this repository and review the example configuration at `example/configuration.py`.
2) Create/modify your configuration file (you can copy the example and adjust).
3) Run one of:
   - Install (from Arch ISO or a safe environment):
     - `python example/configuration.py install`
   - Rebuild (on an existing KodOS system):
     - `python example/configuration.py rebuild`

Notes:
- The example’s `Configuration.run()` method expects a single `install` or `rebuild` argument. You can also invoke `conf.install()` or `conf.rebuild()` programmatically.
- For experimentation, set `dry_run=True` and/or `debug=True` in `Configuration(...)` (see “Runtime modes”).

## Configuration Model

Create a `Configuration` and attach the following components. See `example/configuration.py` for a full reference.

- Base repository
  - `from pykod.repositories import Arch, AUR, Flatpak`
  - `archpkgs = Arch(mirror_url="https://mirror.rackspace.com/archlinux")`
  - Pass `base=archpkgs` into `Configuration(...)`.

- Devices (disks and partitions)
  - Use `Devices` with one or more `Disk` entries, each with a list of `Partition` objects.
  - Supported partition types include: `esp`, `btrfs`, `linux-swap`, and common filesystems.
  - Pykod will:
    - Wipe the disk partition table.
    - Create partitions with the requested types.
    - Format and mount them under the install mount point.
    - Build a Btrfs generations layout: `/store`, `/generations/0/rootfs`, `/kod`, etc.

- Boot configuration
  - `Boot(Kernel(package=archpkgs["linux"]), Loader(type="systemd-boot", timeout=10))`.
  - Pykod sets up systemd‑boot, copies the kernel to `/boot/vmlinuz-<kver>`, builds `initramfs` with `dracut`, and writes loader entries per generation.

- Locale and Network
  - `Locale(default="en_CA.UTF-8 UTF-8", additional_locales=[...], timezone="America/Edmonton", ...)`.
  - `Network(hostname="myhost", settings={"ipv6": True})` writes basic systemd‑networkd files and `/etc/hosts`.

- Desktop and Fonts
  - `DesktopManager(display_manager=Service(package=archpkgs["gdm"]))` and a dict of `DesktopEnvironment` entries.
    - Each `DesktopEnvironment` can specify a `package`, `extra_packages`, and `exclude_packages`.
    - The display manager service is automatically added to system services for enablement.
  - `Fonts(...)` contributes font package lists (no separate install step required).

- Services
  - `Services({...})` maps service names to `Service(...)` definitions.
  - Each `Service` may specify `package`, `service_name` (systemd unit), and optional config commands.
  - Enabled services are recorded per generation.

- Users
  - Define `User(...)` for root and other accounts.
  - Supports `hashed_password` or `no_password=True`, groups, shell, `ssh_authorized` keys, and a dotfiles manager (`Stow`).
  - `programs` field can declare user programs with `Program(enable=True, package=..., deploy_config=True|False, config=[...])`.
  - User services (systemd user units) can be enabled via the `services` dict.

- Packages
  - Combine repo‑scoped package lists using `+`:
    - `archpkgs["git", "neovim"] + aurpkgs["paru"] + flatpakpkgs["com.visualstudio.code"]`
  - Assign to `conf.packages` or embed within Desktop/Fonts/Services/Users. Pykod walks the configuration and collects all `PackageList` instances, then computes install/remove actions.

## Install Flow

High‑level sequence for `install`:

1) Devices
   - Partition/format per `Devices` and build the Btrfs generations layout under `/mnt` by default.
2) Base packages
   - Compute base/kernels via `Arch.get_base_packages(...)` and run `pacstrap`.
   - Refresh package database in chroot.
3) System files
   - Generate `/etc/fstab` with UUIDs and configure schroot profiles, `/etc/os-release`, etc.
4) Boot
   - Set up systemd‑boot, copy kernel/initramfs, and write loader entries for generation 0.
5) Kod user
   - Create `kod` user with NOPASSWD sudo (used for AUR and other tasks).
6) Locale and Network
   - Write timezone, `locale.gen`, `locale.conf`, host/network files.
7) Package installation
   - Collect package sets from the entire configuration (including desktop/fonts/services/users).
   - Prepare repositories (see AUR below) and install included packages; remove excluded packages.
8) Services and Users
   - Enable configured system services.
   - Create users, fetch dotfiles (if configured), deploy user program configs, enable user services.
9) State snapshot
   - Persist desired state to `/mnt/kod/generations/0/installed_packages`, `enabled_services`, and `packages.lock`.

## Rebuild Flow

High‑level sequence for `rebuild`:

1) Determine current and next generation IDs (`/.generation`, top of `/kod/generations`).
2) Create next generation chroot under `/kod/current/.next_current` and mount subvolumes.
3) Optionally `update=True`: for each repo in your configuration, refresh the database and update installed packages inside the chroot.
4) Compute deltas versus the current generation’s recorded packages; install new packages and remove stale ones.
5) If the kernel package changed, update `/boot/vmlinuz-<kver>` and rebuild initramfs in the chroot.
6) Enable/disable services according to the new desired set.
7) Persist next generation’s desired state into `/kod/generations/<N>/...` inside the chroot.
8) Write a new systemd‑boot entry for the next generation and unmount the chroot.

At boot, select the new generation from the systemd‑boot menu. Older generations remain available for rollback.

## AUR Helper Preparation

- Pykod prepares repositories before installs. For AUR, it runs a one‑time bootstrap of the selected helper inside the active chroot.
- The AUR repo provides `prepare(mount_point)` which:
  - Installs `git` and `base-devel` in the chroot if needed.
  - Clones and builds the helper (e.g., `yay`, `paru`) as the `kod` user.
- After preparation, `install_package()` only emits the helper install command; it no longer hardcodes `/mnt`.

## Runtime Modes

- `dry_run=True`
  - Writes to stdout instead of files where safe and prints commands. Intended for planning.
- `debug=True`
  - Prints commands instead of executing them. Useful with `dry_run` to see full flow.
- `verbose=True`
  - Prints commands as they execute for additional context.

## Tips and Pitfalls

- Device safety: Confirm device names (e.g., `/dev/vda`, `/dev/nvme0n1`) and partition plan. The installer wipes partition tables.
- Display manager: The selected display manager service (e.g., `gdm`, `cosmic-greeter`) is added to Services and enabled automatically.
- User dotfiles: Ensure the dotfiles repository is reachable under your network and accessible to the `kod` user in the chroot.
- Flatpak: The first Flatpak use adds the Flathub remote if missing. Ensure the system has Flatpak installed in the chroot before application installs.
- Rollback: You can boot a previous generation from systemd‑boot if the new generation misbehaves.

## Where State Lives

- Desired state per generation
  - `/kod/generations/<N>/installed_packages`: JSON mapping of repos to package lists (plus kernel).
  - `/kod/generations/<N>/enabled_services`: newline‑separated list of enabled services.
  - `/kod/generations/<N>/packages.lock`: captured installed packages with versions (for audit).
- Current generation marker: `/.generation` (inside the root filesystem).

## Example

See a comprehensive example at `example/configuration.py`. It demonstrates:
- Two disks (system + scratch), Btrfs layout, and EFI partition.
- GNOME and COSMIC desktop environments with a display manager and extra packages.
- System services (NetworkManager, PipeWire, CUPS, OpenSSH, etc.).
- Users with dotfiles management (Stow), program configs (git, editors), and a hashed password.
- Mixed package sources: Arch, AUR (paru), Flatpak (Flathub apps).

## Troubleshooting

- Command output
  - Run with `debug=True` or `verbose=True` to see executed commands and flow.
- Chroot issues
  - Ensure mounts are present and the target chroot path exists. Pykod prepares the chroot during install/rebuild.
- Package conflicts
  - Use `exclude_packages` (e.g., in a desktop environment) to remove undesired defaults.
- Kernel/initramfs
  - Rebuild creates/initramfs via `dracut` and copies the kernel into `/boot`. If you switch kernels, Pykod updates the boot entry.

---

Pykod is evolving. The example configuration is the best reference for supported fields and patterns. If you encounter a gap or want a new integration point, open an issue or extend the configuration following the established patterns (PackageList collection, Services enablement, repo prepare/install/remove).
