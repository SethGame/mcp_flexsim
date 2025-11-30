"""Automated build and verification for FlexSimPy module."""

from __future__ import annotations

import logging
import platform
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path
from typing import Any, Literal

from config import get_config

logger = logging.getLogger(__name__)


class FlexSimPyBuilder:
    """Handles FlexSimPy module building and verification."""

    def __init__(self, python_version: str | None = None, auto_build: bool = True):
        """Initialize the FlexSimPy builder.

        Args:
            python_version: Python version to build for (e.g., "3.10"). If None, uses config.
            auto_build: Whether to automatically build if module is missing.
        """
        self.config = get_config()
        self.python_version = python_version or self.config.python_version
        self.auto_build = auto_build
        self.project_root = Path(__file__).parent.parent
        
        # Get flexsimpy_dir from config
        flexsimpy_path = self.config.get("build.flexsimpy_dir", "depends/FlexSimPy")
        self.flexsimpy_dir = self.project_root / flexsimpy_path
        
        self.flexsim_content_dir = self.flexsimpy_dir / "flexsimcontent"

    def check_flexsimpy_available(self) -> tuple[bool, str]:
        """Check if FlexSimPy module is available for import.

        Returns:
            Tuple of (is_available, message)
        """
        try:
            import FlexSimPy

            module_path = getattr(FlexSimPy, "__file__", "unknown")
            logger.info(f"FlexSimPy module found at: {module_path}")
            return True, f"FlexSimPy module available at {module_path}"
        except ImportError as e:
            logger.warning(f"FlexSimPy module not available: {e}")
            return False, f"FlexSimPy module not found: {e}"

    def check_build_output_exists(self) -> tuple[bool, Path | None]:
        """Check if FlexSimPy build output exists.

        Returns:
            Tuple of (exists, path_to_pyd)
        """
        if not self.flexsimpy_dir.exists():
            logger.error(f"FlexSimPy directory not found: {self.flexsimpy_dir}")
            return False, None

        # Check for built .pyd file
        config_name = f"Rel_{self.python_version.replace('.', '_')}"
        output_dir = self.flexsimpy_dir / "out" / config_name
        pyd_file = output_dir / "FlexSimPy.pyd"

        if pyd_file.exists():
            logger.info(f"FlexSimPy build output found: {pyd_file}")
            return True, pyd_file

        logger.warning(f"FlexSimPy build output not found at: {pyd_file}")
        return False, None

    def install_pyd_to_python_path(self, pyd_path: Path) -> bool:
        """Install .pyd file to Python site-packages.

        Args:
            pyd_path: Path to FlexSimPy.pyd file

        Returns:
            True if successful
        """
        try:
            import site

            site_paths = [Path(p) for p in site.getsitepackages()]
            site_packages = next(
                (path for path in site_paths if path.name.lower() == "site-packages"),
                None,
            )

            if site_packages is None:
                user_site = getattr(site, "getusersitepackages", lambda: None)()
                if user_site:
                    candidate = Path(user_site)
                    if candidate.name.lower() == "site-packages":
                        site_packages = candidate

            if site_packages is None:
                platlib = sysconfig.get_path("platlib")
                if platlib:
                    site_packages = Path(platlib)

            if site_packages is None:
                logger.error("Unable to determine site-packages directory for installation")
                return False

            site_packages.mkdir(parents=True, exist_ok=True)
            target = site_packages / "FlexSimPy.pyd"

            if target.exists():
                logger.info(f"FlexSimPy.pyd already in site-packages: {target}")
                return True

            shutil.copy2(pyd_path, target)
            logger.info(f"Installed FlexSimPy.pyd to {target}")
            return True

        except Exception as e:
            logger.error(f"Failed to install FlexSimPy.pyd: {e}")
            return False

    def find_msbuild(self) -> Path | None:
        """Find MSBuild.exe on the system.

        Returns:
            Path to MSBuild.exe or None if not found
        """
        if platform.system() != "Windows":
            logger.error("FlexSimPy build requires Windows")
            return None

        # Common MSBuild locations
        potential_paths = [
            r"C:\Program Files\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\MSBuild.exe",
            r"C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe",
            r"C:\Program Files\Microsoft Visual Studio\2022\Enterprise\MSBuild\Current\Bin\MSBuild.exe",
            r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Professional\MSBuild\Current\Bin\MSBuild.exe",
            r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\MSBuild\Current\Bin\MSBuild.exe",
        ]

        # Check config for custom MSBuild path
        custom_path = self.config.get("build.msbuild_path")
        if custom_path:
            potential_paths.insert(0, custom_path)

        for path_str in potential_paths:
            path = Path(path_str)
            if path.exists():
                logger.info(f"Found MSBuild at: {path}")
                return path

        # Try to find using vswhere
        try:
            result = subprocess.run(
                [
                    r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe",
                    "-latest",
                    "-requires",
                    "Microsoft.Component.MSBuild",
                    "-find",
                    r"MSBuild\**\Bin\MSBuild.exe",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            if result.stdout.strip():
                path = Path(result.stdout.strip().split("\n")[0])
                if path.exists():
                    logger.info(f"Found MSBuild via vswhere: {path}")
                    return path
        except Exception as e:
            logger.debug(f"Could not find MSBuild via vswhere: {e}")

        logger.error("MSBuild.exe not found. Please install Visual Studio 2022 with C++ tools.")
        return None

    def build_flexsimpy(self, force: bool = False) -> tuple[bool, str]:
        """Build FlexSimPy module using MSBuild.

        Args:
            force: Force rebuild even if output exists

        Returns:
            Tuple of (success, message)
        """
        if not force:
            exists, pyd_path = self.check_build_output_exists()
            if exists and pyd_path:
                return True, f"FlexSimPy already built at {pyd_path}"

        # Ensure FlexSim headers and libraries are available before building
        sync_success, sync_msg = self.sync_flexsim_content()
        if not sync_success:
            return False, sync_msg

        logger.info(sync_msg)

        # Find MSBuild
        msbuild = self.find_msbuild()
        if not msbuild:
            return False, "MSBuild not found. Install Visual Studio 2022 with C++ tools."

        # Check solution file exists
        solution_file = self.flexsimpy_dir / "FlexSimPy.sln"
        if not solution_file.exists():
            return False, f"FlexSimPy.sln not found at {solution_file}"

        # Build configuration
        config_name = f"Rel_{self.python_version.replace('.', '_')}"

        try:
            logger.info(f"Building FlexSimPy for Python {self.python_version}...")
            logger.info(f"Configuration: {config_name}")
            logger.info(f"Using MSBuild: {msbuild}")

            # Run MSBuild
            result = subprocess.run(
                [
                    str(msbuild),
                    str(solution_file),
                    f"/p:Platform=x64;Configuration={config_name}",
                    "/t:FlexSimPy",  # Only build FlexSimPy project, not PyConnector
                    "/v:minimal",
                ],
                capture_output=True,
                text=True,
                check=False,
                cwd=str(self.flexsimpy_dir),
            )

            if result.returncode == 0:
                logger.info("FlexSimPy build succeeded")

                # Verify output
                exists, pyd_path = self.check_build_output_exists()
                if exists and pyd_path:
                    return True, f"FlexSimPy built successfully at {pyd_path}"
                else:
                    return False, "Build completed but output file not found"
            else:
                error_msg = f"FlexSimPy build failed with code {result.returncode}"
                if result.stderr:
                    error_msg += f"\n{result.stderr}"
                if result.stdout:
                    logger.error(f"MSBuild output:\n{result.stdout}")
                logger.error(error_msg)
                return False, error_msg

        except Exception as e:
            error_msg = f"Build failed with exception: {e}"
            logger.error(error_msg)
            return False, error_msg

    def ensure_flexsimpy_available(
        self, mode: Literal["check", "build", "install"] = "install"
    ) -> tuple[bool, str]:
        """Ensure FlexSimPy module is available.

        Args:
            mode: Operation mode:
                - "check": Only check if available
                - "build": Check, and build if missing
                - "install": Check, build if missing, and install to site-packages

        Returns:
            Tuple of (success, message)
        """
        # First check if already available
        is_available, msg = self.check_flexsimpy_available()
        if is_available:
            return True, msg

        if mode == "check":
            return False, "FlexSimPy not available and mode is 'check'"

        # Check if build output exists
        exists, pyd_path = self.check_build_output_exists()

        if not exists:
            if not self.auto_build:
                return (
                    False,
                    "FlexSimPy not built and auto_build is disabled. "
                    "Run with --build-flexsimpy to build.",
                )

            # Build it
            logger.info("FlexSimPy not found, attempting to build...")
            success, build_msg = self.build_flexsimpy()
            if not success:
                return False, f"Failed to build FlexSimPy: {build_msg}"

            # Check again for output
            exists, pyd_path = self.check_build_output_exists()
            if not exists or not pyd_path:
                return False, "Build succeeded but output not found"

        # If mode is install, install to site-packages
        if mode == "install" and pyd_path:
            if self.install_pyd_to_python_path(pyd_path):
                return True, f"FlexSimPy installed to site-packages from {pyd_path}"
            else:
                return (
                    False,
                    f"FlexSimPy built at {pyd_path} but failed to install to site-packages. "
                    f"Add {pyd_path.parent} to PYTHONPATH manually.",
                )

        return True, f"FlexSimPy available at {pyd_path}"

    def get_build_status(self) -> dict[str, Any]:
        """Get comprehensive build status information.

        Returns:
            Dictionary with status information
        """
        status = {
            "python_version": self.python_version,
            "project_root": str(self.project_root),
            "flexsimpy_dir": str(self.flexsimpy_dir),
            "flexsimpy_dir_exists": self.flexsimpy_dir.exists(),
        }

        # Check if module is importable
        is_available, msg = self.check_flexsimpy_available()
        status["module_available"] = is_available
        status["module_message"] = msg

        # Check build output
        exists, pyd_path = self.check_build_output_exists()
        status["build_output_exists"] = exists
        status["build_output_path"] = str(pyd_path) if pyd_path else None

        # Check MSBuild
        msbuild = self.find_msbuild()
        status["msbuild_available"] = msbuild is not None
        status["msbuild_path"] = str(msbuild) if msbuild else None

        return status

    def resolve_flexsim_install_path(self) -> Path | None:
        """Resolve FlexSim installation path from configuration."""
        candidates: list[str] = []
        primary_path = getattr(self.config, "flexsim_install_path", "")
        if primary_path:
            candidates.append(primary_path)

        alternative_paths = getattr(self.config, "flexsim_alternative_paths", [])
        if alternative_paths:
            candidates.extend(alternative_paths)

        # Remove duplicates while preserving order
        seen: set[str] = set()
        unique_candidates = []
        for path_str in candidates:
            if path_str and path_str not in seen:
                seen.add(path_str)
                unique_candidates.append(path_str)

        for path_str in unique_candidates:
            resolved = Path(path_str).expanduser()
            
            # If path is relative, make it relative to project root
            if not resolved.is_absolute():
                resolved = self.project_root / resolved
            
            if resolved.exists():
                return resolved

        return None

    def sync_flexsim_content(self) -> tuple[bool, str]:
        """Copy required FlexSim headers and libraries into the build tree."""
        install_path = self.resolve_flexsim_install_path()
        if not install_path:
            return False, (
                "FlexSim install path not found. Configure flexsim.install_path "
                "or flexsim.alternative_paths in config.toml."
            )

        include_dir = install_path / "system" / "include"
        lib_dir = install_path / "system" / "lib"

        if not include_dir.exists():
            return False, f"FlexSim include directory not found: {include_dir}"

        # Prepare destination directory
        try:
            self.flexsim_content_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            return False, f"Failed to create flexsimcontent directory: {exc}"

        copied_files: list[Path] = []

        # Copy include files recursively
        try:
            for item in include_dir.iterdir():
                destination = self.flexsim_content_dir / item.name
                if item.is_dir():
                    shutil.copytree(item, destination, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, destination)
                copied_files.append(destination)
        except Exception as exc:
            return False, f"Failed to copy FlexSim include files: {exc}"

        # Copy required libraries
        library_sources = {
            "flexsim.lib": lib_dir,
            "flexsim_x86.lib": lib_dir,
            "flexsimcontent.lib": include_dir,
            "flexsimcontent_x86.lib": include_dir,
        }

        for lib_name, source_dir in library_sources.items():
            lib_path = source_dir / lib_name
            if lib_path.exists():
                try:
                    destination = self.flexsim_content_dir / lib_name
                    shutil.copy2(lib_path, destination)
                    copied_files.append(destination)
                except Exception as exc:
                    return False, f"Failed to copy {lib_name}: {exc}"

        if not copied_files:
            return False, (
                "No FlexSim headers or libraries were copied. Verify the FlexSim "
                f"installation at {install_path} contains the required files."
            )

        return True, (
            f"Synchronized FlexSim headers and libraries from {install_path} "
            f"into {self.flexsim_content_dir}"
        )


def print_build_status():
    """Print build status to console (for CLI usage)."""
    builder = FlexSimPyBuilder()
    status = builder.get_build_status()

    # Use ASCII characters for better Windows console compatibility
    yes = "[YES]"
    no = "[NO]"

    print("\n=== FlexSimPy Build Status ===\n")
    print(f"Python Version:         {status['python_version']}")
    print(f"Project Root:           {status['project_root']}")
    print(f"FlexSimPy Directory:    {status['flexsimpy_dir']}")
    print(f"Directory Exists:       {yes if status['flexsimpy_dir_exists'] else no}")
    print(f"\nModule Available:       {yes if status['module_available'] else no}")
    print(f"Message:                {status['module_message']}")
    print(f"\nBuild Output Exists:    {yes if status['build_output_exists'] else no}")
    if status["build_output_path"]:
        print(f"Build Output Path:      {status['build_output_path']}")
    print(f"\nMSBuild Available:      {yes if status['msbuild_available'] else no}")
    if status["msbuild_path"]:
        print(f"MSBuild Path:           {status['msbuild_path']}")
    print()


if __name__ == "__main__":
    # CLI for build automation
    import argparse

    parser = argparse.ArgumentParser(description="FlexSimPy Build Automation")
    parser.add_argument("--status", action="store_true", help="Show build status")
    parser.add_argument("--build", action="store_true", help="Build FlexSimPy", default=True)
    parser.add_argument("--install", action="store_true", help="Build and install FlexSimPy", default=True)
    parser.add_argument("--force", action="store_true", help="Force rebuild", default=True)
    parser.add_argument("--python-version", type=str, help="Python version (e.g., 3.10)", default="3.10")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    builder = FlexSimPyBuilder(python_version=args.python_version)

    exit_code = 0
    actions_run = False

    if args.install:
        actions_run = True
        success, msg = builder.ensure_flexsimpy_available(mode="install")
        print(msg)
        if not success:
            exit_code = 1

    if args.build and not args.install:
        actions_run = True
        success, msg = builder.build_flexsimpy(force=args.force)
        print(msg)
        if not success:
            exit_code = 1

    if args.status or not actions_run:
        print_build_status()

    sys.exit(exit_code)
