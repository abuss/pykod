"""Core functions for configuring the system."""

import logging
from pathlib import Path
from typing import Any

from pykod.common import execute_chroot as exec_chroot
from pykod.common import execute_command as exec
from pykod.common import get_dry_run, open_with_dry_run
from pykod.repositories.base import Repository

logger = logging.getLogger("pykod.config")

os_release = """NAME="KodOS Linux"
VERSION="1.0"
PRETTY_NAME="KodOS Linux"
ID=kodos
ANSI_COLOR="38;2;23;147;209"
HOME_URL="https://github.com/kodos-prj/kodos/"
DOCUMENTATION_URL="https://github.com/kodos-prj/kodos/"
SUPPORT_URL="https://github.com/kodos-prj/kodos/"
BUG_REPORT_URL="https://github.com/kodos-prj/kodos/issues"
RELEASE_TYPE="experimental"
"""


def verify_grub_not_installed(mount_point: str, base: Repository) -> None:
    """Verify that GRUB is not installed before systemd-boot installation.

    For Debian/Ubuntu systems, this is a sanity check to ensure our GRUB
    blocking during base installation was successful.

    Args:
        mount_point: Installation mount point
        base: Base repository instance

    Raises:
        ValueError: If GRUB packages are detected (installation should not proceed)
    """
    from pykod.repositories.debian import Debian

    # Only check on Debian/Ubuntu systems
    if not isinstance(base, Debian):
        logger.debug("Not a Debian/Ubuntu system, skipping GRUB verification")
        return

    logger.info("Verifying GRUB is not installed...")

    try:
        # Check for any installed GRUB packages
        check_cmd = "dpkg -l | grep '^ii.*grub' || true"
        result = exec_chroot(check_cmd, mount_point=mount_point, get_output=True)

        if result.strip():
            # GRUB packages found - this is a critical error
            grub_packages = result.strip().split("\n")
            logger.error("GRUB packages detected before systemd-boot installation!")
            logger.error(f"Found packages: {grub_packages}")
            raise ValueError(
                "GRUB packages are installed, cannot proceed with systemd-boot. "
                "This indicates GRUB blocking during base installation failed. "
                f"Detected packages: {result.strip()}"
            )
        else:
            logger.info("✓ Verification passed: No GRUB packages detected")

    except ValueError:
        # Re-raise ValueError from GRUB detection
        raise
    except Exception as e:
        # Warn but continue for other errors (verification failure shouldn't block install)
        logger.warning(
            f"Failed to verify GRUB status: {e}. "
            "Proceeding with systemd-boot installation anyway."
        )


# Filesystem and system configuration functions
def generate_fstab(config, partition_list: list, mount_point: str) -> None:
    """
    Generate a fstab file at the specified mount point based on a list of Partitions.

    Args:
        partition_list (List): A list of Partition objects to be written to the fstab file.
        mount_point (str): The mount point where the fstab file will be written.
    """
    logger.debug(f"Generating fstab for {len(partition_list)} partitions")

    with open_with_dry_run(f"{mount_point}/etc/fstab", "w") as f:
        for part in partition_list:
            if part.source[:5] == "/dev/":
                uuid = exec(f"lsblk -o UUID {part.source} | tail -n 1", get_output=True)
                if uuid:
                    part.source = f"UUID={uuid.strip()}"
            f.write(str(part) + "\n")

    logger.debug("fstab generated successfully")


def configure_system(mount_point: str) -> None:
    """Configure a system based on the given configuration."""
    logger.debug(f"Configuring system at {mount_point}")

    # Replace default os-release
    with open_with_dry_run(f"{mount_point}/etc/os-release", "w") as f:
        f.write(os_release)


#    # Configure schroot
#    system_schroot = """[system]
# type=directory
# description=KodOS
# directory=/
# groups=users,root
# root-groups=root,wheel
# profile=kodos
# personality=linux
# """
#    with open_with_dry_run(f"{mount_point}/etc/schroot/chroot.d/system.conf", "w") as f:
#        f.write(system_schroot)

#    venv_schroot = """[virtual_env]
# type=directory
# description=KodOS
# directory=/
# union-type=overlay
# groups=users,root
# root-groups=root,wheel
# profile=kodos
# personality=linux
# aliases=user_env
# """
#    with open_with_dry_run(
#        f"{mount_point}/etc/schroot/chroot.d/virtual_env.conf", "w"
#    ) as f:
#        f.write(venv_schroot)

#    # Setting profile
#    kodos_dir = Path(mount_point) / "etc" / "schroot" / "kodos"
#    if get_dry_run():
#        logger.debug(f"[dry-run] Creating schroot profile at {kodos_dir}")
#    else:
#        kodos_dir.mkdir(parents=True, exist_ok=True)
#        (kodos_dir / "copyfiles").touch()
#        (kodos_dir / "nssdatabases").touch()

#    venv_fstab = (
#        "# <file system> <mount point>   <type>  <options>       <dump>  <pass>"
#    )
#    for mpoint in [
#        "/proc",
#        "/sys",
#        "/dev",
#        "/dev/pts",
#        "/home",
#        "/root",
#        "/tmp",
#        "/run",
#        "/var/cache",
#        "/var/log",
#        "/var/tmp",
#        "/var/kod",
#    ]:
#        venv_fstab += f"{mpoint}\t{mpoint}\tnone\trw,bind\t0\t0\n"

#    with open_with_dry_run(f"{mount_point}/etc/schroot/kodos/fstab", "w") as f:
#        f.write(venv_fstab)


# Boot-related functions
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
            logger.debug(
                f"[dry-run] Would create boot entries directory: {entries_path}"
            )
        else:
            entries_path_obj.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created boot entries directory: {entries_path}")
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


def setup_bootloader(
    conf: Any, partition_list: list, base: Repository, mount_point: str = "/mnt"
) -> None:
    # bootloader
    """
    Set up the bootloader based on the configuration.

    Note: For Debian/Ubuntu systems, GRUB prevention is handled during
    base package installation (see repositories/debian.py).

    Args:
        conf (dict): The configuration dictionary.
        partition_list (list): A list of Partition objects to use for determining the root device.
        base: Base repository instance for package management.
        mount_point: Installation mount point. Defaults to "/mnt".
    """

    logger.info("Setting up bootloader")
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
        logger.info("Setting up systemd-boot")

        # Verify GRUB is not installed (Debian/Ubuntu safety check)
        verify_grub_not_installed(mount_point, base)

        # Verify kernel package is installed (Debian/Ubuntu pre-flight check)
        from pykod.repositories.debian import Debian

        if isinstance(base, Debian):
            logger.info("Pre-flight check: Verifying kernel package is installed...")
            kernel_check = exec_chroot(
                "dpkg -l | grep '^ii.*linux-image' | head -1",
                mount_point=mount_point,
                get_output=True,
            ).strip()

            if not kernel_check:
                raise RuntimeError(
                    "Cannot setup bootloader: No kernel package installed. "
                    "This indicates base package installation failed. "
                    "Check Step 2 (Base packages) logs for errors."
                )

            logger.debug(f"Kernel package verified: {kernel_check}")

        kver = base.setup_linux(mount_point, kernel_package)
        exec_chroot("bootctl install", mount_point=mount_point)
        logger.debug(f"Kernel version: {kver}")
        base.generate_initramfs(mount_point, kver)
        create_boot_entry(0, partition_list, mount_point=mount_point, kver=kver)

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


# User-related functions
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
    logger.debug("Creating KodOS system user")
    exec_chroot("useradd -m -r -G wheel -s /bin/bash -d /var/kod/.home kod")
    with open_with_dry_run(f"{mount_point}/etc/sudoers.d/kod", "w") as f:
        f.write("kod ALL=(ALL) NOPASSWD: ALL")
    logger.debug("KodOS user created successfully")


def save_configuration(
    config: "Configuration",
    include_pkgs,
    generation_path: Path,
) -> None:
    import json

    # Store configuration instance and repositories as JSON
    config_dict = {}

    # Extract basic configuration attributes
    for attr_name, attr_value in vars(config).items():
        if not attr_name.startswith("_") and attr_name not in ["packages"]:
            try:
                # Try to serialize the attribute
                json.dumps(attr_value)
                config_dict[attr_name] = attr_value
            except (TypeError, ValueError):
                # Skip non-serializable attributes
                config_dict[attr_name] = str(attr_value)

    # Store repositories information with their definitions
    repositories = {}

    # Store base repository definition
    base_repo_attrs = {}
    for attr_name, attr_value in vars(config._base).items():
        if not attr_name.startswith("_"):
            try:
                json.dumps(attr_value)
                base_repo_attrs[attr_name] = attr_value
            except (TypeError, ValueError):
                base_repo_attrs[attr_name] = str(attr_value)

    repositories["base"] = {
        "class_name": config._base.__class__.__name__,
        "type": "base_repository",
        "attributes": base_repo_attrs,
    }

    # Collect all repositories from packages with their definitions
    for repo, packages in include_pkgs.items():
        repo_name = repo.__class__.__name__

        # Extract repository attributes
        repo_attrs = {}
        for attr_name, attr_value in vars(repo).items():
            if not attr_name.startswith("_"):
                try:
                    json.dumps(attr_value)
                    repo_attrs[attr_name] = attr_value
                except (TypeError, ValueError):
                    repo_attrs[attr_name] = str(attr_value)

        repositories[repo_name] = {
            "class_name": repo_name,
            "type": "package_repository",
            "packages": list(packages),
            "attributes": repo_attrs,
        }

    config_dict["repositories"] = repositories

    # Write configuration to JSON file
    config_json_path = generation_path / "configuration.json"
    with open(str(config_json_path), "w") as f:
        json.dump(config_dict, f, indent=2, default=str)

    logger.debug(f"Configuration and repositories stored to: {config_json_path}")


def Source(path: str) -> str:
    return path


class File(dict):
    """File representation for configuration files."""

    def __init__(self, *args, **kwargs):
        """Initialize File object."""
        if len(args) > 0:
            data = args[0]
        else:
            data = kwargs

        super().__init__(data)

    def build_command(self, mount_point: str | None = None) -> list[str]:
        """Return shell commands to copy files into the specified mount point (no execution)."""

        commands = []
        for target_path, source_path in self.items():
            full_target_path = Path(target_path).expanduser()
            if mount_point is not None:
                full_target_path = Path(mount_point) / full_target_path.relative_to("/")
            parent_dir = full_target_path.parent
            full_source_path = Path(source_path).expanduser()
            commands.append(f"mkdir -p {parent_dir}")
            commands.append(f"cp -f {full_source_path} {full_target_path}")
        return commands

    def install(self, mount_point) -> None:
        """Install files to the specified mount point."""
        logger.debug("Installing files")
        commands = self.build_command(mount_point)
        logger.debug(f"File installation commands: {commands}")


def Component(name: str):
    def __init__(self, **kwargs):
        super(self.__class__, self).__init__(**kwargs)

    def __getattr__(self, item):
        return self.get(item, None)

    def __setattr__(self, key, value):
        self[key] = value

    return type(
        name,
        (dict,),
        {"__init__": __init__, "__getattr__": __getattr__, "__setattr__": __setattr__},
    )
