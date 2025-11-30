#!/usr/bin/env python3
"""Guided setup script for the FlexSim MCP server."""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parent
UTILITY_DIR = PROJECT_ROOT / "utility"

# Ensure local utilities are importable
sys.path.insert(0, str(UTILITY_DIR))

from config import get_config  # type: ignore  # noqa: E402
from copy_flexsim import copy_flexsim  # type: ignore  # noqa: E402


def print_header() -> None:
    line = "=" * 70
    print(line)
    print("FlexSim MCP Server Setup")
    print(line)


def prompt_yes_no(question: str, default: bool = True) -> bool:
    """Prompt for a yes/no response."""
    suffix = " [Y/n]: " if default else " [y/N]: "
    while True:
        reply = input(question + suffix).strip().lower()
        if not reply:
            return default
        if reply in {"y", "yes"}:
            return True
        if reply in {"n", "no"}:
            return False
        print("Please answer with 'y' or 'n'.")


def run_command(args: Iterable[str]) -> bool:
    """Run a subprocess command and report success."""
    command = list(args)
    print(f"> {' '.join(command)}")
    try:
        subprocess.run(command, check=True)
        return True
    except subprocess.CalledProcessError as exc:
        print(f"Command failed with exit code {exc.returncode}")
        return False


def ensure_uv() -> bool:
    """Ensure the uv package manager is installed."""
    if shutil.which("uv"):
        print("uv is already available.")
        return True

    print("uv is not on PATH. Attempting installation...")
    system = platform.system()

    if system == "Windows":
        powershell_cmd = (
            "irm https://astral.sh/uv/install.ps1 | iex"
        )
        succeeded = run_command(
            [
                "powershell",
                "-ExecutionPolicy",
                "ByPass",
                "-NoProfile",
                "-Command",
                powershell_cmd,
            ]
        )
    else:
        succeeded = run_command(
            [
                "sh",
                "-c",
                "curl -LsSf https://astral.sh/uv/install.sh | sh",
            ]
        )

    if succeeded and shutil.which("uv"):
        print("uv installation complete.")
        return True

    print("Failed to install uv automatically. Install it manually and rerun this script.")
    return False


def display_config_summary() -> None:
    """Show key configuration values and filesystem state."""
    config = get_config()
    config_path = getattr(config, "_config_path", None)
    print("\nConfiguration summary")
    print("---------------------")
    if config_path:
        print(f"config.toml: {config_path}")
    else:
        print("config.toml: not found (using defaults)")

    flexsim_install = Path(config.flexsim_install_path)
    resolved_install = (
        flexsim_install
        if flexsim_install.is_absolute()
        else (PROJECT_ROOT / flexsim_install)
    )
    print(f"flexsim.install_path: {flexsim_install}  (exists: {resolved_install.exists()})")

    flexsim_src = config.get("flexsim.src_path")
    if flexsim_src:
        print(f"flexsim.src_path:      {flexsim_src}  (exists: {Path(flexsim_src).exists()})")
    else:
        print("flexsim.src_path:      not set")

    python_version = config.get("python.version", "3.10")
    print(f"python.version:        {python_version}")

    flexsimpy_rel = config.get("build.flexsimpy_dir", "depends/FlexSimPy")
    flexsimpy_path = PROJECT_ROOT / flexsimpy_rel
    print(f"FlexSimPy source:      {flexsimpy_path}  (exists: {flexsimpy_path.exists()})")

    flexsim_dev = PROJECT_ROOT / "FlexSimDev" / "program"
    print(f"FlexSimDev/program:    {flexsim_dev}  (exists: {flexsim_dev.exists()})")


def choose_python_version(default_version: str) -> str:
    """Allow the user to confirm or override the Python version."""
    prompt = f"Use Python {default_version} for FlexSimPy builds?"
    if prompt_yes_no(prompt, default=True):
        return default_version

    while True:
        override = input("Enter desired Python version (e.g., 3.12): ").strip()
        if override:
            return override
        print("Please provide a version such as 3.10, 3.11, or 3.12.")


def run_uv_sync() -> bool:
    """Run uv sync from the project root."""
    print("\nSynchronizing project environment with uv...")
    return run_command(["uv", "sync"])


def build_flexsimpy(python_version: str) -> bool:
    """Build and install FlexSimPy via the automation script."""
    print("\nBuilding FlexSimPy...")
    script = PROJECT_ROOT / "utility" / "build_automation.py"
    return run_command(
        [
            "uv",
            "run",
            "python",
            str(script),
            "--python-version",
            python_version,
        ]
    )


def maybe_run_integration_test() -> None:
    """Offer to run the GUI integration test."""
    if not prompt_yes_no("\nRun the GUI integration test now?", default=False):
        return
    script = PROJECT_ROOT / "utility" / "integration_test.py"
    print("\nStarting integration test (this launches FlexSim)...")
    success = run_command(["uv", "run", "python", str(script)])
    if success:
        print("Integration test finished.")
    else:
        print("Integration test failed or was interrupted.")


def show_mcp_instructions() -> None:
    """Print next steps for configuring the MCP server."""
    print("\nMCP server usage")
    print("----------------")
    print("1. Launch the server in test mode to verify tools:")
    print("   uv run mcp_server/flexsim_mcp.py --test-mode")
    print("2. For stdio clients, run without --test-mode and connect via MCP protocol.")
    config_path = PROJECT_ROOT / "mcp_server_config.json"
    if config_path.exists():
        print(f"3. Client configuration lives at: {config_path}")
        print("   Copy the flexsim entry into your MCP client (Cursor, Claude, etc.).")
    else:
        print("3. Generate an MCP client config referencing uv run mcp_server/flexsim_mcp.py.")
    print("4. Run end-to-end checks any time with:")
    print("   uv run python tests/integration/test_mcp_client.py")


def main() -> None:
    print_header()
    display_config_summary()

    print("\nStep 1: FlexSim content")
    if prompt_yes_no("Copy FlexSim into FlexSimDev using utility/copy_flexsim.py?", default=False):
        copy_success = copy_flexsim(force=False)
        if not copy_success:
            print("FlexSim copy step did not complete successfully.")
        else:
            print("FlexSim assets copied.")

    print("\nStep 2: uv environment")
    if not ensure_uv():
        sys.exit(1)
    if not run_uv_sync():
        print("uv sync failed. Resolve the issue and rerun this script.")
        sys.exit(1)

    print("\nStep 3: FlexSimPy build")
    default_version = get_config().get("python.version", "3.10")
    build_version = choose_python_version(default_version)
    if not build_flexsimpy(build_version):
        print("FlexSimPy build failed. Review build logs and rerun as needed.")
    else:
        print("FlexSimPy build completed.")

    print("\nStep 4: Optional integration test")
    maybe_run_integration_test()

    show_mcp_instructions()
    print("\nSetup helper finished.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSetup interrupted by user.")
