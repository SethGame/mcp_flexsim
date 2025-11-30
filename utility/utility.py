"""Utility functions for FlexSim MCP Server."""

import os
import sys

import psutil


def suppress_stderr():
    """Suppress stderr to hide CEF subprocess error messages.

    CEF (Chromium Embedded Framework) tries to launch helper processes
    by relaunching the parent executable with flags like --type=gpu-process.
    When FlexSim is launched from Python, CEF incorrectly tries to launch
    python.exe as helper processes, causing "unknown option" errors.

    This function redirects stderr to devnull to keep the console clean
    while FlexSim GUI is running.

    Returns:
        int: File descriptor for the saved stderr (to restore later if needed)

    Note:
        Only works on Windows. Returns -1 on other platforms.
    """
    if os.name != "nt":
        return -1

    # Save original stderr
    original_stderr = sys.stderr.fileno()
    saved_stderr = os.dup(original_stderr)

    # Redirect stderr to NUL
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, original_stderr)
    os.close(devnull)

    return saved_stderr


def restore_stderr(saved_stderr: int):
    """Restore stderr to its original file descriptor.

    Args:
        saved_stderr: File descriptor returned by suppress_stderr()
    """
    if saved_stderr < 0:
        return

    original_stderr = sys.stderr.fileno()
    os.dup2(saved_stderr, original_stderr)
    os.close(saved_stderr)


def kill_flexsim_processes() -> list[int]:
    """Kill all FlexSim.exe processes.

    Returns:
        List of process IDs that were killed
    """
    killed = []
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if proc.info["name"] and "flexsim" in proc.info["name"].lower():
                proc.kill()
                killed.append(proc.info["pid"])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return killed


def force_exit() -> None:
    """Force exit to avoid segfault during Python cleanup.

    FlexSimPy module has issues with proper shutdown that cause
    segmentation faults during normal Python cleanup.
    """
    os._exit(0)
