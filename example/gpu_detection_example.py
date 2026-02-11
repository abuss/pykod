#!/usr/bin/env python3
"""
Example demonstrating GPU auto-detection feature in pykod.

This example shows different ways to configure GPU support:
1. Auto-detection (recommended for most users)
2. Explicit GPU selection
3. Disabling GPU support
4. CPU microcode auto-detection

Usage:
    python3 gpu_detection_example.py install --dry-run
    python3 gpu_detection_example.py rebuild --dry-run
"""

from tabnanny import verbose

from pykod import *
from pykod.repositories import Arch

# Create base repository
archpkgs = Arch(mirror_url="https://geo.mirror.pkgbuild.com")

# Create configuration
# Note: Set debug=False for actual GPU detection to work (debug mode prints commands but doesn't execute them)
conf = Configuration(base=archpkgs, dry_run=False, verbose=True, debug=False)

# ============================================================================
# OPTION 1: Auto-detect GPU (RECOMMENDED)
# ============================================================================
# This will automatically detect your GPU vendor and install appropriate drivers
# Supports hybrid graphics (e.g., laptops with Intel + NVIDIA)
conf.hardware = Hardware(
    gpu="intel",  # Automatically detect GPU vendor
    # gpu_32bit=False,  # Include 32-bit libraries (useful for Steam/gaming)
    # gpu_extras=True,  # Include extra packages (proprietary alternatives)
)

# ============================================================================
# OPTION 2: Explicit GPU selection
# ============================================================================
# Use this if you want to force a specific driver, or if auto-detection fails
# Uncomment the following lines to use explicit selection:
#
# conf.hardware = Hardware(
#     gpu="nvidia",       # Force NVIDIA proprietary drivers
#     gpu_32bit=True,
#     gpu_extras=True,
# )

# ============================================================================
# OPTION 3: Disable GPU auto-detection
# ============================================================================
# Use this if you want to manage GPU drivers manually
# Uncomment the following lines to skip GPU installation:
#
# conf.hardware = Hardware(
#     gpu=None,           # Skip GPU driver installation
# )

# ============================================================================
# CPU Microcode Configuration
# ============================================================================
# The cpu_microcode field can be:
#   - "auto": Detect CPU vendor and install appropriate microcode (default)
#   - "intel": Force Intel microcode (intel-ucode)
#   - "amd": Force AMD microcode (amd-ucode)
#   - None: Skip microcode installation

conf.hardware.cpu_microcode = "auto"  # Detect and install intel-ucode or amd-ucode

# ============================================================================
# Additional Hardware Configuration
# ============================================================================
# You can combine GPU detection with other hardware packages:
conf.hardware.audio = archpkgs["pipewire-alsa", "pipewire-pulse"]
conf.hardware.wireless = archpkgs["iw", "wireless_tools"]

# ============================================================================
# Package Detection Output (for debugging)
# ============================================================================
print("\n" + "=" * 60)
print("GPU AUTO-DETECTION RESULTS")
print("=" * 60)

# Detect GPU vendors
detected_vendors = conf.hardware.detect_gpu_vendors()
print(f"\nDetected GPU vendors: {detected_vendors}")

# Get GPU packages
gpu_packages = conf.hardware.get_gpu_packages()
print(f"GPU packages to install: {gpu_packages}")

# Get CPU microcode
cpu_microcode = conf.hardware.get_cpu_microcode_package()
print(f"CPU microcode package: {cpu_microcode}")

# Get all hardware packages
all_hardware_pkgs = conf.hardware.get_all_packages(archpkgs)
print(f"\nAll hardware packages:")
print(all_hardware_pkgs)

print("\n" + "=" * 60)
print("CONFIGURATION SUMMARY")
print("=" * 60)
print(f"GPU mode: {conf.hardware.gpu}")
print(f"GPU 32-bit support: {conf.hardware.gpu_32bit}")
print(f"GPU extras: {conf.hardware.gpu_extras}")
print(f"CPU microcode: {conf.hardware.cpu_microcode}")

if __name__ == "__main__":
    from pykod.cli import run

    run(conf)
