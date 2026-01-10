import json
import subprocess
from pathlib import Path
from typing import Callable

from pykod.common import execute_command as exec
from pykod.common import execute_chroot as exec_chroot
from pykod.common import (
    open_with_dry_run,
    set_debug,
    set_dry_run,
    set_verbose,
)
from pykod.core import (
    configure_system,
    create_boot_entry,
    create_kod_user,
    generate_fstab,
    save_configuration,
)
from pykod.devices import load_fstab
from pykod.repositories.base import PackageList, Repository
from pykod.service import Service, Services
from pykod.user import User


class Configuration:
    def __init__(
        self,
        base: Repository,
        dry_run: bool = False,
        debug: bool = False,
        verbose: bool = False,
        mount_point: str = "/mnt",
    ):
        self._base = base
        self._dry_run = dry_run
        self._debug = debug
        self._verbose = verbose
        if dry_run:
            mount_point = "mnt"
        self._mount_point = mount_point
        set_dry_run(self._dry_run)
        set_debug(self._debug)
        set_verbose(self._verbose)
        self._partition_list = []
        self._state: str = ""
        self.packages = PackageList()

    # ---- internal helpers (no behavior change) ----

    def get_users(self) -> dict:
        users: dict[str, User] = {}
        for username, user in vars(self).items():
            if isinstance(user, User):
                users[username] = user
        return users

    def _collect_package_sets(self) -> tuple[PackageList, PackageList]:
        include = PackageList()
        exclude = PackageList()
        _find_package_list(self, include, exclude)
        return include, exclude

    def _apply_repo(
        self, packages: PackageList, action: str, mount_point: str | None = None
    ) -> None:
        for repo, items in packages.items():
            if not items:
                continue
            match action:
                case "install":
                    cmd = repo.install_packages(set(items))
                case "remove":
                    cmd = repo.remove_packages(set(items))
                case _:
                    raise ValueError(f"Unknown action: {action}")
            if mount_point is None:
                exec(cmd)
            else:
                exec_chroot(cmd, mount_point=mount_point)

    def _prepare_repos(self, packages: PackageList, mount_point: str) -> None:
        """Run optional repository preparation steps (e.g., AUR helper bootstrap)."""
        for repo, items in packages.items():
            if not items:
                continue
            if hasattr(repo, "prepare"):
                repo.prepare(mount_point)

    # def _apply_repo_install(
    #     self, packages: PackageList, mount_point: str | None = None
    # ) -> None:
    #     for repo, items in packages.items():
    #         if not items:
    #             continue
    #         cmd = repo.install_package(set(items))
    #         if mount_point is None:
    #             exec(cmd)
    #         else:
    #             exec_chroot(cmd, mount_point=mount_point)

    # def _apply_repo_remove(
    #     self, packages: PackageList, mount_point: str | None = None
    # ) -> None:
    #     for repo, items in packages.items():
    #         if not items:
    #             continue
    #         cmd = repo.remove_package(set(items))
    #         if mount_point is None:
    #             exec(cmd)
    #         else:
    #             exec_chroot(cmd, mount_point=mount_point)

    def _collect_and_prepare_services(self) -> Services:
        services = self.services
        if hasattr(self, "desktop"):
            display_mgr = self.desktop.display_manager
            services[display_mgr.service_name] = display_mgr
        print(f"*******> Collected services: {services}")
        return services

    def _get_boot_and_root_partitions(self, devices) -> tuple[str, str]:
        boot_partition = ""
        root_partition = ""
        for disk in devices.values():
            boot_part, root_part = disk.get_partition_info()
            if not boot_partition:
                boot_partition = boot_part
            if not root_partition:
                root_partition = root_part
        return boot_partition, root_partition

    def _store_generation_state(
        self,
        state_path: str,
        generation_path: str,
        kernel: str,
        include_pkgs: PackageList,
        enabled_services: list[str],
    ) -> None:
        print("Storing generation state...")
        print(f"{state_path=}")
        if self._dry_run:
            store_state_tmp(
                generation_path, self, kernel, include_pkgs, enabled_services
            )
        else:
            store_state(generation_path, kernel, include_pkgs, enabled_services)
            store_installed_packages(state_path, generation_path, self)

    # =============================== INSTALL ================================
    def install(self) -> None:
        """Install the configuration."""
        print(f"{self._dry_run=}")
        print(f"{self._debug=}")
        print(f"{self._verbose=}")
        # elements = self._collect_elements()

        # Device installation
        devices = self.devices
        if devices is None:
            raise ValueError("No devices configuration found.")
        print("Installing device configuration...")
        self._partition_list = devices.install(self, self._mount_point)

        list_base_pkgs = self._base.get_base_packages(self)
        print(f"Base packages to install: {list_base_pkgs['base']}")
        base_packages = list_base_pkgs["kernel"] + list_base_pkgs["base"]
        print(f"Base packages to install: {base_packages}")
        self._base.install_base(self._mount_point, base_packages)
        exec_chroot(self._base.update_database(), mount_point=self._mount_point)

        generate_fstab(self, self._partition_list, self._mount_point)
        configure_system(self._mount_point)

        # Boot installation
        print("Installing boot configuration...")
        boot = self.boot
        boot.install(self)

        # User Kod installation
        print("\nCreating KodOS user...")
        create_kod_user(self._mount_point)

        # Locale installation
        print("Installing locale configuration...")
        self.locale.install(self)

        # Network installation
        print("Installing network configuration...")
        self.network.install(self)

        # Repository and Package installation
        include_pkgs, exclude_pkgs = self._collect_package_sets()
        print(f"Included packages: {include_pkgs}")
        print(f"Excluded packages: {exclude_pkgs}")
        print("-+-" * 40)

        # Prepare repositories that require bootstrapping (e.g., AUR helper)
        self._prepare_repos(include_pkgs + exclude_pkgs, self._mount_point)

        # packages_to_install = self._base.packages_to_install(include_pkgs, exclude_pkgs)
        self._apply_repo(include_pkgs, "install", self._mount_point)
        self._apply_repo(exclude_pkgs, "remove", self._mount_point)

        services = self._collect_and_prepare_services()
        services.enable(self, self._mount_point)
        list_enabled_services = services.get_enabled_services()
        print(f"Enabling services: {list_enabled_services}")

        # User installation
        print("--" * 40)
        users = self.get_users()
        print(users)
        # if "User" in elements:
        for user in users.values():
            user.install(self)

        generation_path = Path(f"{self._mount_point}/kod/generations/0")
        generation_path.mkdir(parents=True, exist_ok=True)
        print(f"Creating generation path at {generation_path}, {self._dry_run=}")
        if boot is None:
            raise ValueError("Boot configuration is required to determine kernel")
        kernel = self.boot.kernel.package.to_list()[0]
        # installed_packages_cmd = self.base.list_installed_packages()
        self._store_generation_state(
            self._mount_point,
            generation_path,
            kernel,
            include_pkgs,
            list_enabled_services,
        )
        # Store configuration files
        # -----------------------------------------------------------------
        # Store configuration instance and repositories as JSON
        save_configuration(self, include_pkgs, generation_path)
        # -----------------------------------------------------------------

        print("\nInstalling KodOS files...")
        exec(f"umount -R {self._mount_point}")
        print("Done")
        if devices is not None:
            exec(f"mount {devices.root_partition} {self._mount_point}")
        exec(f"cp -r /root/pykod {self._mount_point}/store/root/")
        exec(f"umount {self._mount_point}")
        print(" Done installing KodOS")

    # =============================== REBUILD ================================
    def rebuild(self, new_generation: bool = True, update: bool = False) -> None:
        print("Rebuilding configuration...")
        self._state = "rebuild"

        # Get next generation number
        if self._dry_run:
            max_generation = 0  # FOR TESTING
        else:
            max_generation = get_max_generation()
        next_generation_id = int(max_generation) + 1
        print(f"Next generation ID: {next_generation_id}")

        if self._dry_run:
            current_generation_id = 0  # FOR TESTING
        else:
            with open_with_dry_run("/.generation") as f:
                current_generation_id = int(f.readline().strip())
            print(f"{current_generation_id = }")

        # Load current installed packages and enabled services
        current_generation_path = Path(f"/kod/generations/{current_generation_id}")
        print(f"Loading current generation from {current_generation_path}")
        if not (current_generation_path / "installed_packages").is_file():
            print("Missing installed packages information")
            return

        remove_next_generation = False
        try:
            if self._dry_run:
                current_packages, current_services = load_packages_services_tmp(
                    f"mnt{current_generation_path}"
                )
            else:
                current_packages, current_services = load_packages_services(
                    current_generation_path
                )
            print(f"{current_packages = }")
            print(f"{current_services = }")

            # Get boot and root partitions from partition list
            devices = self.devices

            boot_partition, root_partition = self._get_boot_and_root_partitions(devices)

            print(f"{boot_partition=}")
            print(f"{root_partition=}")

            # 4. Snapshot and Root Path Preparation (lines 181-200)
            # - Creates directory for the next generation state
            next_generation_path = f"/kod/generations/{next_generation_id}"
            next_current = Path("/kod/current/.next_current")
            # next_current = Path(f"{next_generation_path}/rootfs")
            if self._dry_run:
                next_generation_path = "mnt" + next_generation_path
                next_current = Path("mnt/kod/current/.next_current")
                # next_current = Path(f"{next_generation_path}/rootfs")
            print(
                f"Creating next generation path at {next_generation_path}, {self._dry_run=}"
            )
            print(f"Creating next current path at {next_current}, {self._dry_run=}")
            next_generation_path = Path(next_generation_path)
            next_generation_path.mkdir(parents=True, exist_ok=True)
            next_current.mkdir(parents=True, exist_ok=True)

            # - If --new_generation flag is used:
            #   - Creates a BTRFS subvolume snapshot of the current root
            if new_generation:
                print("Creating a new generation")
                exec(f"btrfs subvolume snapshot / {next_generation_path}/rootfs")

                # use_chroot = True
                new_root_path = create_next_generation(
                    boot_partition, root_partition, next_generation_id, next_current
                )
                print(f"{new_root_path=}")
            # else:
            #     # os._exit(0)
            #     exec("btrfs subvolume snapshot / /kod/current/old-rootfs")
            #     exec(
            #         f"cp /kod/generations/{current_generation_id}/installed_packages /kod/current/installed_packages"
            #     )
            #     exec(
            #         f"cp /kod/generations/{current_generation_id}/enabled_services /kod/current/enabled_services"
            #     )
            #     use_chroot = False
            #     new_root_path = "/"

            # Repository and Package Processing (lines 205-231)
            # - Gets packages to install/remove from configuration
            include_pkgs, exclude_pkgs = self._collect_package_sets()

            if update:
                print("Updating all packages to the latest version")
                for repo, packages in include_pkgs.items():
                    print(f"Updating repository: {repo.__class__.__name__}")
                    cmd_update = repo.update_database()
                    if cmd_update:
                        exec_chroot(
                            cmd_update, mount_point=new_root_path
                        )  # Refresh package database
                    cmd_update_pkgs = repo.update_installed_packages(packages)
                    if cmd_update_pkgs:
                        exec_chroot(
                            cmd_update_pkgs, mount_point=new_root_path
                        )  # Update all packages

            print(f"Included packages: {include_pkgs}")
            print(f"Excluded packages: {exclude_pkgs}")
            print("-+-" * 40)

            # boot = list(elements["Boot"].values())[0]
            # boot = self.boot
            next_kernel_package = self.boot.kernel.package
            next_kernel = next_kernel_package.to_list()[0]
            pkgs_to_install = repo_packages_list(next_kernel, include_pkgs)

            print(f"Packages to install: {pkgs_to_install}")
            print("-+-" * 40)
            print(f"current_packages: {current_packages}")
            new_to_install = PackageList()
            new_to_remove = PackageList()
            for repo, packages in include_pkgs.items():
                repo_name = repo.__class__.__name__
                pkgs_installed_set = set(current_packages.get(repo_name, []))
                pkgs_to_install_set = set(packages)
                new_pkgs = list(pkgs_to_install_set - pkgs_installed_set)
                remove_pkgs = list(pkgs_installed_set - pkgs_to_install_set)
                new_to_install += repo[new_pkgs]
                new_to_remove += repo[remove_pkgs]
                print(f"For repo {repo_name}:")
                print(f"  To install: {new_pkgs}")
                print(f"  To remove: {remove_pkgs}")

            print(f"\n\nNew packages to install: {new_to_install}\n")
            print(f"Packages to remove: {new_to_remove}\n")

            # Prepare repositories for install inside the new root if needed
            if new_generation:
                self._prepare_repos(new_to_install, new_root_path)
                self._apply_repo(new_to_install, "install", new_root_path)
            else:
                self._apply_repo(new_to_install, "install")

            # print(f"Packages to remove: {pkgs_to_remove}")
            #
            # Compares current vs. desired package state to determine:
            hooks_to_run = []
            current_kernel = current_packages["kernel"][0]
            if next_kernel != current_kernel:
                print(f"Kernel update detected: {current_kernel} -> {next_kernel}")
                hooks_to_run += [
                    update_kernel_hook(self, next_kernel, new_root_path),
                    update_initramfs_hook(self, next_kernel, new_root_path),
                ]

            print(f"Hooks to run: {hooks_to_run}")
            print("Running hooks")
            for hook in hooks_to_run:
                print(f"Running {hook}")
                hook()

            # Service Management (lines 233-241)
            services = self._collect_and_prepare_services()
            print(f"Enabling services {new_root_path = }")
            services.enable(self, new_root_path)

            new_enabled_services = services.get_enabled_services()
            print(f"New enabled services: {new_enabled_services}")
            print(f"Current enabled services: {current_services}")
            services_to_disable = set(current_services) - set(new_enabled_services)
            print(f"Services to disable: {services_to_disable}")

            # Disable removed services
            service = Service()
            for svc_name in services_to_disable:
                service.service_name = svc_name
                if new_generation:
                    print(f"Disabling service: {svc_name}")
                    cmd = service.disable_service(svc_name)
                    exec_chroot(cmd, mount_point=new_root_path)

            print("Removing packages")
            if new_generation:
                self._apply_repo(new_to_remove, "remove", new_root_path)
            else:
                self._apply_repo(new_to_remove, "remove")

            # for repo, packages in new_to_remove.items():
            #     if len(packages) == 0:
            #         continue
            #     print(f"Removing from repo {repo}: {packages}")
            #     cmd = repo.remove_package(set(packages))
            #     exec_chroot(cmd, mount_point=new_root_path)

            # Store new generation state
            # generation_path = f"{new_root_path}/kod/generations/{next_generation_id}"
            # generation_path = next_current
            self._store_generation_state(
                new_root_path,
                next_generation_path,
                next_kernel,
                include_pkgs,
                new_enabled_services,
            )

            # Generation Deployment
            print("==== Deploying new generation ====")
            partition_list = load_fstab("/")
            if new_generation:
                kver = self._base.setup_linux(new_root_path, next_kernel_package)
                print("KVER:", kver)
                create_boot_entry(
                    next_generation_id,
                    partition_list,
                    mount_point=new_root_path,
                    kver=kver,
                )
            # else:
            #     # Move current updated rootfs to a new generation
            #     exec(
            #         f"mv /kod/generations/{current_generation}/rootfs /kod/generations/{generation_id}/"
            #     )
            #     # Moving the current rootfs copy to the current generation path
            #     exec(
            #         f"mv /kod/current/old-rootfs /kod/generations/{current_generation}/rootfs"
            #     )
            #     exec(
            #         f"mv /kod/current/installed_packages /kod/generations/{current_generation}/installed_packages"
            #     )
            #     exec(
            #         f"mv /kod/current/enabled_services /kod/generations/{current_generation}/enabled_services"
            #     )
            #     updated_partition_list = change_subvol(
            #         partition_list,
            #         subvol=f"generations/{generation_id}",
            #         mount_points=["/"],
            #     )
            #     generate_fstab(updated_partition_list, new_root_path)
            #     create_boot_entry(
            #         generation_id,
            #         updated_partition_list,
            #         mount_point=new_root_path,
            #         kver=kver,
            #     )

            # Store configuration instance and repositories as JSON
            save_configuration(self, include_pkgs, next_generation_path)

            # Write generation number
            with open_with_dry_run(
                f"{next_generation_path}/rootfs/.generation", "w"
            ) as f:
                f.write(str(next_generation_id))

        except Exception as e:
            print(f"Error during rebuild: {e}")
            remove_next_generation = True
            # return
        finally:
            kod_paths = [
                "/boot",
                "/kod",
                "/home",
                "/root",
                "/var/log",
                "/var/tmp",
                "/var/cache",
                "/var/kod",
                "/dev",
            ]
            if new_generation:
                for m in kod_paths:
                    exec(f"umount {new_root_path}{m}")
                exec(f"umount -R {new_root_path}")
                # exec(f"rm -rf {new_root_path}")

            if remove_next_generation and next_generation_path.is_dir():
                exec(f"btrfs subvolume delete {next_generation_path}/rootfs")
                exec(f"rm -rf {next_generation_path}")

            # else:
            # exec("mount -o remount,ro /usr")

            print(f"Done. Generation {next_generation_id} created")

    def run(self):
        import sys

        if len(sys.argv) != 2 or sys.argv[1] not in ["install", "rebuild"]:
            print("Usage: python script.py [install|rebuild]")
            sys.exit(1)

        command = sys.argv[1]

        print("-" * 100)
        print(f"Running {command} command...")
        print("Configuration attributes:")

        print("\n", "-" * 80)

        if command == "install":
            self.install()
        elif command == "rebuild":
            self.rebuild(new_generation=True, update=True)


def _find_package_list(
    obj, include_pkgs, exclude_pkgs, visited=None, path=""
) -> PackageList | None:
    # print(f"Visiting {path}: {type(obj)}")
    if visited is None:
        visited = set()

    # Avoid infinite recursion
    if id(obj) in visited:
        return None
    visited.add(id(obj))

    # Check if object is instance of PackageList
    if isinstance(obj, PackageList):
        # print(f"Found PackageList at {path}: {obj}")
        return obj

    # Recursively search attributes
    if hasattr(obj, "__dict__"):
        # print(f"{type(obj)} Object has __dict__")
        # print(vars(obj))
        if "_data" in vars(obj):
            # print(f"Found _data attribute in {path}: {vars(obj)['_data']}")
            for attr_name, attr_value in vars(obj)["_data"].items():
                if not attr_name.startswith("_"):
                    # print(f"Checking attribute {attr_name} of {path}")
                    new_path = f"{path}.{attr_name}" if path else attr_name
                    res = _find_package_list(
                        attr_value, include_pkgs, exclude_pkgs, visited, new_path
                    )
                    if res is not None:
                        # print(f"{attr_name} -> {res}")
                        if attr_name == "exclude_packages":
                            exclude_pkgs += res
                        else:
                            include_pkgs += res
        else:
            for attr_name, attr_value in vars(obj).items():
                if not attr_name.startswith("_"):
                    # print(f"Checking attribute {attr_name} of {path}")
                    new_path = f"{path}.{attr_name}" if path else attr_name
                    res = _find_package_list(
                        attr_value, include_pkgs, exclude_pkgs, visited, new_path
                    )
                    if res is not None:
                        # print(f"{path}: {attr_name} -> {res}")
                        if attr_name == "exclude_packages":
                            exclude_pkgs += res
                        else:
                            include_pkgs += res

    # Search in lists/tuples
    if isinstance(obj, (list, tuple)):
        for i, item in enumerate(obj):
            new_path = f"{path}[{i}]" if path else f"[{i}]"
            _find_package_list(item, include_pkgs, exclude_pkgs, visited, new_path)

    # Search in dictionaries
    if isinstance(obj, dict):
        for key, value in obj.items():
            new_path = f"{path}[{key}]" if path else f"[{key}]"
            _find_package_list(value, include_pkgs, exclude_pkgs, visited, new_path)


def repo_packages_list(kernel, packages) -> dict:
    """Store the list of packages that are installed and the list of services that are enabled."""
    list_packages = {"kernel": [kernel]}
    for repo, packages in packages.items():
        list_packages[repo.__class__.__name__] = sorted(packages)
    return list_packages


def store_state(state_path: str, kernel, packages, services) -> None:
    """Store the list of packages that are installed and the list of services that are enabled."""

    list_packages = repo_packages_list(kernel, packages)
    packages_json = json.dumps(list_packages, indent=2)
    with open_with_dry_run(f"{state_path}/installed_packages", "w") as f:
        f.write(packages_json)

    print(f"Storing enabled services to {state_path}/enabled_services")
    # print(f"Services: {services}")
    list_services = services
    with open_with_dry_run(f"{state_path}/enabled_services", "w") as f:
        f.write("\n".join(list_services))


def store_installed_packages(state_path: str, generation_path: str, config) -> None:
    installed_packages_cmd = config._base.list_installed_packages()
    # def store_installed_packages(state_path: str, config, installed_cmd: str) -> None:
    # """Store the list of installed packages and their versions to /mnt/var/kod/installed_packages.lock."""
    installed_packages_version = exec_chroot(
        installed_packages_cmd, mount_point=state_path, get_output=True
    )
    with open_with_dry_run(f"{generation_path}/packages.lock", "w") as f:
        f.write(installed_packages_version)


def get_max_generation() -> int:
    """Retrieve the highest numbered generation directory in /kod/generations."""
    generations_dir = Path("/kod/generations")
    if not generations_dir.exists():
        return 0

    generations = [
        int(p.name)
        for p in generations_dir.iterdir()
        if p.is_dir() and p.name.isdigit()
    ]
    generation = max(generations) if generations else 0
    return generation


def load_packages_services(state_path: Path) -> tuple[dict, list]:
    """Load the list of packages that are installed and the list of services that are enabled."""
    packages = None
    services = None
    with open_with_dry_run(f"{state_path}/installed_packages", "r") as f:
        packages = json.load(f)
    with open_with_dry_run(f"{state_path}/enabled_services", "r") as f:
        services = [pkg.strip() for pkg in f.readlines() if pkg.strip()]
    return (packages, services)


def create_next_generation(
    boot_part: str, root_part: str, generation: int, next_current: Path
) -> str:
    """
    Create the next generation of the KodOS installation.

    Mounts the generation at /.next_current and sets up the subvolumes and
    mounts the partitions as specified in the fstab file.

    Args:
        boot_part (str): The device name of the boot partition
        root_part (str): The device name of the root partition
        generation (int): The generation number to create

    Returns:
        str: The path to the mounted generation
    """
    # next_current = Path("/kod/current/.next_current")
    # Mounting generation
    # if next_current.is_mount():
    #     print("Reboot is required to update generation")
    #     import os
    #     os._exit(0)
    #     exec(f"umount -R {next_current}")
    #     exec(f"rm -rf {next_current}")

    # next_current.mkdir(parents=True, exist_ok=True)

    exec(f"mount -o subvol=generations/{generation}/rootfs {root_part} {next_current}")
    exec(f"mount {boot_part} {next_current}/boot")
    exec(f"mount {root_part} {next_current}/kod")
    exec(f"mount -o subvol=store/home {root_part} {next_current}/home")

    subdirs = ["root", "var/log", "var/tmp", "var/cache", "var/kod"]
    for dir in subdirs:
        exec(f"mount --bind /kod/store/{dir} {next_current}/{dir}")

    # partition_list = load_fstab()
    # change_subvol(
    #     partition_list, subvol=f"generations/{generation}", mount_points=["/"]
    # )
    # generate_fstab(partition_list, str(next_current))

    # Write generation number
    (next_current / ".generation").write_text(str(generation))

    print("===================================")

    return str(next_current)


def update_kernel_hook(
    conf, kernel_package: str, mount_point: str
) -> Callable[[], None]:
    """Create a hook function to update the kernel for a specified package."""

    def hook() -> None:
        print(f"Update kernel ....{kernel_package}")
        kernel_file, kver = conf._base.get_kernel_info(
            mount_point, package=kernel_package
        )
        print(f"{kver=}")
        print(f"cp {kernel_file} /boot/vmlinuz-{kver}")
        exec_chroot(f"cp {kernel_file} /boot/vmlinuz-{kver}", mount_point=mount_point)

    return hook


def update_initramfs_hook(
    conf, kernel_package: str, mount_point: str
) -> Callable[[], None]:
    """Create a hook function to update the initramfs for a specified package."""

    def hook() -> None:
        print(f"Update initramfs ....{kernel_package}")
        kernel_file, kver = conf._base.get_kernel_info(
            mount_point, package=kernel_package
        )
        print(f"{kver=}")
        exec_chroot(
            f"dracut --kver {kver} --hostonly /boot/initramfs-linux-{kver}.img",
            mount_point=mount_point,
        )

    return hook


# Temporary version without dry-run support


def store_state_tmp(state_path: str, config, kernel, packages, services) -> None:
    """Store the list of packages that are installed and the list of services that are enabled."""

    list_packages = repo_packages_list(kernel, packages)
    with open(f"{state_path}/installed_packages", "w") as f:
        json.dump(list_packages, f, indent=2)

    print(f"Storing enabled services to {state_path}/enabled_services")
    # print(f"Services: {services}")
    with open(f"{state_path}/enabled_services", "w") as f:
        f.write("\n".join(services))

    installed_packages_cmd = config._base.list_installed_packages()
    installed_pakages_version = subprocess.run(
        installed_packages_cmd, shell=True, capture_output=True, text=True
    ).stdout
    with open(f"{state_path}/packages.lock", "w") as f:
        f.write(installed_pakages_version)


def load_packages_services_tmp(state_path: Path) -> tuple[dict, list]:
    """Load the list of packages that are installed and the list of services that are enabled."""
    packages = None
    services = None
    with open(f"{state_path}/installed_packages", "r") as f:
        packages = json.load(f)
    with open(f"{state_path}/enabled_services", "r") as f:
        services = [pkg.strip() for pkg in f.readlines() if pkg.strip()]
    return (packages, services)
