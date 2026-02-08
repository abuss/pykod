# pykod - Python-based Linux System Configuration Tool

**pykod** is a declarative system configuration tool for Linux distributions, enabling atomic system updates through BTRFS snapshots and generations.

## Features

- 🐧 **Multi-Distribution Support**: Arch Linux, Debian, Ubuntu
- 📦 **Declarative Configuration**: Define your entire system in Python
- 🔄 **Atomic Updates**: BTRFS-based generations for safe system updates
- 🚀 **systemd-boot**: Modern bootloader support across all distributions
- 🎨 **GPU Driver Support**: Automatic driver packages for NVIDIA, AMD, Intel
- 🔧 **Reproducible Builds**: Version-controlled system configurations

## Supported Distributions

| Distribution | Status | Bootstrap Tool | Package Manager |
|--------------|--------|----------------|-----------------|
| Arch Linux   | ✅ Stable | pacstrap | pacman |
| Debian       | ✅ Stable | debootstrap | apt |
| Ubuntu       | ✅ Stable | debootstrap | apt |

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/your-repo/pykod.git
cd pykod

# Install dependencies (example for Arch)
sudo pacman -S python python-pip btrfs-progs systemd-boot

# Install pykod
pip install -e .
```

### Basic Usage

#### Arch Linux Configuration

```python
from pykod import *
from pykod.repositories import Arch

arch = Arch()
conf = Configuration(base=arch)

conf.devices = Devices(
    disk0=Disk(
        device="/dev/sda",
        partitions=[
            Partition(name="efi", size="512M", type="esp", mountpoint="/boot"),
            Partition(name="root", size="100%", type="btrfs", mountpoint="/"),
        ],
    ),
)

conf.boot = Boot(
    kernel=Kernel(package=arch["linux"]),
    loader=Loader(type="systemd-boot"),
)

# ... more configuration ...
```

#### Debian Configuration

```python
from pykod import *
from pykod.repositories import Debian

debian = Debian()  # Defaults to "stable"
conf = Configuration(base=debian)

conf.boot = Boot(
    kernel=Kernel(package=debian["linux-image-amd64"]),
    loader=Loader(type="systemd-boot"),
)

# ... rest similar to Arch ...
```

#### Ubuntu Configuration

```python
from pykod import *
from pykod.repositories import Debian

ubuntu = Debian(release="noble", variant="ubuntu")
conf = Configuration(base=ubuntu)

conf.boot = Boot(
    kernel=Kernel(package=ubuntu["linux-image-generic"]),
    loader=Loader(type="systemd-boot"),
)

# ... rest similar to Debian ...
```

## Distribution-Specific Details

### Common Features (All Distributions)

✅ systemd-boot bootloader  
✅ BTRFS with atomic generations  
✅ systemd service management  
✅ GPU driver auto-detection  
✅ Flatpak support  

### Distribution Differences

#### Package Names

| Component | Arch | Debian/Ubuntu |
|-----------|------|---------------|
| Build tools | `base-devel` | `build-essential` |
| Kernel | `linux` | `linux-image-amd64` or `linux-image-generic` |
| Firefox | `firefox` | `firefox-esr` (Debian) / `firefox` (Ubuntu) |
| SSH service | `sshd` | `ssh` |
| Intel microcode | `intel-ucode` | `intel-microcode` |
| AMD microcode | `amd-ucode` | `amd64-microcode` |

#### GPU Packages

**NVIDIA:**
- Arch: `nvidia`, `nvidia-utils`, `nvidia-settings`
- Debian: `nvidia-driver`, `nvidia-settings`

**AMD:**
- Arch: `xf86-video-amdgpu`, `mesa`, `vulkan-radeon`
- Debian: `xserver-xorg-video-amdgpu`, `mesa-vulkan-drivers`

**Intel:**
- Arch: `xf86-video-intel`, `mesa`, `vulkan-intel`
- Debian: `xserver-xorg-video-intel`, `mesa-vulkan-drivers`

### Debian Release Options

```python
# Track current stable (recommended)
debian = Debian()  # or Debian(release="stable")

# Specific version
debian = Debian(release="bookworm")  # Debian 12

# Testing branch
debian = Debian(release="testing")
```

### Ubuntu Release Options

```python
# Ubuntu 24.04 LTS (with default repositories: main + universe)
ubuntu = Debian(release="noble", variant="ubuntu")

# Ubuntu 22.04 LTS
ubuntu = Debian(release="jammy", variant="ubuntu")

# Ubuntu 20.04 LTS
ubuntu = Debian(release="focal", variant="ubuntu")
```

### Repository Components

#### Ubuntu Components

Ubuntu repositories are divided into 4 components. By default, `main` and `universe` are enabled:

```python
# Default (main + universe - recommended)
ubuntu = Debian(release="noble", variant="ubuntu")

# All repositories (including proprietary)
ubuntu = Debian(
    release="noble", 
    variant="ubuntu",
    components=["main", "universe", "multiverse", "restricted"]
)

# Minimal (main only)
ubuntu = Debian(release="noble", variant="ubuntu", components=["main"])
```

**Component descriptions:**
- **main** - Canonical-supported free and open-source software
- **universe** - Community-maintained free and open-source software (enabled by default)
- **multiverse** - Software restricted by copyright or legal issues
- **restricted** - Proprietary drivers for devices

#### Debian Components

Debian repositories have 3 components. By default, only `main` is enabled:

```python
# Default (main only)
debian = Debian()

# With contrib and non-free
debian = Debian(components=["main", "contrib", "non-free"])

# Non-free-firmware (Debian 12+)
debian = Debian(components=["main", "contrib", "non-free", "non-free-firmware"])
```

**Component descriptions:**
- **main** - Free software that meets the Debian Free Software Guidelines
- **contrib** - Free software that depends on non-free software
- **non-free** - Software that does not meet DFSG (proprietary licenses)
- **non-free-firmware** - Non-free firmware files (Debian 12+)

## Architecture

### Generations System

pykod uses BTRFS subvolumes to create immutable system snapshots:

```
/
├── boot/                    # ESP partition (systemd-boot)
├── kod/
│   ├── generations/
│   │   ├── 0/
│   │   │   └── rootfs/     # Generation 0 (initial install)
│   │   ├── 1/
│   │   │   └── rootfs/     # Generation 1 (first update)
│   │   └── ...
│   ├── store/
│   │   ├── home/           # Persistent user data
│   │   ├── root/           # Persistent root home
│   │   └── var/            # Persistent variable data
│   └── current/            # Symlink to active generation
```

### Update Process

```bash
# Install initial system
python configuration.py install

# Update system (creates new generation)
python configuration.py rebuild

# Rollback (boot into previous generation via bootloader)
# Select previous generation from systemd-boot menu
```

## Examples

See the `example/` directory for complete configuration examples:

- `configuration.py` - Arch Linux with GNOME + Cosmic
- `configuration-debian.py` - Debian stable with GNOME
- `configuration-ubuntu.py` - Ubuntu 24.04 with GNOME
- `configuration-vm.py` - Minimal VM configuration
- `configuration-lenovo.py` - Laptop-specific configuration

## Advanced Configuration

### GPU Detection

```python
from pykod.repositories.arch import GPU_PACKAGES
# or
from pykod.repositories.debian import GPU_PACKAGES

# Intel GPU
conf.hardware = Hardware(
    gpu=arch[*GPU_PACKAGES["intel"]["base"]],
)

# NVIDIA GPU with 32-bit support
conf.hardware = Hardware(
    gpu=arch[
        *GPU_PACKAGES["nvidia"]["base"],
        *GPU_PACKAGES["nvidia"]["32bit"],
    ],
)
```

### Multiple Desktops

```python
conf.desktop = DesktopManager(
    display_manager=Service(package=arch["gdm"]),
    environments={
        "gnome": DesktopEnvironment(enable=True, package=arch["gnome"]),
        "plasma": DesktopEnvironment(enable=True, package=arch["plasma"]),
        "cosmic": DesktopEnvironment(enable=True, package=arch["cosmic"]),
    },
)
```

### Custom Package Repositories

```python
# Arch with AUR
from pykod.repositories import Arch, AUR

arch = Arch()
aur = AUR(helper="yay")

conf.packages = Packages(
    arch["firefox", "git", "vim"] +
    aur["visual-studio-code-bin", "brave-bin"]
)
```

## Requirements

- Python 3.10+
- BTRFS filesystem support
- systemd-boot
- One of: Arch Linux, Debian, or Ubuntu

### Distribution-Specific Requirements

**Arch Linux:**
- `pacstrap`, `arch-install-scripts`
- `btrfs-progs`
- `dracut`

**Debian/Ubuntu:**
- `debootstrap`
- `btrfs-progs`
- `dracut`
- `systemd-boot` (from Debian repos)

## Contributing

Contributions welcome! Please see CONTRIBUTING.md for guidelines.

### Adding New Distribution Support

To add support for a new distribution:

1. Create `src/pykod/repositories/your_distro.py`
2. Implement all abstract methods from `Repository` class
3. Add GPU package mappings
4. Create example configuration in `example/`
5. Update this README

## License

MIT License - See LICENSE file for details

## Project Status

- ✅ Arch Linux - Stable
- ✅ Debian - Stable
- ✅ Ubuntu - Stable
- 🚧 Fedora - Planned
- 🚧 openSUSE - Planned

## Credits

Developed by Antal Buss and contributors.

Inspired by NixOS's declarative approach to system configuration.
