import json
import logging
import subprocess
from pathlib import Path
from typing import Callable

from chorut import ChrootManager

from pykod.common import execute_chroot as exec_chroot
from pykod.common import (
    execute_command,
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

# Module-level logger for configuration operations
logger = logging.getLogger("pykod.config")


class Configuration:
    def __init__(
        self,
        base: Repository,
        dry_run: bool = False,
        debug: bool = False,
        verbose: bool = False,
        mount_point: str = "/mnt",
        interactive: bool = False,
    ):
        self._base = base
        self._dry_run = dry_run
        self._debug = debug
        self._verbose = verbose
        self._interactive = interactive
        if dry_run:
            mount_point = "mnt"
        self._mount_point = mount_point
        set_dry_run(self._dry_run)
        set_debug(self._debug)
        set_verbose(self._verbose)
        self._partition_list = []
        self._state: str = ""
        self.packages = PackageList()
        self._logger_configured = False

    # ---- internal helpers (no behavior change) ----

    def _pause_if_interactive(self, step_name: str) -> None:
        """Pause for user review if interactive mode is enabled.

        Args:
            step_name: Name of the step that was just completed
        """
        if self._interactive:
            logger.info("=" * 80)
            logger.info(f"Step completed: {step_name}")
            logger.info("=" * 80)
            print(f"\n{'=' * 80}")
            print(f"STEP COMPLETED: {step_name}")
            print(f"{'=' * 80}")
            print(f"Press ENTER to continue to the next step, or Ctrl+C to abort...")
            try:
                input()
            except KeyboardInterrupt:
                logger.warning("Installation aborted by user")
                print("\n\nInstallation aborted by user.")
                raise SystemExit(1)
            logger.info(f"Resuming installation after '{step_name}'")

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
                execute_command(cmd)
            else:
                exec_chroot(cmd, mount_point=mount_point)

    def _prepare_repos(self, packages: PackageList, mount_point: str) -> None:
        """Run optional repository preparation steps (e.g., AUR helper bootstrap)."""
        for repo, items in packages.items():
            if not items:
                continue
            if hasattr(repo, "prepare"):
                repo.prepare(mount_point)

    def _collect_and_prepare_services(self) -> Services:
        services = self.services
        if hasattr(self, "desktop"):
            display_mgr = self.desktop.display_manager
            services[display_mgr.service_name] = display_mgr
        logger.debug(f"Collected services: {services}")
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
        logger.debug("Storing generation state...")
        logger.debug(f"State path: {state_path}")
        if self._dry_run:
            store_state_tmp(
                generation_path, self, kernel, include_pkgs, enabled_services
            )
        else:
            store_state(generation_path, kernel, include_pkgs, enabled_services)
            store_installed_packages(state_path, generation_path, self)

    def _setup_logging(self, generation_path: Path, operation: str = "install") -> None:
        """Setup logging for install/rebuild operations.

        Args:
            generation_path: Path where generation-specific logs will be stored
            operation: Type of operation ("install" or "rebuild")
        """
        if not self._logger_configured:
            from pykod.common import setup_install_logging

            try:
                setup_install_logging(
                    generation_path=generation_path,
                    log_name=operation,
                    level=logging.DEBUG,
                )
                self._logger_configured = True
            except Exception as e:
                # Fallback to basic logging if setup fails
                print(f"[WARNING] Failed to configure logging: {e}")
                logging.basicConfig(level=logging.INFO)
                self._logger_configured = True

    # =============================== INSTALL ================================
    def install(self) -> None:
        """Install the configuration."""

        # Setup logging early
        generation_path = Path(f"{self._mount_point}/kod/generations/0")
        generation_path.mkdir(parents=True, exist_ok=True)
        self._setup_logging(generation_path, operation="install")

        logger.info("=" * 80)
        logger.info("Starting KodOS Installation")
        logger.info("=" * 80)
        logger.debug(
            f"Configuration: dry_run={self._dry_run}, debug={self._debug}, verbose={self._verbose}, mount_point={self._mount_point}"
        )

        # Progress tracking
        total_steps = 10
        current_step = 0

        # Step 1: Device installation
        current_step += 1
        logger.info(
            f"[{current_step}/{total_steps}] Installing device configuration..."
        )
        devices = self.devices if hasattr(self, "devices") else None
        if devices is None:
            logger.error("No devices configuration found")
            raise ValueError("No devices configuration found.")
        self._partition_list = devices.install(self, self._mount_point)
        logger.debug(f"Partition list: {self._partition_list}")
        self._pause_if_interactive(
            "Device installation (partitioning, formatting, mounting)"
        )

        # Step 2: Base packages
        current_step += 1
        logger.info(
            f"[{current_step}/{total_steps}] Installing base system packages..."
        )
        list_base_pkgs = self._base.get_base_packages(self)
        base_packages = list_base_pkgs["kernel"] + list_base_pkgs["base"]
        logger.debug(f"Kernel packages: {list_base_pkgs['kernel']}")
        logger.debug(f"Base packages: {list_base_pkgs['base']}")
        logger.info(f"Installing {len(base_packages.to_list())} base packages")
        self._base.install_base(self._mount_point, base_packages)
        exec_chroot(self._base.update_database(), mount_point=self._mount_point)
        self._pause_if_interactive(
            "Base system packages installation (debootstrap, kernel, essential tools)"
        )

        # Step 3: System configuration
        current_step += 1
        logger.info(
            f"[{current_step}/{total_steps}] Configuring system (fstab, hostname, etc.)..."
        )
        generate_fstab(self, self._partition_list, self._mount_point)
        configure_system(self._mount_point)
        self._pause_if_interactive("System configuration (fstab, hostname, timezone)")

        # Step 4: Boot configuration
        current_step += 1
        logger.info(f"[{current_step}/{total_steps}] Installing boot configuration...")
        boot = self.boot
        boot.install(self)
        self._pause_if_interactive(
            "Boot configuration (systemd-boot, initramfs, boot entries)"
        )

        # Step 5: KodOS user
        current_step += 1
        logger.info(f"[{current_step}/{total_steps}] Creating KodOS user...")
        create_kod_user(self._mount_point)
        self._pause_if_interactive("KodOS user creation")

        # Step 6: Locale configuration
        current_step += 1
        logger.info(
            f"[{current_step}/{total_steps}] Installing locale configuration..."
        )
        self.locale.install(self)
        self._pause_if_interactive("Locale configuration")

        # Step 7: Network configuration
        current_step += 1
        logger.info(
            f"[{current_step}/{total_steps}] Installing network configuration..."
        )
        self.network.install(self)
        self._pause_if_interactive("Network configuration")

        # Step 8: Repository and package installation
        current_step += 1
        logger.info(f"[{current_step}/{total_steps}] Installing packages...")
        include_pkgs, exclude_pkgs = self._collect_package_sets()

        # Validate packages
        if invalid_pkgs := self._check_packages(include_pkgs):
            logger.error(f"Invalid packages found: {invalid_pkgs}")
            raise ValueError("Package validation failed.")

        logger.debug(f"Included packages: {include_pkgs}")
        logger.debug(f"Excluded packages: {exclude_pkgs}")
        logger.info(
            f"Installing {len(include_pkgs)} packages, excluding {len(exclude_pkgs)} packages"
        )

        # Prepare repositories that require bootstrapping (e.g., AUR helper)
        self._prepare_repos(include_pkgs + exclude_pkgs, self._mount_point)

        # Install/remove packages
        self._apply_repo(include_pkgs, "install", self._mount_point)
        self._apply_repo(exclude_pkgs, "remove", self._mount_point)
        self._pause_if_interactive(
            "Package installation (user packages, desktop environment, etc.)"
        )

        # Step 9: Services
        current_step += 1
        logger.info(f"[{current_step}/{total_steps}] Enabling system services...")
        services = self._collect_and_prepare_services()
        services.enable(self, self._mount_point)
        list_enabled_services = services.get_enabled_services()
        logger.info(f"Enabled {len(list_enabled_services)} services")
        logger.debug(f"Enabled services: {list_enabled_services}")
        self._pause_if_interactive("Services enabled")

        # Step 10: User installation
        current_step += 1
        logger.info(f"[{current_step}/{total_steps}] Installing user configurations...")
        users = self.get_users()
        logger.debug(f"Users to configure: {list(users.keys())}")
        for username, user in users.items():
            logger.info(f"Configuring user: {username}")
            user.install(self)
        self._pause_if_interactive(
            "User configurations (user creation, shell, dotfiles)"
        )

        # Store generation state
        logger.info("Storing generation state...")
        if boot is None:
            logger.error("Boot configuration is required to determine kernel")
            raise ValueError("Boot configuration is required to determine kernel")
        kernel = self.boot.kernel.package.to_list()[0]
        logger.debug(f"Kernel package: {kernel}")

        self._store_generation_state(
            self._mount_point,
            generation_path,
            kernel,
            include_pkgs,
            list_enabled_services,
        )

        # Store configuration files
        logger.info("Saving configuration metadata...")
        save_configuration(self, include_pkgs, generation_path)

        # Final installation steps
        logger.info("Installing KodOS system files...")
        execute_command(f"umount -R {self._mount_point}")
        if devices is not None:
            execute_command(f"mount {devices.root_partition} {self._mount_point}")
        execute_command(f"cp -r /root/pykod {self._mount_point}/store/root/")
        execute_command(f"umount {self._mount_point}")

        logger.info("=" * 80)
        logger.info("KodOS Installation Completed Successfully")
        logger.info("=" * 80)

        # Final pause for review
        if self._interactive:
            print(f"\n{'=' * 80}")
            print("INSTALLATION COMPLETED SUCCESSFULLY!")
            print(f"{'=' * 80}")
            print("You can now reboot into your new system.")
            print("Press ENTER to finish...")
            try:
                input()
            except KeyboardInterrupt:
                pass

    # =============================== REBUILD ================================
    def rebuild(
        self, live_switch: bool = False, upgrade: bool = False, reboot: bool = False
    ) -> None:
        """Rebuild the configuration."""

        self._state = "rebuild"

        # Get next generation number
        if self._dry_run:
            max_generation = 0  # FOR TESTING
        else:
            max_generation = get_max_generation()
        next_generation_id = int(max_generation) + 1

        current_generation_id = self._get_current_generation()

        current_generation_path = Path(f"/kod/generations/{current_generation_id}")
        next_generation_path = Path(f"/kod/generations/{next_generation_id}")
        next_current_moun_point = Path("/kod/current/.next_current")

        if self._dry_run:
            dry_run_path = Path("mnt")
            current_generation_path = Path(f"{dry_run_path}{current_generation_path}")
            next_generation_path = Path(f"{dry_run_path}{next_generation_path}")
            next_current_moun_point = Path(f"{dry_run_path}{next_current_moun_point}")

        # Create directories and setup logging
        next_generation_path.mkdir(parents=True, exist_ok=True)
        self._setup_logging(next_generation_path, operation="rebuild")

        logger.info("=" * 80)
        logger.info(f"Starting KodOS Rebuild - Generation {next_generation_id}")
        logger.info("=" * 80)
        logger.debug(f"Current generation: {current_generation_id}")
        logger.debug(f"Next generation: {next_generation_id}")
        logger.debug(
            f"Options: live_switch={live_switch}, upgrade={upgrade}, reboot={reboot}"
        )
        logger.debug(f"Current generation path: {current_generation_path}")
        logger.debug(f"Next generation path: {next_generation_path}")
        logger.debug(f"Next current mount point: {next_current_moun_point}")

        # Progress tracking
        total_steps = 8
        current_step = 0

        # Step 1: Validate and prepare
        current_step += 1
        logger.info(f"[{current_step}/{total_steps}] Validating system state...")

        # Get boot and root partitions from partition list
        devices = self.devices
        boot_partition, root_partition = self._get_boot_and_root_partitions(devices)
        logger.debug(f"Boot partition: {boot_partition}")
        logger.debug(f"Root partition: {root_partition}")

        # Load current installed packages and enabled services
        if not (current_generation_path / "installed_packages").is_file():
            logger.warning("Missing installed packages information")
            return

        # Step 2: Create new generation snapshot
        current_step += 1
        logger.info(f"[{current_step}/{total_steps}] Creating generation snapshot...")
        next_current_moun_point.mkdir(parents=True, exist_ok=True)

        if live_switch:
            logger.info("Live switch mode: Moving current rootfs to new generation")
            execute_command(
                f"mv {current_generation_path}/rootfs {next_generation_path}"
            )
            execute_command(
                f"btrfs subvolume snapshot / {current_generation_path}/rootfs"
            )
        else:
            logger.info("Creating new BTRFS subvolume snapshot")
            execute_command(f"btrfs subvolume snapshot / {next_generation_path}/rootfs")

        new_root_path = create_next_generation(
            boot_partition,
            root_partition,
            next_generation_id,
            next_current_moun_point,
        )
        logger.debug(f"New root path: {new_root_path}")

        requires_reboot = reboot
        remove_next_generation = False
        try:
            # Step 3: Load current state
            current_step += 1
            logger.info(
                f"[{current_step}/{total_steps}] Loading current generation state..."
            )
            current_packages, current_services = load_packages_services(
                current_generation_path
            )
            logger.debug(f"Current packages: {current_packages}")
            logger.debug(f"Current services: {current_services}")
            if current_packages is None or current_services is None:
                logger.error("Failed to load current generation state")
                raise Exception("Failed to load current generation state")

            # Step 4: Calculate package changes
            current_step += 1
            logger.info(
                f"[{current_step}/{total_steps}] Calculating package changes..."
            )
            include_pkgs, exclude_pkgs = self._collect_package_sets()

            logger.debug(f"Included packages: {include_pkgs}")
            logger.debug(f"Excluded packages: {exclude_pkgs}")

            if upgrade:
                logger.info("Upgrading all packages to latest version")
                for repo, packages in include_pkgs.items():
                    repo_name = repo.__class__.__name__
                    logger.info(f"Updating repository: {repo_name}")
                    cmd_update = repo.update_database()
                    if cmd_update:
                        exec_chroot(cmd_update, mount_point=new_root_path)
                    cmd_update_pkgs = repo.update_installed_packages(packages)
                    if cmd_update_pkgs:
                        exec_chroot(cmd_update_pkgs, mount_point=new_root_path)

            # Determine packages to install and remove
            next_kernel_package = self.boot.kernel.package
            next_kernel = next_kernel_package.to_list()[0]
            pkgs_to_install = repo_packages_list(next_kernel, include_pkgs)

            logger.debug(f"Target packages: {pkgs_to_install}")
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
                if new_pkgs:
                    logger.debug(f"Repo {repo_name} - To install: {new_pkgs}")
                if remove_pkgs:
                    logger.debug(f"Repo {repo_name} - To remove: {remove_pkgs}")

            logger.info(f"Packages to install: {len(new_to_install)}")
            logger.info(f"Packages to remove: {len(new_to_remove)}")
            logger.debug(f"New packages to install: {new_to_install}")
            logger.debug(f"Packages to remove: {new_to_remove}")

            # Step 5: Install new packages
            current_step += 1
            logger.info(f"[{current_step}/{total_steps}] Installing new packages...")
            self._prepare_repos(new_to_install, new_root_path)
            self._apply_repo(new_to_install, "install", new_root_path)

            # Check for kernel updates
            hooks_to_run = []
            current_kernel = current_packages["kernel"][0]
            if next_kernel != current_kernel:
                logger.warning(
                    f"Kernel update detected: {current_kernel} -> {next_kernel}"
                )
                logger.warning("System reboot will be required")
                requires_reboot = True
                hooks_to_run += [
                    update_kernel_hook(self, next_kernel, new_root_path),
                    update_initramfs_hook(self, next_kernel, new_root_path),
                ]

            if hooks_to_run:
                logger.info(f"Running {len(hooks_to_run)} post-installation hooks")
                for hook in hooks_to_run:
                    logger.debug(f"Running hook: {hook}")
                    hook()

            # Step 6: Service management
            current_step += 1
            logger.info(f"[{current_step}/{total_steps}] Managing system services...")
            services = self._collect_and_prepare_services()
            logger.debug(f"Enabling services at: {new_root_path}")
            services.enable(self, new_root_path)

            new_enabled_services = services.get_enabled_services()
            logger.debug(f"New enabled services: {new_enabled_services}")
            logger.debug(f"Current enabled services: {current_services}")
            services_to_disable = set(current_services) - set(new_enabled_services)

            if services_to_disable:
                logger.info(f"Disabling {len(services_to_disable)} services")
                logger.debug(f"Services to disable: {services_to_disable}")

            # Disable removed services
            service = Service()
            for svc_name in services_to_disable:
                service.service_name = svc_name
                logger.debug(f"Disabling service: {svc_name}")
                cmd = service.disable_service(svc_name, is_live=live_switch)
                exec_chroot(cmd, mount_point=new_root_path)

            # Step 7: Remove old packages
            current_step += 1
            logger.info(f"[{current_step}/{total_steps}] Removing obsolete packages...")
            self._apply_repo(new_to_remove, "remove", new_root_path)

            # Store new generation state
            logger.info("Storing generation state...")
            self._store_generation_state(
                new_root_path,
                next_generation_path,
                next_kernel,
                include_pkgs,
                new_enabled_services,
            )

            # Step 8: Deploy new generation
            current_step += 1
            logger.info(f"[{current_step}/{total_steps}] Deploying new generation...")
            partition_list = load_fstab("/")
            kver = self._base.setup_linux(new_root_path, next_kernel_package)
            logger.debug(f"Kernel version: {kver}")
            create_boot_entry(
                next_generation_id,
                partition_list,
                mount_point=new_root_path,
                kver=kver,
            )

            # Store configuration instance and repositories as JSON
            logger.info("Saving configuration metadata...")
            save_configuration(self, include_pkgs, next_generation_path)

            # Write generation number
            with open_with_dry_run(
                f"{next_generation_path}/rootfs/.generation", "w"
            ) as f:
                f.write(str(next_generation_id))

        except Exception as e:
            logger.error(f"Error during rebuild: {e}")
            remove_next_generation = True
            raise
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
            ]
            if not live_switch:
                logger.debug("Unmounting generation paths")
                for m in kod_paths:
                    execute_command(f"umount {new_root_path}{m}")

            if (
                not live_switch
                and remove_next_generation
                and next_generation_path.is_dir()
            ):
                logger.warning(f"Cleaning up failed generation {next_generation_id}")
                execute_command(f"btrfs subvolume delete {next_generation_path}/rootfs")
                execute_command(f"rm -rf {next_generation_path}")
            else:
                logger.info(f"Generation {next_generation_id} created successfully")

        if requires_reboot:
            logger.warning("=" * 80)
            logger.warning("REBOOT REQUIRED to switch to the new generation")
            logger.warning("=" * 80)

        if reboot:
            from time import sleep

            logger.info("Automatic reboot requested, rebooting in 5 seconds...")
            sleep(5)
            execute_command("reboot")

    def rebuild_user(self, username: str) -> None:
        """Rebuild the specified user configuration."""
        logger.info(f"Rebuilding user configuration for {username}...")
        user = _find_user(self, username)
        logger.debug(f"Found user: {user} {type(user)}")
        if user is None:
            logger.warning(f"User {username} not found in configuration.")
            return
        logger.info(f"User {username} configuration rebuilt.")
        user.rebuild()

    def _get_current_generation(self) -> int:
        """Retrieve the current generation number from /.generation."""
        if self._dry_run:
            return 0
        with open_with_dry_run("/.generation") as f:
            current_generation = int(f.readline().strip())
        return current_generation

    def _check_packages(self, packages: PackageList) -> list:
        invalid_packages = []
        for repo, items in packages.items():
            cmds = repo.is_valid_packages(items)
            logger.debug(f"Validation command for repo {repo}: {cmds}")
            if cmds is None:
                continue
            for pkg, cmd in zip(items, cmds):
                if self._dry_run:
                    result = subprocess.run(
                        cmd, shell=True, capture_output=True, text=True
                    )
                    results = result.stdout.splitlines()
                else:
                    results = exec_chroot(
                        cmd, mount_point=self._mount_point, get_output=True
                    ).splitlines()
                    logger.debug(f"{cmd} result: {results}")
                if not results:
                    invalid_packages.append(pkg)

        if invalid_packages:
            logger.warning(f"Invalid packages found: {invalid_packages}")
        return invalid_packages


def _find_user(obj, username: str) -> User | None:
    # For each attribute in obj, check if it's a User with the given username
    for attr in dir(obj):
        if isinstance(getattr(obj, attr), User):
            user = getattr(obj, attr)
            if user.username == username:
                return user
    return None


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
            res = _find_package_list(
                value, include_pkgs, exclude_pkgs, visited, new_path
            )
            if res is None:
                continue
            if key == "exclude_packages":
                exclude_pkgs += res
            else:
                include_pkgs += res


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

    logger.debug(f"Storing enabled services to {state_path}/enabled_services")
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
    # state_path = "mnt" / state_path if dry_run else state_path
    with open(f"{state_path}/installed_packages", "r") as f:
        packages = json.load(f)
    with open(f"{state_path}/enabled_services", "r") as f:
        services = [pkg.strip() for pkg in f.readlines() if pkg.strip()]
    return (packages, services)


def load_previous_configuration(state_path: Path):
    """Load the previous configuration from the specified state path."""
    config_path = state_path / "configuration.json"
    if not config_path.exists():
        logger.warning(f"No configuration file found at {config_path}")
        return None

    with open(config_path, "r") as f:
        config_data = json.load(f)

    logger.debug(f"Loading configuration from {config_data}")
    # config = load_configuration(config_data)
    # return config
    return config_data


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

    execute_command(
        f"mount -o subvol=generations/{generation}/rootfs {root_part} {next_current}"
    )
    execute_command(f"mount {boot_part} {next_current}/boot")
    execute_command(f"mount {root_part} {next_current}/kod")
    execute_command(f"mount -o subvol=store/home {root_part} {next_current}/home")

    subdirs = ["root", "var/log", "var/tmp", "var/cache", "var/kod"]
    for dir in subdirs:
        execute_command(f"mount --bind /kod/store/{dir} {next_current}/{dir}")

    # Write generation number
    (next_current / ".generation").write_text(str(generation))

    logger.debug("Next generation mount setup complete")

    return str(next_current)


def update_kernel_hook(
    conf, kernel_package: str, mount_point: str
) -> Callable[[], None]:
    """Create a hook function to update the kernel for a specified package."""

    def hook() -> None:
        logger.info(f"Updating kernel: {kernel_package}")
        kernel_file, kver = conf._base.get_kernel_info(
            mount_point, package=kernel_package
        )
        logger.debug(f"Kernel version: {kver}")
        logger.debug(f"Copying {kernel_file} to /boot/vmlinuz-{kver}")
        exec_chroot(f"cp {kernel_file} /boot/vmlinuz-{kver}", mount_point=mount_point)

    return hook


def update_initramfs_hook(
    conf, kernel_package: str, mount_point: str
) -> Callable[[], None]:
    """Create a hook function to update the initramfs for a specified package."""

    def hook() -> None:
        logger.info(f"Updating initramfs for kernel: {kernel_package}")
        kernel_file, kver = conf._base.get_kernel_info(
            mount_point, package=kernel_package
        )
        logger.debug(f"Kernel version: {kver}")
        conf._base.generate_initramfs(mount_point, kver)

    return hook


# Temporary version without dry-run support


def store_state_tmp(state_path: str, config, kernel, packages, services) -> None:
    """Store the list of packages that are installed and the list of services that are enabled."""

    list_packages = repo_packages_list(kernel, packages)
    with open(f"{state_path}/installed_packages", "w") as f:
        json.dump(list_packages, f, indent=2)

    logger.debug(f"Storing enabled services to {state_path}/enabled_services")
    with open(f"{state_path}/enabled_services", "w") as f:
        f.write("\n".join(services))

    installed_packages_cmd = config._base.list_installed_packages()
    installed_pakages_version = subprocess.run(
        installed_packages_cmd, shell=True, capture_output=True, text=True
    ).stdout
    with open(f"{state_path}/packages.lock", "w") as f:
        f.write(installed_pakages_version)


# def load_packages_services_tmp(state_path: Path) -> tuple[dict, list]:
#     """Load the list of packages that are installed and the list of services that are enabled."""
#     packages = None
#     services = None
#     with open(f"{state_path}/installed_packages", "r") as f:
#         packages = json.load(f)
#     with open(f"{state_path}/enabled_services", "r") as f:
#         services = [pkg.strip() for pkg in f.readlines() if pkg.strip()]
#     return (packages, services)
