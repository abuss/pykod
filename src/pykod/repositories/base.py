"""Base repository configuration classes."""


class PackageList:
    def __init__(self) -> None:
        self._pkgs = {}  # (Repository, [])

    def new(self, repo, items) -> "PackageList":
        self._pkgs = {repo: items}  # (Repository, [])
        return self

    def __add__(self, other_pkgs):
        new_list = PackageList()
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

    def __len__(self) -> int:
        total = 0
        for items in self._pkgs.values():
            total += len(items)
        return total

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

    def __repr__(self) -> str:
        res = "PKGS["
        for repo, pkgs in self._pkgs.items():
            res += f"\n   => {repo.__class__.__name__}: {pkgs}"
        res += "\n]"
        return res

    def items(self):
        for repo, items in self._pkgs.items():
            yield repo, items

    def to_list(self):
        all_items = []
        for items in self._pkgs.values():
            all_items.extend(items)
        return all_items


class Repository:
    def __init__(self):
        self._pkgs = {}

    def __getitem__(self, items) -> PackageList:
        if isinstance(items, (list, tuple)):
            return PackageList().new(self, items)
        return PackageList().new(self, (items,))

    def __repr__(self) -> str:
        return f"{self.__dict__}"

    # def get_base_packages(self, conf) -> dict:
    #     return {}

    # def install_base(self, mount_point, packages): ...

    def packages(self):
        return self._pkgs

    def update_database(self) -> str:
        return ""

    def update_installed_packages(self, packages: tuple) -> str:
        return ""
