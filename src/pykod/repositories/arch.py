"""Arch Linux repository configuration."""

# from pykod.config import Install, Rebuild
from pykod.common import exec, exec_chroot, get_dry_run

from .base import Repository


class Arch(Repository):
    def __init__(self, repos=["base", "contrib"], **kwargs):
        # super().__init__(repos=repos, **kwargs)
        self.repos = repos
        self.mirror_url = kwargs.get(
            "mirror_url", "https://mirror.rackspace.com/archlinux/"
        )
        # self.url = f"{self.mirror_url}core/os/x86_64/"

    def install_base(self, mount_point, packages):
        list_pkgs = packages._pkgs[self]
        print(f"{list_pkgs=}")
        exec(f"pacstrap -K {mount_point} {' '.join(list_pkgs)}")

    def install(self, items) -> None:
        print("[install] Arch repo:", self)
        for item in items:
            print(f"  - {item}")

    def remove(self, items) -> None:
        print("[remove] Arch repo:", self)
        for item in items:
            print(f"  - {item}")

    def get_base_packages(self, conf) -> dict:
        """Get the base packages to install for the given configuration."""
        # CPU microcode
        with open("/proc/cpuinfo") as f:
            while True:
                line = f.readline()
                if "AuthenticAMD" in line:
                    microcode = "amd-ucode"
                    break
                if "GenuineIntel" in line:
                    microcode = "intel-ucode"
                    break

        if conf.boot and conf.boot.kernel and conf.boot.kernel.package:
            kernel_package = conf.boot.kernel.package
        else:
            kernel_package = self["linux"]

        # TODO: add verions to each package
        packages = {
            "kernel": kernel_package,
            "base": self[
                "base",
                "base-devel",
                microcode,
                "btrfs-progs",
                "linux-firmware",
                "bash-completion",
                "mlocate",
                "sudo",
                "schroot",
                "whois",
                "dracut",
                "git",
            ],
        }

        # TODO: remove this package dependency
        # packages["base"] += ["arch-install-scripts"]
        return packages

    def get_kernel_file(self, mount_point: str, package: str = "linux"):
        """Retrieve the kernel file path and version from the specified mount point."""
        kernel_pkg = package.to_list()[0]
        kernel_file = exec_chroot(
            f"pacman -Ql {kernel_pkg} | grep vmlinuz",
            mount_point=mount_point,
            get_output=True,
        )
        if get_dry_run():
            kernel_file = "linux /usr/lib/modules/6.18.1-kodos1-2/vmlinuz"
        kernel_file = kernel_file.split(" ")[-1].strip()
        kver = kernel_file.split("/")[-2]
        return kernel_file, kver

    def setup_linux(self, mount_point, kernel_package):
        kernel_file, kver = self.get_kernel_file(
            mount_point=mount_point, package=kernel_package
        )
        exec_chroot(f"cp {kernel_file} /boot/vmlinuz-{kver}")
        return kver

    def install_package(self, package_name) -> str:
        pkgs = " ".join(package_name)
        cmd = f"pacman -S --needed --noconfirm {pkgs}"
        return cmd
        # exec_chroot(cmd, mount_point=mount_point)

    def remove_package(self, package_name) -> str:
        pkgs = " ".join(package_name)
        cmd = f"pacman -Rnsc --noconfirm {pkgs}"
        return cmd
        # exec_chroot(cmd, mount_point=mount_point)

    def update_installed_packages(self) -> str:
        cmd = "pacman -Syu --noconfirm"
        return cmd
        # exec_chroot(cmd, mount_point=mount_point)

    def update_database(self) -> str:
        cmd = "pacman -Sy"
        return cmd
        # exec_chroot(cmd, mount_point=mount_point)


# Arch
def proc_repos(conf, current_repos=None, update=False, mount_point="/mnt"):
    """
    Process the repository configuration from the given config.

    This function reads the repository configuration from the given config and
    register information about how to build, install, or update each repository.
    The function will write the result to /var/kod/repos.json.

    Args:
        conf (dict): The configuration dictionary to read from.
        current_repos (dict): The current repository configuration.
        update (bool): If True, update the package list. Defaults to False.
        mount_point (str): The mount point where the installation is being
            performed. Defaults to "/mnt".

    Returns:
        tuple: A tuple containing the processed repository configuration and
            the list of packages that were installed.
    """
    # TODO: Add support for custom repositories and to be used during rebuild
    repos_conf = conf.repos
    repos = {}
    packages = []
    update_repos = False
    for repo, repo_desc in repos_conf.items():
        if current_repos and repo in current_repos and not update:
            repos[repo] = current_repos[repo]
            continue
        repos[repo] = {}
        for action, cmd in repo_desc["commands"].items():
            repos[repo][action] = cmd

        if "build" in repo_desc:
            build_info = repo_desc["build"]
            url = build_info["url"]
            build_cmd = build_info["build_cmd"]
            name = build_info["name"]

            # TODO: Generalize this code to support other distros
            # exec_chroot("pacman -S --needed --noconfirm git base-devel")
            exec_chroot(
                f"runuser -u kod -- /bin/bash -c 'cd && git clone {url} {name} && cd {name} && {build_cmd}'",
                mount_point=mount_point,
            )

        if "package" in repo_desc:
            exec_chroot(
                f"pacman -S --needed --noconfirm {repo_desc['package']}",
                mount_point=mount_point,
            )
            packages += [repo_desc["package"]]
        update_repos = True

    if update_repos:
        exec(f"mkdir -p {mount_point}/var/kod")
        with open(f"{mount_point}/var/kod/repos.json", "w") as f:
            f.write(json.dumps(repos, indent=2))

    return repos, packages
