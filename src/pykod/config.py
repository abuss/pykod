from operator import ne

from pykod.common import set_debug, set_dry_run, set_verbose
from pykod.core import configure_system, create_kod_user, generate_fstab
from pykod.desktop import DesktopEnvironment, DesktopManager
from pykod.devices import Boot, Devices, Disk, Kernel, Loader, Partition
from pykod.fonts import Fonts
from pykod.hardware import HardwareManager
from pykod.locale import Locale
from pykod.network import Network
from pykod.packages import Packages
from pykod.repositories.base import PackageList, Repository


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
        self.partition_list = None

    # import inspect

    # frame = inspect.currentframe().f_back
    # self._sections = [
    #     "System",
    #     "Users",
    #     "User",
    #     "Repositories",
    #     "Network",
    #     # "Disk",
    #     # "Partition",
    #     "Boot",
    #     "Kernel",
    #     "Loader",
    #     "Locale",
    # ]
    # frame.f_globals["NestedDict"] = NestedDict
    # for name in self._sections:
    #     exec(
    #         f"{name} = lambda **kwargs: NestedDict(**kwargs)",
    #         frame.f_globals,
    #         frame.f_locals,
    #     )
    # self.repos = Repositories()
    # self.system = System()
    # Create the functions for the given list
    # create_lambda_functions(["Repo", "System", "Users", "Arch", "AUR", "User"])
    # pass

    # def __enter__(self):
    #     return self

    # def __exit__(self, exc_type, exc_val, exc_tb):
    #     pass

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
        elements = {}
        for _, obj in vars(self).items():
            name = type(obj).__name__
            # if hasattr(type(obj), "install")
            elements[name] = obj
            # name: obj

        # print(f"{elements=}")
        partition_list = []
        if "Devices" in elements:
            devices = elements["Devices"]
            print("Installing device configuration...")
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

            #    - Configures the system with `configure_system()` - sets up basic system configuration
            configure_system(self.mount_point)

        if "Boot" in elements:
            boot = elements["Boot"]
            print("Installing boot configuration...")
            #    - Sets up the bootloader with `setup_bootloader()`
            boot.install(self)

        #    - Creates the KodOS user with `create_kod_user()`
        print("\nCreating KodOS user...")
        create_kod_user(self.mount_point)

        if "Locale" in elements:
            print("Installing locale configuration...")
            locale = elements["Locale"]
            locale.install(self)

        if "Network" in elements:
            network = elements["Network"]
            print("Installing network configuration...")
            network.install(self)

        # ### 5. **Package Management** (lines 117-121)
        #    - Processes repositories with `dist.proc_repos()`
        #    - Gets packages to install from configuration with `get_packages_to_install()`
        #    - Gets pending packages to install with `get_pending_packages()`
        #    - Installs all packages using `manage_packages()` with chroot
        include_pkgs = PackageList()
        exclude_pkgs = PackageList()
        _find_package_lists(self, include_pkgs, exclude_pkgs)
        # print(f"Included packages: {include_pkgs}")
        print("Installing packages from repository")
        for repo, packages in include_pkgs.items():
            print(f"- {repo.__class__.__name__}:\n   {sorted(packages)}")
        print("Excluding packages to install")
        for repo, packages in exclude_pkgs.items():
            print(f"- {repo.__class__.__name__}:\n   {sorted(packages)}")
            # for package in packages:
            # self.base.install_package(package, self.mount_point)

        # print(f"Excluded packages: {exclude_pkgs}")

    # def _list_packages(self):
    #     # for name, obj in vars(self).items():
    #     #     print(name)
    #     include_pkgs = PackageList()
    #     exclude_pkgs = PackageList()
    #     _find_package_lists(self, include_pkgs, exclude_pkgs)
    #     print(f"Included packages: {include_pkgs}")
    #     print(f"Excluded packages: {exclude_pkgs}")


def _find_package_lists(
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
                    res = _find_package_lists(
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
                    res = _find_package_lists(
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
            _find_package_lists(item, include_pkgs, exclude_pkgs, visited, new_path)

    # Search in dictionaries
    if isinstance(obj, dict):
        for key, value in obj.items():
            new_path = f"{path}[{key}]" if path else f"[{key}]"
            _find_package_lists(value, include_pkgs, exclude_pkgs, visited, new_path)
