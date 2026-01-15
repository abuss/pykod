#!/usr/bin/env python3
"""
CLI interface for KodOS Configuration Manager.

This module defines CLI-related functions extracted from the Configuration class:
- run(config): command-line dispatcher
- remove_generation(config, generation_id): remove a specific generation
- list_generations(config): list all available generations

These functions expect an instance of `Configuration` to be passed in, allowing
them to delegate operational work back to the config object (e.g., install/rebuild).
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .common import execute_command


def run(config: Any) -> None:
    """
    Entry point for the CLI. Parses arguments and delegates to Configuration methods.
    """
    parser = argparse.ArgumentParser(description="KodOS Configuration Manager")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Install command
    subparsers.add_parser("install", help="Install the configuration")

    # Rebuild command
    rebuild_parser = subparsers.add_parser("rebuild", help="Rebuild the configuration")
    rebuild_parser.add_argument(
        "-s",
        "--switch",
        action="store_true",
        help="Create a new generation and live switch to the new generation after rebuild",
    )
    rebuild_parser.add_argument(
        "-u",
        "--upgrade",
        action="store_true",
        help="Upgrade all packages to their latest versions during rebuild",
    )
    rebuild_parser.add_argument(
        "-r",
        "--reboot",
        action="store_true",
        help="Reboot the system to switch to the new generation after rebuild",
    )

    # Remove generation command
    remove_gen_parser = subparsers.add_parser(
        "remove_generation", help="Remove a specific generation"
    )
    remove_gen_parser.add_argument(
        "generation_id", type=int, help="Generation ID to remove"
    )

    # Rebuild user command
    subparsers.add_parser("rebuild-user", help="Rebuild user configuration")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    print("-" * 100)
    print(f"Running {args.command} command...")
    print("Configuration attributes:")
    print("\n", "-" * 80)

    if args.command == "install":
        config.install()
    elif args.command == "rebuild":
        switch = args.switch if hasattr(args, "switch") else False
        upgrade = args.upgrade if hasattr(args, "upgrade") else False
        reboot = args.reboot if hasattr(args, "reboot") else False
        config.rebuild(live_switch=switch, upgrade=upgrade, reboot=reboot)
    elif args.command == "remove_generation":
        remove_generation(config, args.generation_id)
    elif args.command == "list_generation":
        list_generations(config)
    elif args.command == "rebuild-user":
        import os

        user = os.environ.get("USER")
        print(f"USER: {user}")
        config.rebuild_user(user)


def remove_generation(config: Any, generation_id: int) -> None:
    """
    Remove a specific generation and its associated boot entry and subvolume.
    """
    print(f"Removing generation {generation_id}...")
    generation_path = Path(f"/kod/generations/{generation_id}")

    if not generation_path.exists():
        print(f"Generation {generation_id} does not exist")
        return

    # Remove the boot entry for the generation
    boot_entry_path = f"/boot/loader/entries/kod-{generation_id}.conf"
    if Path(boot_entry_path).exists():
        execute_command(f"rm {boot_entry_path}")
        print(f"Removed boot entry: {boot_entry_path}")

    # Remove the BTRFS subvolume if it exists
    rootfs_path = generation_path / "rootfs"
    if rootfs_path.exists():
        execute_command(f"btrfs subvolume delete {rootfs_path}")

    # Remove the generation directory
    execute_command(f"rm -rf {generation_path}")
    print(f"Generation {generation_id} removed successfully")


def list_generations(config: Any) -> None:
    """
    List all available generations with basic metadata if available.
    """
    generations_dir = Path("/kod/generations")

    if not generations_dir.exists():
        print("No generations directory found")
        return

    generations = [
        p for p in generations_dir.iterdir() if p.is_dir() and p.name.isdigit()
    ]

    if not generations:
        print("No generations found")
        return

    print("Available generations:")
    for gen_path in sorted(generations, key=lambda x: int(x.name)):
        gen_id = gen_path.name
        # Try to read additional info about the generation
        try:
            installed_packages_file = gen_path / "installed_packages"
            if installed_packages_file.exists():
                with open(installed_packages_file, "r") as f:
                    packages_info = json.load(f)
                    kernel = packages_info.get("kernel", ["unknown"])[0]
                    print(f"  Generation {gen_id}: kernel={kernel}")
            else:
                print(f"  Generation {gen_id}: info unavailable")
        except Exception as e:
            print(f"  Generation {gen_id}: error reading info ({e})")
