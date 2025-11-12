from typing import Protocol, override


class Install(Protocol):
    def install(self): ...


class Rebuild(Protocol):
    def rebuild(self): ...


class RebuildUser(Protocol):
    def rebuild_user(self, user: str): ...


class NestedDict:
    def __init__(self, *args, **kwargs):
        self.__dict__["_data"] = {}
        # self._data = {}
        for k in args:
            self._data[k] = NestedDict()
        for k, v in kwargs.items():
            self._data[k] = v

    def __getattr__(self, name) -> "NestedDict":
        if name in self._data:
            return self._data[name]
        else:
            self._data[name] = NestedDict()
            return self._data[name]

    @override
    def __setattr__(self, name, value):
        if name == "_data":
            super().__setattr__(name, value)
        else:
            if isinstance(value, dict):
                value = NestedDict(**value)
            self._data[name] = value

    @override
    def __repr__(self) -> str:
        # return pprint.pformat(self._data, indent=2, width=10)
        return str(self._data)


class Configuration:
    # def __init__(self):
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

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
        # Get the local variables from the calling framearchpkgs = Arch(url="https://mirror.rackspace.com/archlinux")
        # import inspect

        # frame = inspect.currentframe().f_back
        # locals_dict = frame.f_locals
        # # Remove the created functions
        # # for name in self._sections:
        # #     exec(f"del {name}", frame.f_globals, frame.f_locals)

        # # Add variables as attributes to this object
        # for name, value in locals_dict.items():
        #     if not name.startswith("_") and name != "c":
        #         setattr(self, name, value)

    def install(self):
        for name, obj in vars(self).items():
            if hasattr(type(obj), "install"):
                print("[[[[", obj, "]]]]")
                obj.install()
