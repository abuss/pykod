import json
import subprocess
from asyncio.events import new_event_loop
from collections import defaultdict
from modulefinder import packagePathMap
from pathlib import Path
from typing import Callable

from pykod.common import (
    exec,
    exec_chroot,
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
)
from pykod.devices import load_fstab
from pykod.repositories.base import PackageList, Repository
from pykod.service import Service, Services


class Configuration:
    def __init__(
        self,
        base: Repository,
        dry_run: bool = False,
        debug: bool = False,
        verbose: bool = False,
        mount_point: str = "/mnt",
    ):
        self.packages = PackageList()
        self.base = base
        self.dry_run = dry_run
        self.debug = debug
        self.verbose = verbose
        self.mount_point = mount_point
        set_dry_run(self.dry_run)
        set_debug(self.debug)
        set_verbose(self.verbose)
        self.partition_list = []
        self.state: str = ""

    # =============================== INSTALL ================================
    def install(self) -> None:
        print(f"{self.dry_run=}")
        print(f"{self.debug=}")
        print(f"{self.verbose=}")
        self.state = "install"
        # list all attributes that have an install method and call it
        elements = defaultdict(dict)
        for name, obj in vars(self).items():
            class_name = type(obj).__name__
            elements[class_name][name] = obj

        # DEvice processing
        devices = None
        # partition_list = []
        if device_obj := elements.get("Devices"):
            print("Installing device configuration...")
            devices = list(device_obj.values())[0]
            # devices = elements["Devices"]
            # ### 2. **Partition Creation** (line 105)
            #    - `create_partitions(conf)` - Creates disk partitions based on configuration
            #    - Returns boot partition, root partition, and partition list
            # ### 3. **Filesystem Hierarchy Creation** (line 107)
            #    - `create_filesystem_hierarchy()` - Creates and mounts the filesystem structure at the mount point
            #    - Sets up all necessary mount points
            # mount_point = "/mnt"

            self.partition_list = devices.install(self, self.mount_point)
            # ### 4. **Base System Installation** (lines 110-114)
            #    - Gets base packages using `dist.get_base_packages(conf)`
            list_base_pkgs = self.base.get_base_packages(self)
            print(f"Base packages to install: {list_base_pkgs['base']}")
            base_packages = list_base_pkgs["kernel"] + list_base_pkgs["base"]
            print(f"Base packages to install: {base_packages}")
            #    - Installs essential packages with `dist.install_essentials_pkgs()`
            self.base.install_base(self.mount_point, base_packages)

            # Generate fstab
            generate_fstab(self, self.partition_list, self.mount_point)

            # Configures the system with `configure_system()` - sets up basic system configuration
            configure_system(self.mount_point)
        else:
            raise ValueError("No devices configuration found.")

        if "Boot" in elements:
            boot = list(elements["Boot"].values())[0]
            print("Installing boot configuration...")
            #    - Sets up the bootloader with `setup_bootloader()`
            boot.install(self)

        #    - Creates the KodOS user with `create_kod_user()`
        print("\nCreating KodOS user...")
        create_kod_user(self.mount_point)

        if "Locale" in elements:
            print("Installing locale configuration...")
            locale = list(elements["Locale"].values())[0]
            locale.install(self)

        if "Network" in elements:
            network = list(elements["Network"].values())[0]
            print("Installing network configuration...")
            network.install(self)

        # ### 5. **Package Management** (lines 117-121)
        #    - Processes repositories with `dist.proc_repos()`
        #    - Gets packages to install from configuration with `get_packages_to_install()`
        #    - Gets pending packages to install with `get_pending_packages()`
        #    - Installs all packages using `manage_packages()` with chroot
        include_pkgs = PackageList()
        exclude_pkgs = PackageList()
        _find_package_list(self, include_pkgs, exclude_pkgs)
        print(f"Included packages: {include_pkgs}")
        print(f"Excluded packages: {exclude_pkgs}")
        print("-+-" * 40)

        # packages_to_install = self.base.packages_to_install(include_pkgs, exclude_pkgs)
        packages_to_install = include_pkgs
        print(f"Packages to install: {packages_to_install}")
        print("-+-" * 40)
        x = input()

        # print("Installing packages from repository")
        for repo, packages in packages_to_install.items():
            # print(f"- {repo.__class__.__name__}:\n   {sorted(packages)}")
            cmd = repo.install_package(set(packages))
            # print(f"  Command: {cmd}")
            exec_chroot(cmd, mount_point=self.mount_point)

        # print("Excluding packages")
        pkgs_to_remove = self.packages_to_remove(exclude_pkgs)
        print(f"Packages to remove: {pkgs_to_remove}")
        print("-+-" * 40)
        x = input()
        # for packages in pkgs_to_remove:
        # print(f"- {repo.__class__.__name__}:\n   {sorted(packages)}")
        cmd = self.base.remove_package(pkgs_to_remove)
        # print(f"  Command: {cmd}")
        exec_chroot(cmd, mount_point=self.mount_point)

        # ### 6. **Service Management** (lines 124-126)
        #    - Gets system services to enable from configuration
        #    - Enables all services using `enable_services()` with chroot
        services = Services()
        if "Services" in elements:
            for svc in elements["Services"].values():
                services.update(svc)

        if "DesktopManager" in elements:
            desktop_manager = list(elements["DesktopManager"].values())[0]
            display_manger = desktop_manager.display_manager
            services[display_manger.service_name] = display_manger

        services.enable(self)

        list_enabled_services = services.list_enabled_services()
        print(f"Enabling services: {list_enabled_services}")

        # ### 7. **User Processing** (line 130)store_packages_services
        #    - `proc_users(ctx, conf)` - Creates and configures users defined in the configuration
        print("--" * 40)
        for obj in elements["User"].values():
            obj.install(self)

        # ### 8. **Generation Storage** (lines 133-134)
        #    - Stores installed packages and enabled services to generation 0 path (`/kod/generations/0`)
        #    - Generates package lock file using `dist.generale_package_lock()`
        # generation_path = f"{self.mount_point}/kod/generations/0"
        generation_path = "mnt/kod/generations/0"
        kernel = boot.kernel.package.to_list()[0]
        store_packages_services_tmp(
            generation_path, kernel, include_pkgs, list_enabled_services
        )
        #
        installed_packages_cmd = self.base.list_installed_packages()
        store_installed_packages_tmp(generation_path, self, installed_packages_cmd)

        # TODO: Save current configurtion

        # ### 9. **Cleanup and Finalization** (lines 136)
        #    - Unmounts all filesystems under the mount point
        #    - Remounts the root partition
        #    - Copies the KodOS source to `/store/root/`
        #    - Final unmount
        #    - Prints "Done installing KodOS"

        exec(f"umount -R {self.mount_point}")
        print("Done")
        exec(f"mount {devices.root_partition} {self.mount_point}")
        exec(f"cp -r /root/pykod {self.mount_point}/store/root/")
        exec(f"umount {self.mount_point}")
        print(" Done installing KodOS")

    # =============================== REBUILD ================================
    def rebuild(self, new_generation: bool = True, update: bool = False) -> None:
        print("Rebuilding configuration...")
        self.state = "rebuild"
        # list all attributes that have an install method and call it
        elements = defaultdict(dict)
        for name, obj in vars(self).items():
            class_name = type(obj).__name__
            # if hasattr(type(obj), "rebuild"):
            elements[class_name][name] = obj
            # name: obj
        print(f"==== Elements =====\n{elements.keys()=}")
        # ['Locale', 'Network', 'DesktopManager', 'Fonts', 'User', 'Services']

        # Get next generation number
        # max_generation = get_max_generation()
        max_generation = 0  # FOR TESTING
        next_generation_id = int(max_generation) + 1
        print(f"Next generation ID: {next_generation_id}")

        with open_with_dry_run("/.generation") as f:
            current_generation_id = int(f.readline().strip())
        current_generation_id = 0  # FOR TESTING
        print(f"{current_generation_id = }")

        # 3. Current State Loading (lines 171-179)
        # - Loads current installed packages and enabled services from /kod/generations/{current_generation}/
        # - Validates that the current generation state files exist

        # Load current installed packages and enabled services
        current_generation_path = Path(f"mnt/kod/generations/{current_generation_id}")
        print(f"Loading current generation from {current_generation_path}")
        if not (current_generation_path / "installed_packages").is_file():
            print("Missing installed packages information")
            return

        current_packages, current_services = load_packages_services_tmp(
            current_generation_path
        )
        print(f"{current_packages = }")
        print(f"{current_services = }")

        # Get boot and root partitions from partition list
        devices = None
        boot_partition = ""
        root_partition = ""
        if "Devices" in elements:
            devices = list(elements["Devices"].values())[0]
            if devices is None:
                raise ValueError("No devices configuration found.")
            for disk in devices.values():
                boot_part, root_part = disk.info_partitions()
                if boot_partition == "":
                    boot_partition = boot_part
                if root_partition == "":
                    root_partition = root_part

        print(f"{boot_partition=}")
        print(f"{root_partition=}")

        # 4. Snapshot and Root Path Preparation (lines 181-200)
        # - Creates directory for the next generation state
        next_generation_path = Path(
            f"mnt/kod/generations/{next_generation_id}"
        )  # FOR TESTING
        next_generation_path.mkdir(parents=True, exist_ok=True)

        # - If --new_generation flag is used:
        #   - Creates a BTRFS subvolume snapshot of the current root
        if new_generation:
            print("Creating a new generation")
            exec(f"btrfs subvolume snapshot / {next_generation_path}/rootfs")
            # use_chroot = True
            new_root_path = create_next_generation(
                boot_partition, root_partition, next_generation_id
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

        if update:
            print("Updating all packages to the latest version")
            cmd_update_db = self.base.update_database()
            exec_chroot(
                cmd_update_db, mount_point=new_root_path
            )  # Refresh package database
            cmd_update_pkgs = self.base.update_installed_packages()
            exec_chroot(
                cmd_update_pkgs, mount_point=new_root_path
            )  # Update all packages

        #   - Sets up chroot environment for the new generation
        # - If not creating new generation:
        #   - Creates a snapshot of current root as backup (/kod/current/old-rootfs)
        #   - Copies current state files to /kod/current/
        #   - Uses the current root filesystem directly

        # 5. Repository and Package Processing (lines 205-231)
        # - Loads current repositories
        # - Processes repositories from configuration
        # - If --update flag is used:
        #   - Refreshes package database
        #   - Updates all packages
        # - Gets packages to install/remove from configuration
        include_pkgs = PackageList()
        exclude_pkgs = PackageList()
        _find_package_list(self, include_pkgs, exclude_pkgs)
        print(f"Included packages: {include_pkgs}")
        print(f"Excluded packages: {exclude_pkgs}")
        print("-+-" * 40)

        boot = list(elements["Boot"].values())[0]
        next_kernel_package = boot.kernel.package
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

        # print("Installing packages from repository")
        for repo, packages in new_to_install.items():
            # print(f"- {repo.__class__.__name__}:\n   {sorted(packages)}")
            cmd = repo.install_package(set(packages))
            # print(f"  Command: {cmd}")
            exec_chroot(cmd, mount_point=new_root_path)

        # print(f"Packages to remove: {pkgs_to_remove}")
        #
        # - Compares current vs. desired package state to determine:
        #   - New packages to install
        #   - Packages to remove
        #   - Packages to update
        #   - Hooks to run
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

        #
        #
        # 6. Service Management (lines 233-241)
        # - Gets services to enable from configuration
        # - Calculates service differences:
        #   - Services to disable (in current but not in desired)
        #   - New services to enable (in desired but not in current)
        # - Disables obsolete services if not creating new generation
        services = Services()
        if "Services" in elements:
            for svc in elements["Services"].values():
                services.update(svc)

        if "DesktopManager" in elements:
            desktop_manager = list(elements["DesktopManager"].values())[0]
            display_manger = desktop_manager.display_manager
            services[display_manger.service_name] = display_manger

        services.enable(self)

        new_enabled_services = services.list_enabled_services()
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

        # print("Removing packages")
        for repo, packages in new_to_remove.items():
            # print(f"- {repo.__class__.__name__}:\n   {sorted(packages)}")
            cmd = repo.remove_package(set(packages))
            # print(f"  Command: {cmd}")
            exec_chroot(cmd, mount_point=new_root_path)

        #
        # 7. Package Operations (lines 246-262)
        # - Package Removal: Removes packages that are no longer needed
        # - Package Installation: Installs new packages
        # - Hook Execution: Runs any post-installation hooks
        #
        # 8. Service Enablement (lines 264-266)
        # - Enables new system services
        #
        # 9. State Storage (lines 279-288)
        # - Stores the list of installed packages and enabled services for the new generation
        # - Generates package lock file
        # - Gets kernel information for boot entry creation

        # ### 8. **Generation Storage** (lines 133-134)
        #    - Stores installed packages and enabled services to generation 0 path (`/kod/generations/0`)
        #    - Generates package lock file using `dist.generale_package_lock()`

        # generation_path = f"{new_root_path}/kod/generations/{next_generation_id}"
        generation_path = f"mnt/kod/generations/{next_generation_id}"
        # kernel = boot.kernel.package.to_list()[0]
        store_packages_services_tmp(
            generation_path, next_kernel, include_pkgs, new_enabled_services
        )
        #
        installed_packages_cmd = self.base.list_installed_packages()
        store_installed_packages_tmp(generation_path, self, installed_packages_cmd)

        #
        # 10. Generation Deployment (lines 290-310)
        # - If new generation:
        #   - Creates new boot entry with the kernel version

        print("==== Deploying new generation ====")
        partition_list = load_fstab("/")
        if new_generation:
            kver = self.base.setup_linux(new_root_path, next_kernel_package)
            print("KVER:", kver)
            print(f"{self.partition_list=}")
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

        # Write generation number
        with open_with_dry_run(f"{next_generation_path}/rootfs/.generation", "w") as f:
            f.write(str(next_generation_id))

        kod_paths = [
            "/boot",
            "/kod",
            "/home",
            "/root",
            "/var/log",
            "/var/tmp",
            "/var/cache",
            "/var/kod",
        ]
        if new_generation:
            for m in kod_paths:
                exec(f"umount {new_root_path}{m}")
            exec(f"umount {new_root_path}")
            exec(f"rm -rf {new_root_path}")

        # else:
        # exec("mount -o remount,ro /usr")

        print(f"Done. Generation {next_generation_id} created")

        # - If in-place update:
        #   - Reorganizes filesystem structure to create generation hierarchy
        #   - Updates filesystem table (fstab) with new subvolume path
        #   - Creates boot entry for the updated generation
        # - Writes the generation number to the new generation's .generation file
        #
        # 11. Cleanup (lines 312-330)
        # - If new generation: Unmounts all mount points and removes temporary directories
        # - Prints completion message with the new generation ID
        #
        # Key Features:
        # - Atomic updates: Can create snapshots before changes
        # - Rollback capability: Maintains generation history
        # - Package management: Handles installation, removal, and updates
        # - Service management: Manages systemd services
        # - BTRFS integration: Uses subvolumes for generation management
        # - Boot loader integration: Updates boot entries for new generations
        # The rebuild process is designed to be safe and reversible, allowing the system to be
        # updated while maintaining the ability to rollback to previous generations if needed.

    def packages_to_remove(self, exclude_pkgs):
        installed_packages_cmd = self.base.list_installed_packages()
        print(f"*** {installed_packages_cmd=}")
        installed_pakages_version = []
        if self.state == "install":
            installed_pakages_version = exec_chroot(
                installed_packages_cmd, mount_point=self.mount_point, get_output=True
            )
            # installed_pakages_version = subprocess.run(
            #     installed_packages_cmd, shell=True, capture_output=True, text=True
            # ).stdout
        # else:
        # installed_pakages_version = exec(installed_packages_cmd, get_output=True)
        print(f"{installed_pakages_version=}")
        installed_pakages = set(
            [line.split(" ")[0] for line in installed_pakages_version.splitlines()]
        )
        print(f"{installed_pakages=}")
        pkgs_to_remove = installed_pakages & set(exclude_pkgs.to_list())
        print(f"{pkgs_to_remove=}")
        return pkgs_to_remove


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


def store_packages_services(state_path: str, kernel, packages, services) -> None:
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


def store_packages_services_tmp(state_path: str, kernel, packages, services) -> None:
    """Store the list of packages that are installed and the list of services that are enabled."""
    list_packages = repo_packages_list(kernel, packages)
    packages_json = json.dumps(list_packages, indent=2)
    with open(f"{state_path}/installed_packages", "w") as f:
        f.write(packages_json)

    print(f"Storing enabled services to {state_path}/enabled_services")
    # print(f"Services: {services}")
    list_services = services
    with open(f"{state_path}/enabled_services", "w") as f:
        f.write("\n".join(list_services))


def store_installed_packages(state_path: str, config, installed_cmd: str) -> None:
    """Store the list of installed packages and their versions to /mnt/var/kod/installed_packages.lock."""
    installed_pakages_version = exec_chroot(
        installed_cmd, mount_point=config.mount_point, get_output=True
    )
    with open_with_dry_run(f"{state_path}/packages.lock", "w") as f:
        f.write(installed_pakages_version)


def store_installed_packages_tmp(state_path: str, config, installed_cmd: str) -> None:
    """Store the list of installed packages and their versions to /mnt/var/kod/installed_packages.lock."""
    # installed_pakages_version = exec_chroot(
    #     installed_cmd, mount_point=config.mount_point, get_output=True
    # )
    installed_pakages_version = subprocess.run(
        installed_cmd, shell=True, capture_output=True, text=True
    ).stdout
    with open(f"{state_path}/packages.lock", "w") as f:
        f.write(installed_pakages_version)


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


def load_packages_services_tmp(state_path: Path) -> tuple[dict, list]:
    """Load the list of packages that are installed and the list of services that are enabled."""
    packages = None
    services = None
    with open(f"{state_path}/installed_packages", "r") as f:
        packages = json.load(f)
    with open(f"{state_path}/enabled_services", "r") as f:
        services = [pkg.strip() for pkg in f.readlines() if pkg.strip()]
    return (packages, services)


def create_next_generation(boot_part: str, root_part: str, generation: int) -> str:
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
    next_current = Path("mnt/kod/current/.next_current")
    # Mounting generation
    # if next_current.is_mount():
    #     print("Reboot is required to update generation")
    #     import os
    #     os._exit(0)
    #     exec(f"umount -R {next_current}")
    #     exec(f"rm -rf {next_current}")

    next_current.mkdir(parents=True, exist_ok=True)

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
        kernel_file, kver = conf.base.get_kernel_file(
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
        kernel_file, kver = conf.base.get_kernel_file(
            mount_point, package=kernel_package
        )
        print(f"{kver=}")
        exec_chroot(
            f"dracut --kver {kver} --hostonly /boot/initramfs-linux-{kver}.img",
            mount_point=mount_point,
        )

    return hook
