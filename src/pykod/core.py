"""Core functions for configuring the system."""

from pathlib import Path
from typing import Any

from pykod.common import exec, exec_chroot, get_dry_run, open_with_dry_run

# from pykod.devices import FsEntry
from pykod.repositories.base import Repository

os_release = """NAME="KodOS Linux"
VERSION="1.0"
PRETTY_NAME="KodOS Linux"
ID=kodos
ANSI_COLOR="38;2;23;147;209"
HOME_URL="https://github.com/kodos-prj/kodos/"
DOCUMENTATION_URL="https://github.com/kodos-prj/kodos/"
SUPPORT_URL="https://github.com/kodos-prj/kodos/"
BUG_REPORT_URL="https://github.com/kodos-prj/kodos/issues"
RELEASE_TYPE="expeirimental"
"""


def generate_fstab(config, partiton_list: list, mount_point: str) -> None:
    """
    Generate a fstab file at the specified mount point based on a list of Partitions.

    Args:
        partiton_list (List): A list of Partition objects to be written to the fstab file.
        mount_point (str): The mount point where the fstab file will be written.
    """
    print("Generating fstab")

    with open_with_dry_run(f"{mount_point}/etc/fstab", "w") as f:
        for part in partiton_list:
            if part.source[:5] == "/dev/":
                uuid = exec(f"lsblk -o UUID {part.source} | tail -n 1", get_output=True)
                if uuid:
                    part.source = f"UUID={uuid.strip()}"
            f.write(str(part) + "\n")


def configure_system(mount_point: str) -> None:
    """Configure a system based on the given configuration."""
    # Replace default os-release
    with open_with_dry_run(f"{mount_point}/etc/os-release", "w") as f:
        f.write(os_release)

    # Configure schroot
    system_schroot = """[system]
type=directory
description=KodOS
directory=/
groups=users,root
root-groups=root,wheel
profile=kodos
personality=linux
"""
    with open_with_dry_run(f"{mount_point}/etc/schroot/chroot.d/system.conf", "w") as f:
        f.write(system_schroot)

    venv_schroot = """[virtual_env]
type=directory
description=KodOS
directory=/
union-type=overlay
groups=users,root
root-groups=root,wheel
profile=kodos
personality=linux
aliases=user_env
"""
    with open_with_dry_run(
        f"{mount_point}/etc/schroot/chroot.d/virtual_env.conf", "w"
    ) as f:
        f.write(venv_schroot)

    # Setting profile
    kodos_dir = Path(mount_point) / "etc" / "schroot" / "kodos"
    # print(f"{use_dry_run=}, {kodos_dir=}")
    if get_dry_run():
        print(f"[dry-run] mkdir -p {kodos_dir}")
        print(f"[dry-run] touch {kodos_dir / 'copyfiles'}")
        print(f"[dry-run] touch {kodos_dir / 'nssdatabases'}")
    else:
        kodos_dir.mkdir(parents=True, exist_ok=True)
        (kodos_dir / "copyfiles").touch()
        (kodos_dir / "nssdatabases").touch()

    venv_fstab = (
        "# <file system> <mount point>   <type>  <options>       <dump>  <pass>"
    )
    for mpoint in [
        "/proc",
        "/sys",
        "/dev",
        "/dev/pts",
        "/home",
        "/root",
        "/tmp",
        "/run",
        "/var/cache",
        "/var/log",
        "/var/tmp",
        "/var/kod",
    ]:
        venv_fstab += f"{mpoint}\t{mpoint}\tnone\trw,bind\t0\t0\n"

    with open_with_dry_run(f"{mount_point}/etc/schroot/kodos/fstab", "w") as f:
        f.write(venv_fstab)


def get_kernel_version(mount_point: str) -> str:
    """Retrieve the kernel version from the specified mount point."""
    kernel_version = exec_chroot(
        "uname -r", mount_point=mount_point, get_output=True
    ).strip()
    return kernel_version


def create_boot_entry(
    generation: int,
    partition_list: list,
    boot_options: list[str] | None = None,
    is_current: bool = False,
    mount_point: str = "/mnt",
    kver: str | None = None,
) -> None:
    """
    Create a systemd-boot loader entry for the specified generation.

    Args:
        generation (int): The generation number to create an entry for.
        partition_list (list): A list of Partition objects to use for determining the root device.
        boot_options (list, optional): A list of additional boot options to include in the entry.
        is_current (bool, optional): If True, the entry will be named "kodos" and set as the default.
        mount_point (str, optional): The mount point of the chroot environment to write the entry to.
        kver (str, optional): The kernel version to use in the entry. If not provided, the current kernel
            version will be determined using `uname -r` in the chroot environment.
    """
    subvol = f"generations/{generation}/rootfs"
    root_fs = [part for part in partition_list if part.destination in ["/"]][0]
    root_device = root_fs.source_uuid()
    options = " ".join(boot_options) if boot_options else ""
    options += f" rootflags=subvol={subvol}"
    entry_name = "kodos" if is_current else f"kodos-{generation}"

    if not kver:
        kver = get_kernel_version(mount_point)

    today = exec("date +'%Y-%m-%d %H:%M:%S'", get_output=True).strip()
    entry_conf = f"""
title KodOS
sort-key kodos
version Generation {generation} KodOS (build {today} - {kver})
linux /vmlinuz-{kver}
initrd /initramfs-linux-{kver}.img
options root={root_device} rw {options}
    """
    entries_path = f"{mount_point}/boot/loader/entries/"
    entries_path_obj = Path(entries_path)
    if not entries_path_obj.is_dir():
        if get_dry_run():
            print(f"[dry-run] mkdir -p {entries_path}")
        else:
            entries_path_obj.mkdir(parents=True, exist_ok=True)
    with open_with_dry_run(
        f"{mount_point}/boot/loader/entries/{entry_name}.conf", "w"
    ) as f:
        f.write(entry_conf)

    # Update loader.conf
    loader_conf_systemd = f"""
default {entry_name}.conf
timeout 10
console-mode keep
"""
    with open_with_dry_run(f"{mount_point}/boot/loader/loader.conf", "w") as f:
        f.write(loader_conf_systemd)


def setup_bootloader(conf: Any, partition_list: list, base: Repository) -> None:
    # bootloader
    """
    Set up the bootloader based on the configuration.

    Args:
        conf (dict): The configuration dictionary.
        partition_list (list): A list of Partition objects to use for determining the root device.
    """

    print("\n\n[install] Setting up bootloader")
    # boot_conf = conf.boot
    loader_conf = conf.loader

    kernel_package = base["linux"]
    if hasattr(conf, "kernel"):
        kernel_conf = conf.kernel
        if hasattr(kernel_conf, "package"):
            kernel_package = kernel_conf.package

    # Default bootloader
    boot_type = "systemd-boot"

    if hasattr(loader_conf, "type"):
        boot_type = loader_conf.type

    # Using systemd-boot as bootloader
    if boot_type == "systemd-boot":
        print("==== Setting up systemd-boot ====")
        kver = base.setup_linux("/mnt", kernel_package)
        # if base_distribution == "arch":
        #     kernel_file, kver = get_kernel_file(mount_point="/mnt", package=kernel_package)
        #     exec_chroot(f"cp {kernel_file} /boot/vmlinuz-linux-{kver}")
        # else:
        #     kernel_file, kver = get_kernel_file(mount_point="/mnt", package=kernel_package)
        exec_chroot("bootctl install")
        print("KVER:", kver)
        exec_chroot(f"dracut --kver {kver} --hostonly /boot/initramfs-linux-{kver}.img")
        create_boot_entry(0, partition_list, mount_point="/mnt", kver=kver)

    # Using Grub as bootloader
    if boot_type == "grub":
        pass
        # pkgs_required = ["grub", "efibootmgr", "grub-btrfs"]
        # if "include" in loader_conf:
        #     pkgs_required += loader_conf["include"].values()

        # exec_chroot(f"pacman -S --noconfirm {' '.join(pkgs_required)}")
        # exec_chroot(
        #     "grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=GRUB",
        # )
        # exec_chroot("grub-mkconfig -o /boot/grub/grub.cfg")
        # # pkgs_installed += ["efibootmgr"]


# Core
def create_kod_user(mount_point: str) -> None:
    """
    Create the 'kod' user and give it NOPASSWD access in the sudoers file.

    This function creates a user named 'kod' with a home directory in
    /var/kod/.home and adds it to the wheel group. It also creates a sudoers
    file for the user which allows it to run any command with NOPASSWD.

    Args:
        mount_point (str): The mount point where the installation is being
            performed.
    """
    exec_chroot("useradd -m -r -G wheel -s /bin/bash -d /var/kod/.home kod")
    with open_with_dry_run(f"{mount_point}/etc/sudoers.d/kod", "w") as f:
        f.write("kod ALL=(ALL) NOPASSWD: ALL")
