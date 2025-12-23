"""Base repository configuration classes."""

# from dataclasses import dataclass
from typing import override

from pykod.base import NestedDict


class PackageList:
    def __init__(self) -> None:
        self._pkgs = {}  # (Repository, [])

    def new(self, repo, items) -> None:
        self._pkgs = {repo: items}  # (Repository, [])
        return self

    def __add__(self, other_pkgs):
        new_list = PackageList()
        # _list = new_list._pkgs
        for repo, items in self._pkgs.items():
            if repo in new_list._pkgs:
                new_list._pkgs[repo] += items
            else:
                new_list._pkgs[repo] = items
        for repo, items in other_pkgs._pkgs.items():
            if repo in new_list._pkgs:
                new_list._pkgs[repo] += items
            else:
                new_list._pkgs[repo] = items

        return new_list

    def __iadd__(self, other_pkgs):
        """In-place addition operator (+=) for PackageList.

        Args:
            other_pkgs: Another PackageList to merge into this one

        Returns:
            self: The modified PackageList object
        """
        for repo, items in other_pkgs._pkgs.items():
            if repo in self._pkgs:
                # Merge items from the same repository
                self._pkgs[repo] += items
            else:
                # Add new repository entry
                self._pkgs[repo] = items

        return self

    @override
    def __repr__(self) -> str:
        res = "PKGS["
        for x in self._pkgs.items():
            res += f"\n => {x}"
        res += "\n]"
        # return pprint.pformat(self._data, indent=2, width=10)
        return res

    def install(self):
        for repo, items in self._pkgs.items():
            # print(f"Installing from repo {repo}:")
            repo.install(items)
            # for item in items:
            #     print(f"  - {item}")

    def remove(self):
        for repo, items in self._pkgs.items():
            print(f"Removing from repo {repo}:")
            repo.remove(items)
            # for item in items:
            #     print(f"  - {item}")

    def to_list(self):
        all_items = []
        for items in self._pkgs.values():
            all_items.extend(items)
        return all_items


class Repository:
    def __init__(self):
        self._pkgs = {}

    def __getitem__(self, items) -> PackageList:
        print(self, items)
        if isinstance(items, (list, tuple)):
            return PackageList().new(self, items)
        return PackageList().new(self, (items,))

    @override
    def __repr__(self) -> str:
        # return pprint.pformat(self._data, indent=2, width=10)
        return f"{self.__dict__}"

    def packages(self):
        return self._pkgs
