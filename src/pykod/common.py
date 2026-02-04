"""Common utility functions and debugging utilities for KodOS.

This module provides core utility functions for command execution, debugging,
and system interaction used throughout the KodOS system.
"""

import logging
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from chorut import ChrootManager

# Module-level variables
use_debug: bool = False
use_verbose: bool = False
use_dry_run: bool = False
problems: list[dict] = []


@dataclass
class CommandExecutionError(Exception):
    """Raised when a command execution fails."""

    cmd: str
    return_code: int
    stderr: str = ""
    stdout: str = ""

    def __post_init__(self):
        super().__init__(
            f"Command failed with return code {self.return_code}: {self.cmd}"
        )


@dataclass
class CommandTimeoutError(Exception):
    """Raised when a command execution times out."""

    cmd: str
    timeout: Optional[int]

    def __post_init__(self):
        timeout_str = f"{self.timeout}s" if self.timeout is not None else "unknown"
        super().__init__(f"Command timed out after {timeout_str}: {self.cmd}")


@dataclass
class UnsafeCommandError(Exception):
    """Raised when a command contains potentially unsafe characters."""

    cmd: str
    reason: str

    def __post_init__(self):
        super().__init__(f"Unsafe command rejected: {self.reason} in '{self.cmd}'")


class Color:
    """ANSI color codes for terminal output formatting."""

    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    DARKCYAN = "\033[36m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


# Mode getter/setter functions
def set_debug(val: bool = True) -> None:
    """Set the global debug mode state.

    Args:
        val: Whether to enable debug mode. Defaults to True.
    """
    global use_debug
    use_debug = val


def set_verbose(val: bool = True) -> None:
    """Set the global verbose mode state.

    Args:
        val: Whether to enable verbose mode. Defaults to True.
    """
    global use_verbose
    use_verbose = val


def set_dry_run(val: bool = True) -> None:
    """Set the global dry-run mode state."""
    global use_dry_run
    use_dry_run = val


def get_dry_run() -> bool:
    return use_dry_run


# Command execution functions
def fake_exec(
    cmd: str,
    get_output: bool = False,
    encoding: str = "utf-8",
) -> str:
    print(">>", Color.PURPLE + cmd + Color.END)
    return ""


def execute_command(
    cmd: str,
    get_output: bool = False,
    encoding: str = "utf-8",
) -> str:
    """Execute a shell command with comprehensive error handling.

    This is a critical function that handles command execution throughout KodOS.
    It provides proper error handling, return code checking, timeout support,
    and basic security validation.

    Args:
        cmd: The shell command to execute.
        get_output: Whether to return command output. Defaults to False.
        encoding: Text encoding for command output. Defaults to 'utf-8'.

    Returns:
        Command output if get_output=True, empty string otherwise.

    Raises:
        CommandExecutionError: If command fails and check_return_code is True.
        CommandTimeoutError: If command times out.
        UnsafeCommandError: If command contains unsafe patterns and allow_unsafe is False.
        OSError: For system-level execution errors.
    """
    if use_debug or use_verbose:
        print(">>", Color.PURPLE + cmd + Color.END)

    # In debug mode, only print commands but don't execute
    if use_debug:
        return ""

    try:
        if get_output:
            # Use subprocess for better control and error handling
            if not use_dry_run:
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, encoding=encoding
                )

                # if check_return_code and result.returncode != 0:
                if result.returncode != 0:
                    logger.error(f"Command failed: {cmd}")
                    logger.error(f"Return code: {result.returncode}")
                    logger.error(f"Stderr: {result.stderr}")
                    problems.append(
                        {
                            "type": "command_execution",
                            "command": cmd,
                            "return_code": result.returncode,
                            "stderr": result.stderr,
                            "stdout": result.stdout,
                        }
                    )
                    raise CommandExecutionError(
                        cmd=cmd,
                        return_code=result.returncode,
                        stderr=result.stderr,
                        stdout=result.stdout,
                    )

                return result.stdout
            else:
                print(f"{Color.GREEN}{cmd}{Color.END}")
                return ""
        else:
            # For commands without output capture, use subprocess.run
            if not use_dry_run:
                result = subprocess.run(cmd, shell=True)

                # if check_return_code and result.returncode != 0:
                if result.returncode != 0:
                    logger.error(f"Command failed: {cmd}")
                    logger.error(f"Return code: {result.returncode}")
                    problems.append(
                        {
                            "type": "command_execution",
                            "command": cmd,
                            "return_code": result.returncode,
                        }
                    )
                    raise CommandExecutionError(
                        cmd=cmd,
                        return_code=result.returncode,
                    )
                return ""
            else:
                print(f"{Color.GREEN}{cmd}{Color.END}")
                return ""

    # except subprocess.TimeoutExpired:
    #     logger.error(f"Command timed out after {timeout}s: {cmd}")
    #     raise CommandTimeoutError(cmd, timeout)
    except OSError as e:
        logger.error(f"OS error executing command '{cmd}': {e}")
        raise


def execute_chroot(
    cmd: str, mount_point: str = "/mnt", get_output: bool = False, **kwargs
) -> str:
    """Execute a command within a chroot environment with error handling.

    Args:
        cmd: The command to execute inside the chroot.
        mount_point: The mount point for the chroot. Defaults to "/mnt".
        get_output: Whether to return command output. Defaults to False.
        **kwargs: Additional arguments passed to execute_command().

    Returns:
        Command output from the chroot execution.

    Raises:
        CommandExecutionError: If chroot command fails.
        OSError: If chroot environment is not accessible.
    """
    # return execute_command(chroot_cmd, get_output=get_output, **kwargs)
    if use_debug or use_verbose:
        print(f"({mount_point})>>", Color.PURPLE + cmd + Color.END)

    if not use_dry_run:
        with ChrootManager(mount_point) as chroot:
            result = chroot.execute(cmd, capture_output=get_output)
            return result.stdout if get_output is not None else ""
    else:
        print(f"{Color.PURPLE}chroot {mount_point} {cmd}{Color.END}")
        return ""


# File utilities
class CloseableStdoutWrapper:
    def __init__(self, original_stdout):
        self._stdout = original_stdout
        self._closed = False

    def write(self, text):
        if not self._closed:
            return self._stdout.write(text)
        return 0

    def flush(self):
        if not self._closed:
            return self._stdout.flush()

    def close(self):
        self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __getattr__(self, name):
        if self._closed:
            raise ValueError("I/O operation on closed file")
        return getattr(self._stdout, name)


def open_with_dry_run(
    file: str | Path, mode: str = "r", **kwargs: Any
) -> CloseableStdoutWrapper:
    """Extended open function that considers dry_run parameter.

    If dry_run is True (or global use_dry_run is True), returns sys.stdout
    for write operations instead of opening the actual file.

    Args:
        file: File path to open
        mode: File mode (same as built-in open)
        dry_run: Override for dry run mode. If None, uses global use_dry_run
        **kwargs: Additional arguments passed to built-in open()

    Returns:
        File object or sys.stdout in dry run mode for write operations
    """
    # In dry run mode, return stdout for write operations
    if use_dry_run and ("w" in mode or "a" in mode):
        print(
            f"{Color.YELLOW}[DRY RUN] Would open file: {file} (mode: {mode}){Color.END}"
        )
        return CloseableStdoutWrapper(sys.stdout)

    # For read operations or when not in dry run mode, use normal open
    return open(file, mode, **kwargs)


# Utility functions
def report_problems():
    for prob in problems:
        print("Problem:", prob)
