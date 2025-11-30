#!/usr/bin/env python
"""Copy FlexSim installation from src_path to FlexSimDev directory."""

import argparse
import os
import shutil
import sys
from pathlib import Path

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent))

from config import get_config


def copy_with_retry(src, dst, *, follow_symlinks=True):
    """Copy file with retry on permission errors."""
    try:
        shutil.copy2(src, dst, follow_symlinks=follow_symlinks)
    except (PermissionError, OSError) as e:
        # Skip files we can't copy (e.g., locked files)
        print(f"  Skipping {src.name}: {e}")


def copy_flexsim(force=False):
    """Copy FlexSim installation to FlexSimDev directory.
    
    Args:
        force: If True, overwrite existing directory without asking
    """
    config = get_config()
    
    # Get src_path from config
    src_path_str = config.get("flexsim.src_path")
    if not src_path_str:
        print("ERROR: flexsim.src_path not found in config.toml")
        return False
    
    src_path = Path(src_path_str)
    if not src_path.exists():
        print(f"ERROR: Source path does not exist: {src_path}")
        return False
    
    # Destination is FlexSimDev in repo root
    repo_root = Path(__file__).parent.parent
    dst_path = repo_root / "FlexSimDev"
    
    print(f"Source:      {src_path}")
    print(f"Destination: {dst_path}")
    print(f"\nThis will copy the entire FlexSim installation.")
    print(f"This may take several minutes...")
    
    # Check if destination already exists
    if dst_path.exists():
        if not force:
            response = input(f"\nDestination directory already exists. Overwrite? (y/n): ")
            if response.lower() != 'y':
                print("Copy cancelled.")
                return False
        print(f"Removing existing directory...")
        try:
            shutil.rmtree(dst_path, ignore_errors=True)
        except Exception as e:
            print(f"Warning: Could not remove some files: {e}")
    
    print(f"\nCopying files...")
    copied_files = 0
    skipped_files = 0
    
    try:
        # Use copytree with ignore_errors and custom copy function
        def copy_function(src, dst, *, follow_symlinks=True):
            nonlocal copied_files, skipped_files
            try:
                shutil.copy2(src, dst, follow_symlinks=follow_symlinks)
                copied_files += 1
                if copied_files % 100 == 0:
                    print(f"  Copied {copied_files} files...", end='\r')
            except (PermissionError, OSError) as e:
                skipped_files += 1
        
        shutil.copytree(
            src_path, 
            dst_path, 
            copy_function=copy_function,
            ignore_dangling_symlinks=True,
            dirs_exist_ok=True
        )
        
        print(f"\n✓ Copy complete!")
        print(f"  FlexSim installed to: {dst_path}")
        print(f"  Files copied: {copied_files}")
        if skipped_files > 0:
            print(f"  Files skipped: {skipped_files}")
        return True
    except Exception as e:
        print(f"\n✗ Copy failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Copy FlexSim installation")
    parser.add_argument("--force", "-f", action="store_true", 
                        help="Overwrite existing directory without asking")
    args = parser.parse_args()
    
    success = copy_flexsim(force=args.force)
    sys.exit(0 if success else 1)

