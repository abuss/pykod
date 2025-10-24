# from dataclasses import field
# from dataclasses import dataclass
# from typing import NamedTuple, Optional
# from collections import namedtuple
# from typing import Any
#
# packages_to_install = []
# # from pykod.repos import ArchRepo, AURRepo, FlatpakRepo

from typing import Callable
from pprint import pprint
import pykod.section as section


class ConfigurationClass(type):
    def __new__(cls, name, bases, attrs):
        return super(ConfigurationClass, cls).__new__(cls, name, bases, attrs)


class Configuration(metaclass=ConfigurationClass):
    def __init__(self, name: str):
        self.system_config = []
        self.name = name
        self._inside_composite_call = False

    # def __enter__(self):
    #     return self
    #
    # def __exit__(self, exc_type, exc_value, traceback):
    #     print("\nFinal system configuration:")
    #     for i, item in enumerate(self.system_config):
    #         print(f"\n{i + 1:2d}. {type(item).__name__}:")
    #         pprint(item, indent=4, width=100)

    def __getattr__(self, name):
        # print(" ==> ", name)
        function = getattr(section, name)
        return self._wrap(function)

    def _wrap(self, func: Callable):
        def fn(*args, **kwargs):
            result = func(*args, **kwargs)

            # Define composite functions that contain other configuration objects
            composite_functions = ["Boot"]
            component_functions = ["Kernel", "Loader"]

            # If this is a composite function, check if its arguments are from component functions
            if func.__name__ in composite_functions:
                # Filter out any component results that were just added
                # by checking the last few items in system_config
                components_to_remove = []
                for arg in args:
                    # If the argument type matches a component that was just added, mark for removal
                    if (
                        hasattr(arg, "__class__")
                        and arg.__class__.__name__ in component_functions
                    ):
                        # Check if this exact object is in the recent entries
                        for i in range(
                            len(self.system_config) - 1,
                            max(-1, len(self.system_config) - 10),
                            -1,
                        ):
                            if i >= 0 and self.system_config[i] == arg:
                                components_to_remove.append(i)
                                break

                # Remove the component entries (in reverse order to maintain indices)
                for idx in sorted(components_to_remove, reverse=True):
                    self.system_config.pop(idx)

            # Add the result to system_config
            self.system_config.append(result)
            return result

        return fn
