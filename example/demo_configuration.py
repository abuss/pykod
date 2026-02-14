# class Repo:
#     def __init__(self) -> None:
#         self._listpkgs = set()

#     def __enter__(self):
#         print("Enter repo")
#         return self

#     def __exit__(self, a, b, c):
#         print("Exit repo", a, b, c)
#         return self._listpkgs

#     @override
#     def __getattr__(self, name):
#         print(name)
#         self._listpkgs.add(name)
#         return self

#     @override
#     def show(self):
#         print(self._listpkgs)

#     @override
#     def __getitem__(self, items):
#         if isinstance(items, (list, tuple)):
#             for item in items:
#                 print(item)
#                 self._listpkgs.add(item)
#         else:
#             print(items)
#             self._listpkgs.add(items)
#         return self


# class Archlinux(Repo):
#     def __init__(self, url) -> None:
#         super().__init__()
#         self.url = url

#     def install(self):
#         print("Download repo indices")
#         print("Configure the repo")


# class AUR(Repo):
#     def __init__(self, helper, helper_url) -> None:
#         super().__init__()
#         self.helper = helper
#         self.helper_url = helper_url

#         def install(self):
#             print("Download helper")
#             print("Prepare helper")


# def arch_repo(url):
#     return Archlinux(url)


# Structure
#
# - repository (package sources)
# - system
#   - devices (disk)
#   - boot
#       - kernel
#       - loader
#   - locale
#   - network
#   - hardware
#       - sound
#       - scanner
# - desktop
#   - windows manager (gnome, kde, cosmic, ...)
#   - desktop manager (gdm, lightdm, etc)
# - users
# - environment
#   - services
#   - fonts
#   - programs
#

# %%

import pprint
from types import SimpleNamespace
from typing import override

from pykod.disk import Partition

# %%

# def Arch(str):
#     return str


# def create_lambda_func(function_names):
#     """Create lambda functions that return their kwargs and add them to calling scope"""
#     import inspect

#     # Get the frame of the caller
#     frame = inspect.currentframe().f_back
#     caller_locals = frame.f_locals

#     for name in function_names:
#         caller_locals[name] = lambda **kwargs: kwargs


def create_lambda_functions(function_names):
    """Create lambda functions that return their kwargs and add them to global scope"""
    for name in function_names:
        globals()[name] = lambda **kwargs: SimpleNamespace(**kwargs)


# Create the functions for the given list
# create_lambda_functions(["Repo", "System", "Users"])


class NestedObject:
    def __init__(self, **kwargs):
        self.__dict__["_data"] = {}
        for k, v in kwargs.items():
            self._data[k] = v

    def __getattr__(self, name):
        if name in self._data:
            return self._data[name]
        else:
            self._data[name] = NestedObject()
            return self._data[name]

    def __setattr__(self, name, value):
        if name == "_data":
            super().__setattr__(name, value)
        else:
            if isinstance(value, dict):
                value = NestedObject(**value)
            self._data[name] = value

    @override
    def __repr__(self) -> str:
        res = ""
        # return json.dumps(self._data, indent=4)
        return pprint.pformat(self._data, indent=2, width=10)


class Repo(NestedObject):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.__dict__["_pkgs"] = {}

    def __getattr__(self, name):
        if name in self._data:
            return self._[name]
        else:
            self._pkgs[name] = NestedObject()
            return self._pkgs[name]

    def __setattr__(self, name, value):
        print(name, value)
        if name == "_pkgs":
            super().__setattr__(name, value)
        else:
            if isinstance(value, dict):
                value = NestedObject(**value)
            self._pkgs[name] = value

    @override
    def __getitem__(self, items):
        if isinstance(items, (list, tuple)):
            for item in items:
                # print(item)
                self._pkgs[item] = NestedObject()
        else:
            # print(items)
            self._pkgs[items] = NestedObject()
        return self

    def __add__(self, o):
        return [self, o]

    @override
    def __repr__(self) -> str:
        # res = ""
        # return json.dumps(self._data, indent=4)
        return f"{} => {pprint.pformat(self._data, indent=2, width=10)}"


class Arch(Repo):
    def __init__(self, repos=["base", "contrib"], **kwargs):
        super().__init__(repos=repos, **kwargs)
        # print(" ++++++++ Post init +++++++++")
        # self.repos = repos

    def install(self):
        print("Installing Arch repo:", self)


class AUR(Repo):
    def install(self):
        print("Installing AUR repo:", self)


class Configuration:
    def __init__(self):
        import inspect

        frame = inspect.currentframe().f_back
        self._sections = [
            "System",
            "Users",
            "User",
            "Repositories",
            # "Arch",
            # "AUR",
            "Flatpak",
            "Network",
            "Disk",
            "Partition",
            "Boot",
            "Kernel",
            "Loader",
            "Locale",
        ]
        for name in self._sections:
            exec(
                f"{name} = lambda **kwargs: NestedObject(**kwargs)",
                frame.f_globals,
                frame.f_locals,
            )
        self.repos = Repositories()
        self.system = System()
        # Create the functions for the given list
        # create_lambda_functions(["Repo", "System", "Users", "Arch", "AUR", "User"])
        # pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Get the local variables from the calling framearchpkgs = Arch(url="https://mirror.rackspace.com/archlinux")
        import inspect

        frame = inspect.currentframe().f_back
        locals_dict = frame.f_locals
        # Remove the created functions
        for name in self._sections:
            exec(f"del {name}", frame.f_globals, frame.f_locals)

        # Add variables as attributes to this object
        for name, value in locals_dict.items():
            if not name.startswith("_") and name != "c":
                setattr(self, name, value)

    # @override
    # def __repr__(self) -> str:
    #     return str(self.__dict__)


archpkgs2 = Arch(url="https://mirror.rackspace.com/archlinux")

conf = Configuration()

with conf as c:
    import cli

    import pykod.disk as disk
    import pykod.openssh as openssh

    # c.repos = Repositories(
    #     archpkgs=Arch(url="https://mirror.rackspace.com/archlinux"),
    #     aurpkgs=AUR(helper="yay", helper_url="https://aur.archlinux.org/yay-bin.git"),
    #     flatpakpkgs=Flatpak(url_hub="flathub"),
    # )
    # c.repos = {
    #     "archpkgs": Arch(url="https://mirror.rackspace.com/archlinux"),
    #     "aurpkgs": AUR(
    #         helper="yay", helper_url="https://aur.archlinux.org/yay-bin.git"
    #     ),
    # }
    c.archpkgs = Arch(url="https://mirror.rackspace.com/archlinux")
    c.aurpkgs = AUR(helper="yay", helper_url="https://aur.archlinux.org/yay-bin.git")
    c.flatpakpkgs = Flatpak(url_hub="flathub")

    c.system = System(
        disk0=Disk(
            device="/dev/vda",
            partitions=[
                Partition(name="efi", params="size=512M"),
                Partition(name="root", params="size=20G"),
                Partition(name="swap", params="size=2G"),
                Partition(name="home", params="size=remaining"),
            ],
        ),
        boot=Boot(
            kernel=Kernel(
                package="linux",
                modules=[
                    "xhci_pci",
                    "ohci_pci",
                    "ehci_pci",
                    "virtio_pci",
                    "ahci",
                    "usbhid",
                    "sr_mod",
                    "virtio_blk",
                ],
            ),
            loader=Loader(
                type="systemd-boot",
                timeout=10,
                include=["memtest86+"],
            ),
            # loader={
            #     "type": "systemd-boot",
            #     "timeout": 10,
            #     "include": ["memtest86+"],
            # },
        ),
        locale=Locale(
            default="en_CA.UTF-8 UTF-8",
            additional_locales=[
                "en_US.UTF-8 UTF-8",
                "en_GB.UTF-8 UTF-8",
            ],
            extra_settings={
                "LC_ADDRESS": "en_CA.UTF-8",
                "LC_IDENTIFICATION": "en_CA.UTF-8",
                "LC_MEASUREMENT": "en_CA.UTF-8",
                "LC_MONETARY": "en_CA.UTF-8",
                "LC_NAME": "en_CA.UTF-8",
                "LC_NUMERIC": "en_CA.UTF-8",
                "LC_PAPER": "en_CA.UTF-8",
                "LC_TELEPHONE": "en_CA.UTF-8",
                "LC_TIME": "en_CA.UTF-8",
            },
            keymap="us",
            timezone="America/Edmonton",
        ),
        network=Network(
            hostname="eszkoz",
            settings={"ipv6": True},
        ),
    )
    packages = [c.archpkgs.btop, c.archpkgs.vscode]

    ret = c.archpkgs["brave", "opencode"] + c.aurpkgs["zed", "opera"]

    c.system.boot.loader.package = "grub2"
    # devices={disk := "hda"})
    user = Users(root=User(nopassword=True, shell="/bin/bash"))
    user.zsh.enable = True

print("-" * 100)
# Print all attributes from conf
print("Configuration attributes:")
for attr_name in dir(conf):
    if not attr_name.startswith("_"):
        attr_value = getattr(conf, attr_name)
        print(f"> {attr_name}: {attr_value} :: {type(attr_value)}")
# pprint.pp(conf)
# print(dir(objx))

print("\n", "-" * 100)
print(conf.repos)
# for k, v in conf.get("repos", {}).items():
#     print(k)
#     v.install()

for attr_name in dir(conf):
    if not attr_name.startswith("_"):
        attr_value = getattr(conf, attr_name)
        if isinstance(attr_value, Repo):
            print(f"====> {attr_name}: {attr_value} :: {type(attr_value)}")
            attr_value.install()

print(conf.ret)
print(conf.archpkgs._pkgs)
print(conf.aurpkgs._pkgs)
