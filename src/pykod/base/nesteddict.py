from typing import override


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
