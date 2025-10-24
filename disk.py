from dataclasses import dataclass


@dataclass
class Partition:
    name: str
    device: str
    params: str | None = None


def disk_definition(device: str, swap_size: str | None):
    print("This is the disk module.")
    print(f"Defining disk for device: {device} with swap size: {swap_size}")
    return [
        Partition(name="root", device=device, params="size=20G"),
        Partition(
            name="swap",
            device=device,
            params=f"size={swap_size}" if swap_size else "size=2G",
        ),
        Partition(name="home", device=device, params="size=remaining"),
        Partition(name="efi", device=device, params="size=512M"),
    ]
