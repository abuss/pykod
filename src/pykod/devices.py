"""Devices configuration."""

from dataclasses import dataclass
from typing import Any, override

from pykod.base import NestedDict

# from pykod.common import fake_exec as exec
from pykod.common import exec
from pykod.core import generate_fstab, setup_bootloader

_filesystem_cmd: dict[str, str | None] = {
    "esp": "mkfs.vfat -F32",
    "fat32": "mkfs.vfat -F32",
    "vfat": "mkfs.vfat",
    "bfs": "mkfs.bfs",
    "cramfs": "mkfs.cramfs",
    "ext3": "mkfs.ext3",
    "fat": "mkfs.fat",
    "msdos": "mkfs.msdos",
    "xfs": "mkfs.xfs",
    "btrfs": "mkfs.btrfs -f",
    "ext2": "mkfs.ext2",
    "ext4": "mkfs.ext4",
    "minix": "mkfs.minix",
    "f2fs": "mkfs.f2fs",
    "linux-swap": "mkswap",
    "noformat": None,
}

_filesystem_type: dict[str, str | None] = {
    "esp": "ef00",
    # "vfat": "",
    "btrfs": "8300",
    "linux-swap": "8200",
    "noformat": None,
}


class Disk(NestedDict):
    """Represents a disk device with partitions."""

    def __init__(self, **kwargs):
        """Initialize Disk with device and partitions."""
        super().__init__(**kwargs)

    @override
    def install(self):
        """Install disk partitions as per configuration."""
        print("\n\n[install] Partitioning disk:", self.device)
        print(f"with partitions {self.partitions}")
        device = self._data.get("device", "")
        partitions = self._data.get("partitions", [])
        boot_part, root_part, part_list = self._create_disk_partitions(
            device, partitions
        )
        return boot_part, root_part, part_list

    def rebuild(self):
        print("[rebuild] Using disk:", self.device)

    def _create_disk_partitions(self, device: str, partitions: list[Any]):
        """Create partitions on a single disk device.

        This function handles the creation of partitions on a single disk according
        to the disk configuration. It wipes the existing partition table, creates
        new partitions with specified filesystems, and sets up mount points.

        Args:
            disk_info: Dictionary containing device path and partition specifications.
                    Expected keys: 'device', 'partitions'

        Returns:
            Tuple containing (boot_partition, root_partition, partitions_list) where
            boot_partition and root_partition are device paths or None,
            and partitions_list contains FsEntry objects for created partitions.
        """
        if "nvme" in device or "mmcblk" in device:
            device_sufix = "p"
        else:
            device_sufix = ""

        # Delete partition table
        exec(f"wipefs -a {device}", f"Failed to wipe partition table on {device}")
        exec("sync", "Failed to sync after wiping partition table")

        print(f"{partitions=}")
        if not partitions:
            return None, None, []

        delay_action = []
        boot_partition = None
        root_partition = None
        partitions_list = []
        for pid, part in enumerate(partitions, 1):
            name = part.name
            size = part.size
            filesystem_type = part.type
            mountpoint = part.mountpoint
            blockdevice = f"{device}{device_sufix}{pid}"

            if name.lower() in ["boot", "efi"]:
                boot_partition = blockdevice
            elif name.lower() == "root":
                root_partition = blockdevice

            end = 0 if size == "100%" else f"+{size}"
            partition_type = _filesystem_type[filesystem_type]

            exec(
                f"sgdisk -n 0:0:{end} -t 0:{partition_type} -c 0:{name} {device}",
                f"Failed to create partition {name} on {device}",
            )

            # Format filesystem
            if filesystem_type in _filesystem_cmd.keys():
                cmd = _filesystem_cmd[filesystem_type]
                if cmd:
                    exec(
                        f"{cmd} {blockdevice}",
                        f"Failed to format {blockdevice} as {filesystem_type}",
                    )

            # if filesystem_type == "btrfs":
            #     delay_action = create_btrfs(delay_action, part, blockdevice)

            if mountpoint and mountpoint != "none":
                install_mountpoint = "/mnt" + mountpoint
                if mountpoint != "/":
                    print(f"[DELAY] mkdir -p {install_mountpoint}")
                    print(f"[DELAY] mount {blockdevice} {install_mountpoint}")
                    delay_action.append(f"mkdir -p {install_mountpoint}")
                    delay_action.append(f"mount {blockdevice} {install_mountpoint}")
                    partitions_list.append(
                        FsEntry(
                            blockdevice, mountpoint, filesystem_type, "defaults", 0, 0
                        )
                    )
                else:
                    delay_action = [
                        f"mkdir -p {install_mountpoint}",
                        f"mount {blockdevice} {install_mountpoint}",
                    ] + delay_action
                    partitions_list.append(
                        FsEntry(
                            blockdevice, mountpoint, filesystem_type, "defaults", 0, 0
                        )
                    )
                print("====>", blockdevice, mountpoint)

        print("=======================")
        if delay_action:
            for cmd_action in delay_action:
                exec(cmd_action)
        print("=======================")

        return boot_partition, root_partition, partitions_list


@dataclass
class Partition:  # (NestedDict, Install, Rebuild):
    name: str
    size: str
    type: str
    mountpoint: str | None = None
    format: bool = True


# class Devices(NestedDict, Install, Rebuild):
class Devices(NestedDict):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._boot_partition = None
        self._root_partition = None
        self._partition_list = []

    def install(self, config, mount_point: str = "/mnt") -> list:
        print(f"[install] in {mount_point} create partitions:")
        print(self._data)
        print("=" * 50)
        disks = [disk for disk in self._data.values() if isinstance(disk, Disk)]
        for disk in disks:
            boot_part, root_part, part_list = disk.install()
            self._partition_list += part_list
            if boot_part:
                if self._boot_partition is None and boot_part:
                    self._boot_partition = boot_part
                else:
                    raise Exception(f"Multiple boot partitions detected! {boot_part}")
            if root_part:
                if self._root_partition is None and root_part:
                    self._root_partition = root_part
                else:
                    raise Exception("Multiple root partitions detected!")

        # print("Partitions list:", self._partition_list)
        # for p in self._partition_list:
        #     print(" >>>", p)
        #
        # Create filesystem hierarchy if we have both boot and root partitions
        if self._boot_partition and self._root_partition:
            partition_list = self._create_filesystem_hierarchy(mount_point)
        else:
            partition_list = []

        # Add any additional partitions that weren't handled by the hierarchy
        # (like scratch, additional data partitions, etc.)
        for p in self._partition_list:
            # Check if this partition is already in the final list
            if not any(
                existing.source == p.source and existing.destination == p.destination
                for existing in partition_list
            ):
                partition_list.append(p)
                print(f"Adding additional partition: {p.source} -> {p.destination}")

        # print("Final partition list:")
        # for p in partition_list:
        #     print("    =>", p)

        # Generate fstab
        # generate_fstab(config, partition_list, mount_point)

        return partition_list

    def rebuild(self) -> None:
        print("[rebuild] Arch repo:", self)
        print("Refresh repos")

    # Core
    def _create_filesystem_hierarchy(self, mount_point: str) -> list:
        # Initial generation
        generation = 0
        for dir in ["store", "generations", "current"]:
            exec(f"mkdir -p {mount_point}/{dir}")

        subdirs = ["root", "var/log", "var/tmp", "var/cache", "var/kod"]
        for dir in subdirs:
            exec(f"mkdir -p {mount_point}/store/{dir}")

        # Create home as subvolume if no /home is specified in the config
        # (TODO: Add support for custom home)
        exec(f"sudo btrfs subvolume create {mount_point}/store/home")

        # First generation
        exec(f"mkdir -p {mount_point}/generations/{generation}")
        exec(f"btrfs subvolume create {mount_point}/generations/{generation}/rootfs")

        # Mounting first generation
        exec(f"umount -R {mount_point}")
        exec(
            f"mount -o subvol=generations/{generation}/rootfs {self._root_partition} {mount_point}"
        )
        partition_list = [
            FsEntry(
                self._root_partition,
                "/",
                "btrfs",
                f"rw,relatime,ssd,space_cache=v2,subvol=generations/{generation}/rootfs",
            )
        ]

        for dir in subdirs + ["boot", "home", "kod"]:
            exec(f"mkdir -p {mount_point}/{dir}")

        exec(f"mount {self._boot_partition} {mount_point}/boot")
        boot_options = "rw,relatime,fmask=0022,dmask=0022,codepage=437,iocharset=ascii,shortname=mixed,utf8,errors=remount-ro"
        partition_list.append(
            FsEntry(self._boot_partition, "/boot", "vfat", boot_options)
        )

        exec(f"mount {self._root_partition} {mount_point}/kod")
        partition_list.append(
            FsEntry(
                self._root_partition, "/kod", "btrfs", "rw,relatime,ssd,space_cache=v2"
            )
        )

        btrfs_options = "rw,relatime,ssd,space_cache=v2"

        exec(f"mount -o subvol=store/home {self._root_partition} {mount_point}/home")
        partition_list.append(
            FsEntry(
                self._root_partition,
                "/home",
                "btrfs",
                btrfs_options + ",subvol=store/home",
            )
        )

        for dir in subdirs:
            exec(f"mount --bind {mount_point}/kod/store/{dir} {mount_point}/{dir}")
            partition_list.append(
                FsEntry(f"/kod/store/{dir}", f"/{dir}", "none", "rw,bind")
            )

        # Write generation number
        # with open(f"{mount_point}/.generation", "w") as f:
        #     f.write(str(generation))

        print("===================================")

        return partition_list


class FsEntry:
    """Represents a filesystem entry for fstab configuration.

    This class encapsulates filesystem mount information including source device,
    destination mountpoint, filesystem type, mount options, and dump/pass values
    used in fstab entries.

    Attributes:
        source (str): Source device or UUID
        destination (str): Mount point destination path
        fs_type (str): Filesystem type (e.g., 'ext4', 'btrfs', 'vfat')
        options (str): Mount options (e.g., 'defaults', 'rw,bind')
        dump (int): Backup frequency for dump utility (usually 0 or 1)
        pass_ (int): Filesystem check order (0=no check, 1=root, 2=other)
    """

    def __init__(
        self,
        source: str,
        destination: str,
        fs_type: str,
        options: str,
        dump: int = 0,
        pass_: int = 0,
    ) -> None:
        """Initialize a filesystem entry.

        Args:
            source: Source device path or UUID
            destination: Mount point destination
            fs_type: Filesystem type
            options: Mount options string
            dump: Dump backup frequency. Defaults to 0.
            pass_: Filesystem check pass number. Defaults to 0.
        """
        self.source = source
        self.destination = destination
        self.fs_type = fs_type
        self.options = options
        self.dump = dump
        self.pass_ = pass_

    def __str__(self) -> str:
        """Return a formatted string representation of the fstab entry.

        Returns:
            Formatted fstab entry with proper column alignment.
        """
        return (
            f"{self.source:<25} {self.destination:<15} {self.fs_type:<10} "
            f"{self.options:<10} {self.dump:<10} {self.pass_}"
        )

    def mount(self, install_mountpoint: str) -> str:
        if self.fs_type == "btrfs":
            return f"mount -o {self.options} {self.source} {install_mountpoint}{self.destination}"
        if self.fs_type == "none":
            return f"mount --bind {self.source} {install_mountpoint}{self.destination}"
        if self.fs_type == "esp":
            return f"mount -t vfat -o {self.options} {self.source} {install_mountpoint}{self.destination}"
        return f"mount -t {self.fs_type} -o {self.options} {self.source} {install_mountpoint}{self.destination}"

    def source_uuid(self) -> str:
        if self.source[:5] == "/dev/":
            uuid = exec(f"lsblk -o UUID {self.source} | tail -n 1", get_output=True)
            if uuid:
                return f"UUID={uuid.strip()}"
        return self.source


class Boot(NestedDict):
    def install(self, config):
        print("[install] Boot configuration:", self)
        setup_bootloader(self, config.partition_list, config.base)


class Kernel(NestedDict):
    def install(self, _config):
        print("[install] Kernel configuration:", self)


class Loader(NestedDict):
    def install(self, _config):
        print("[install] Loader configuration:", self)
