import json
from collections import defaultdict

from pykod.common import (
    exec,
    exec_chroot,
    open_with_dry_run,
    set_debug,
    set_dry_run,
    set_verbose,
)
from pykod.core import configure_system, create_kod_user, generate_fstab
from pykod.desktop import DesktopEnvironment, DesktopManager
from pykod.devices import Boot, Devices, Disk, Kernel, Loader, Partition
from pykod.fonts import Fonts

# from pykod._hardware import HardwareManager
from pykod.locale import Locale
from pykod.network import Network
from pykod.packages import Packages
from pykod.repositories.base import PackageList, Repository
from pykod.service import Services


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

    # 1. **Initialization** (lines 78-86)
    #    - Creates a `Context` object with the current user, mount point (`/mnt` by default), and sets `use_chroot=True` and `stage="install"`
    #    - Loads the configuration file
    #    - Determines the base distribution (defaults to "arch" if not specified)
    #    - Sets up the distribution-specific module

    # ### 2. **Partition Creation** (line 105)
    #    - `create_partitions(conf)` - Creates disk partitions based on configuration
    #    - Returns boot partition, root partition, and partition list

    # ### 3. **Filesystem Hierarchy Creation** (line 107)
    #    - `create_filesystem_hierarchy()` - Creates and mounts the filesystem structure at the mount point
    #    - Sets up all necessary mount points

    # ### 4. **Base System Installation** (lines 110-114)
    #    - Gets base packages using `dist.get_base_packages(conf)`
    #    - Installs essential packages with `dist.install_essentials_pkgs()`
    #    - Configures the system with `configure_system()` - sets up basic system configuration
    #    - Sets up the bootloader with `setup_bootloader()`
    #    - Creates the KodOS user with `create_kod_user()`

    # ### 5. **Package Management** (lines 117-121)
    #    - Processes repositories with `dist.proc_repos()`
    #    - Gets packages to install from configuration with `get_packages_to_install()`
    #    - Gets pending packages to install with `get_pending_packages()`
    #    - Installs all packages using `manage_packages()` with chroot

    # ### 6. **Service Management** (lines 124-126)
    #    - Gets system services to enable from configuration
    #    - Enables all services using `enable_services()` with chroot

    # ### 7. **User Processing** (line 130)
    #    - `proc_users(ctx, conf)` - Creates and configures users defined in the configuration

    # ### 8. **Generation Storage** (lines 133-134)
    #    - Stores installed packages and enabled services to generation 0 path (`/kod/generations/0`)
    #    - Generates package lock file using `dist.generale_package_lock()`

    # ### 9. **Cleanup and Finalization** (lines 136)
    #    - Unm-142ounts all filesystems under the mount point
    #    - Remounts the root partition
    #    - Copies the KodOS source to `/store/root/`
    #    - Final unmount
    #    - Prints "Done installing KodOS"

    def install(self) -> None:
        print(f"{self.dry_run=}")
        print(f"{self.debug=}")
        print(f"{self.verbose=}")
        # list all attributes that have an install method and call it
        elements = defaultdict(dict)
        for name, obj in vars(self).items():
            class_name = type(obj).__name__
            # if hasattr(type(obj), "install")
            # elements[name] = obj
            elements[class_name][name] = obj
            # name: obj

        # print(f"{elements=}")
        devices = None
        partition_list = []
        if "Devices" in elements:
            # devices = elements["Devices"]
            print("Installing device configuration...")
            # ### 2. **Partition Creation** (line 105)
            #    - `create_partitions(conf)` - Creates disk partitions based on configuration
            #    - Returns boot partition, root partition, and partition list
            # ### 3. **Filesystem Hierarchy Creation** (line 107)
            #    - `create_filesystem_hierarchy()` - Creates and mounts the filesystem structure at the mount point
            #    - Sets up all necessary mount points
            # mount_point = "/mnt"

            devices = list(elements["Devices"].values())[0]
            if devices is None:
                raise ValueError("No devices configuration found.")

            # for device in disks_obj.values():
            # devices = elements["Devices"].popitem()[1]
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

            #    - Configures the system with `configure_system()` - sets up basic system configuration
            configure_system(self.mount_point)

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

        packages_to_install = self.base.packages_to_install(include_pkgs, exclude_pkgs)
        print(f"Packages to install: {packages_to_install}")
        print("-+-" * 40)
        x = input()

        # print("Installing packages from repository")
        for repo, packages in packages_to_install.items():
            # print(f"- {repo.__class__.__name__}:\n   {sorted(packages)}")
            cmd = repo.install_package(set(packages))
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

        # ### 7. **User Processing** (line 130)
        #    - `proc_users(ctx, conf)` - Creates and configures users defined in the configuration
        print("--" * 40)
        for obj in elements["User"].values():
            obj.install(self)

        # ### 8. **Generation Storage** (lines 133-134)
        #    - Stores installed packages and enabled services to generation 0 path (`/kod/generations/0`)
        #    - Generates package lock file using `dist.generale_package_lock()`
        generation_path = f"{self.mount_point}/kod/generations/0"
        store_packages_services(generation_path, include_pkgs, list_enabled_services)
        installed_packages_cmd = self.base.list_installed_packages()
        store_installed_packages(generation_path, self, installed_packages_cmd)

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


def store_packages_services(state_path: str, packages, services) -> None:
    """Store the list of packages that are installed and the list of services that are enabled."""
    list_packages = {}
    for repo, packages in packages.items():
        list_packages[repo.__class__.__name__] = sorted(packages)
    packages_json = json.dumps(list_packages, indent=2)
    with open_with_dry_run(f"{state_path}/installed_packages", "w") as f:
        f.write(packages_json)

    print(f"Storing enabled services to {state_path}/enabled_services")
    # print(f"Services: {services}")
    list_services = services
    with open_with_dry_run(f"{state_path}/enabled_services", "w") as f:
        f.write("\n".join(list_services))


def store_installed_packages(state_path: str, config, installed_cmd: str) -> None:
    """Store the list of installed packages and their versions to /mnt/var/kod/installed_packages.lock."""
    installed_pakages_version = exec_chroot(
        installed_cmd, mount_point=config.mount_point, get_output=True
    )
    with open_with_dry_run(f"{state_path}/packages.lock", "w") as f:
        f.write(installed_pakages_version)
