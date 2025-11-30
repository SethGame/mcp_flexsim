#!/usr/bin/env python
"""Integration test script for FlexSim with GUI.

Simple synchronous version that works reliably.
Usage: python integration_test.py
"""

import sys
import time
from pathlib import Path
import os
from typing import Optional

# Ensure FlexSimPy is available
sys.path.insert(0, str(Path(__file__).parent))

from config import get_config
from utility import force_exit, kill_flexsim_processes, suppress_stderr

# Suppress CEF subprocess error messages (stderr from failed python.exe launches)
# These happen because CEF tries to launch python.exe as helper processes
suppress_stderr()

import FlexSimPy


def resolve_program_dir() -> Path:
    """Find a FlexSim program directory that exists on disk."""
    candidates: list[Path] = []
    project_root = Path(__file__).parent.parent

    try:
        config_install = get_config().flexsim_install_path
        if config_install:
            candidate = Path(config_install)
            # If relative path, make it relative to project root
            if not candidate.is_absolute():
                candidate = project_root / candidate
            candidates.append(candidate)
    except Exception:
        pass

    # Project-local fallback (used in dev checkouts)
    candidates.append(project_root.parent.parent / "program")

    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate

    searched = "\n   - ".join(str(c) for c in candidates)
    raise FileNotFoundError(
        "Unable to locate FlexSim program directory. Checked paths:\n   - " + searched
    )



def test_flexsim_gui():
    """Interactive test of FlexSim with GUI."""
    print("\n" + "=" * 60)
    print("FlexSim GUI Integration Test")
    print("=" * 60)

    print("\n[LAUNCH] Launching FlexSim with GUI...")

    program_dir = resolve_program_dir()
    print(f"   Using program directory: {program_dir}")

    # Launch FlexSim
    controller = FlexSimPy.launch(
        programDir=str(program_dir),
        showGUI=True,
        evaluationLicense=True,
    )

    print("[OK] FlexSim launched successfully!")
    print(f"   Controller: {controller}")

    # Try different model paths
    model_paths = [
        # Local project example
        Path(__file__).parent.parent / "examples" / "HelloWorld_1.fsm",
        # Built-in FlexSim example
        Path(r"C:\Program Files\FlexSim 2025 Update 2\program\Examples\HelloWorld_1.fsm"),
    ]

    model_path = None
    for path in model_paths:
        if path.exists():
            model_path = path
            break

    if not model_path:
        print("[WARN] No model file found!")
        print("   Checked paths:")
        for path in model_paths:
            print(f"   - {path}")
    else:
        print(f"\n[OPEN] Opening model: {model_path.name}")
        print(f"   Full path: {model_path}")

        controller.open(str(model_path.resolve()))
        print("[OK] Model opened successfully!")

    # Get current simulation time
    sim_time = controller.time()
    print(f"\n[TIME] Current simulation time: {sim_time}")

    # Interactive menu
    while True:
        print("\n" + "-" * 40)
        print("Choose an action:")
        print("1. Reset simulation")
        print("2. Run simulation for 100 time units")
        print("3. Stop simulation")
        print("4. Get current time")
        print("5. Run to specific time")
        print("6. Evaluate FlexScript")
        print("Q. Quit")
        print("-" * 40)

        choice = input("Enter choice: ").strip().upper()

        if choice == "1":
            print("[RESET] Resetting simulation...")
            controller.reset()
            print("[OK] Reset complete!")

        elif choice == "2":
            print("[RUN] Running simulation for 100 time units...")
            controller.run()
            time.sleep(2)  # Let it run
            controller.stop()
            new_time = controller.time()
            print(f"[OK] Simulation stopped at time: {new_time}")

        elif choice == "3":
            print("[STOP] Stopping simulation...")
            controller.stop()
            print("[OK] Stopped!")

        elif choice == "4":
            current_time = controller.time()
            print(f"[TIME] Current simulation time: {current_time}")

        elif choice == "5":
            target = input("Enter target time: ").strip()
            try:
                target_time = float(target)
                print(f"[>>] Running to time {target_time}...")
                controller.runToTime(target_time)
                print(f"[OK] Reached time: {controller.time()}")
            except ValueError:
                print("[ERROR] Invalid time value!")

        elif choice == "6":
            script = input("Enter FlexScript code: ").strip()
            if script:
                print(f"[EVAL] Evaluating: {script}")
                result = controller.evaluate(script)
                print(f"[OUT] Result: {result}")

        elif choice == "Q":
            print("\n[BYE] Exiting... (FlexSim will remain open)")
            break

        else:
            print("[ERROR] Invalid choice!")

    print("\n[INFO] FlexSim window will remain open.")
    print("    Close it manually when done.")

    return controller


if __name__ == "__main__":
    controller: Optional[FlexSimPy.Controller] = None
    try:
        controller = test_flexsim_gui()
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        auto_close = os.environ.get("FLEXSIM_AUTO_CLOSE", "1").lower() not in {"0", "false", "no"}
        if auto_close:
            killed = kill_flexsim_processes()
            if killed:
                print(f"[CLEANUP] Terminated FlexSim processes: {', '.join(map(str, killed))}")
            else:
                print("[CLEANUP] No FlexSim processes found.")

        if os.environ.get("FLEXSIM_FORCE_EXIT", "1").lower() not in {"0", "false", "no"}:
            print("[CLEANUP] Forcing interpreter exit to avoid FlexSimPy shutdown issues.")
            force_exit()
