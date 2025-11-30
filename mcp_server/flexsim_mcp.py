#!/usr/bin/env python3
"""MCP Server for FlexSim simulation control.

Provides tools to control FlexSim simulations through the Model Context Protocol (MCP).
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, field_validator

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "utility"))

from config import get_config
from utility import suppress_stderr, force_exit

# ============================================================================
# Logging Configuration
# ============================================================================

log_file = Path(__file__).parent / "flexsim_mcp.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file, mode='w'),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

logger.info("FlexSim MCP Server starting...")
logger.info(f"Python: {sys.version}")

# ============================================================================
# FlexSimPy Import
# ============================================================================

FlexSimPy = None
try:
    import FlexSimPy
    logger.info("FlexSimPy module loaded")
except ImportError as e:
    logger.error(f"FlexSimPy not available: {e}")

# ============================================================================
# Global State
# ============================================================================

_controller = None
_controller_lock = asyncio.Lock()

# ============================================================================
# Input Models
# ============================================================================


class OpenModelInput(BaseModel):
    """Input for opening a model."""
    model_path: str = Field(..., min_length=1)

    @field_validator("model_path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        path = Path(v)
        if path.suffix.lower() not in [".fsm", ".fsx"]:
            raise ValueError("Model must be .fsm or .fsx file")
        if not path.exists():
            raise ValueError(f"File not found: {v}")
        return str(path.resolve())


class RunToTimeInput(BaseModel):
    """Input for running to a specific time."""
    target_time: float = Field(..., gt=0)
    fast_mode: bool = Field(default=False)


class EvaluateScriptInput(BaseModel):
    """Input for evaluating FlexScript."""
    script: str = Field(..., min_length=1, max_length=10000)


class NodeAccessInput(BaseModel):
    """Input for node operations."""
    node_path: str = Field(..., min_length=1)
    value: Any | None = Field(default=None)


class SaveModelInput(BaseModel):
    """Input for saving model."""
    save_path: str | None = Field(default=None)


class StepInput(BaseModel):
    """Input for stepping simulation."""
    steps: int = Field(default=1, ge=1, le=1000)


class ExportResultsInput(BaseModel):
    """Input for exporting results."""
    export_path: str = Field(...)
    format: str = Field(default="csv")

# ============================================================================
# Helper Functions
# ============================================================================


def format_time(seconds: float) -> str:
    """Format simulation time as human-readable string."""
    if seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        return f"{seconds/60:.2f}m"
    else:
        return f"{seconds/3600:.2f}h"


def format_error(e: Exception) -> str:
    """Format exception as user-friendly error message."""
    msg = str(e)
    if "not found" in msg.lower():
        return f"Not found: {msg}"
    elif "syntax" in msg.lower():
        return f"FlexScript syntax error: {msg}"
    elif "license" in msg.lower():
        return f"License error: {msg}"
    elif "permission" in msg.lower():
        return f"Permission denied: {msg}"
    return f"Error: {msg}"

# ============================================================================
# Controller Management
# ============================================================================


async def get_controller():
    """Get or create the FlexSim controller instance."""
    global _controller

    async with _controller_lock:
        if _controller is None:
            _controller = await launch_flexsim()
        return _controller


def launch_flexsim_sync():
    """Launch FlexSim synchronously (called in thread executor)."""
    if FlexSimPy is None:
        raise RuntimeError("FlexSimPy module not available")

    config = get_config()
    program_dir = config.flexsim_install_path

    # Try alternative paths if primary not found
    if not Path(program_dir).exists():
        for alt_path in config.flexsim_alternative_paths:
            if Path(alt_path).exists():
                program_dir = alt_path
                break
        else:
            raise FileNotFoundError(
                f"FlexSim not found at {program_dir}. "
                "Update config.toml with correct path."
            )

    logger.info(f"Launching FlexSim from: {program_dir}")

    # Suppress stderr to hide CEF subprocess errors
    suppress_stderr()

    controller = FlexSimPy.launch(
        programDir=program_dir,
        showGUI=True,
        evaluationLicense=True,
    )

    logger.info("FlexSim launched successfully")
    return controller


async def launch_flexsim():
    """Launch FlexSim asynchronously."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, launch_flexsim_sync)

# ============================================================================
# Lifespan Management
# ============================================================================


@asynccontextmanager
async def lifespan(app):
    """Manage FlexSim lifecycle."""
    logger.info("Server starting up...")
    logger.info("FlexSim will launch when first tool is called (lazy initialization)")
    yield
    logger.info("Server shutting down...")
    if _controller:
        logger.info("FlexSim window will remain open")

# ============================================================================
# MCP Server Setup
# ============================================================================

mcp = FastMCP("flexsim_mcp", lifespan=lifespan)

# ============================================================================
# Core Tools
# ============================================================================


@mcp.tool()
async def flexsim_open_model(params: OpenModelInput) -> str:
    """Open a FlexSim model file.

    Args:
        model_path: Path to .fsm or .fsx file

    Example:
        model_path="C:/Models/warehouse.fsm"
    """
    try:
        controller = await get_controller()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, controller.open, params.model_path)

        model_name = Path(params.model_path).stem
        time = controller.time()

        return f"✓ Opened: {model_name}\nTime: {format_time(time)}"
    except Exception as e:
        return format_error(e)


@mcp.tool()
async def flexsim_reset() -> str:
    """Reset simulation to initial state (time = 0)."""
    try:
        controller = await get_controller()
        controller.reset()
        return "✓ Simulation reset to time 0"
    except Exception as e:
        return format_error(e)


@mcp.tool()
async def flexsim_run() -> str:
    """Start running the simulation continuously."""
    try:
        controller = await get_controller()
        controller.run()
        return "✓ Simulation running (use flexsim_stop to pause)"
    except Exception as e:
        return format_error(e)


@mcp.tool()
async def flexsim_run_to_time(params: RunToTimeInput) -> str:
    """Run simulation until reaching target time.

    Args:
        target_time: Target simulation time in seconds
        fast_mode: Run at maximum speed (default: True). Set to False for real-time GUI updates.

    Example:
        target_time=3600  # Run for 1 hour
    """
    try:
        controller = await get_controller()
        start = controller.time()

        if start >= params.target_time:
            return f"Already at time {format_time(start)}"

        if params.fast_mode:
            # Fast mode: blocking call at max speed (no GUI updates)
            controller.runToTime(params.target_time)
        else:
            # Real-time mode: set stop time and run with GUI animation
            controller.evaluate(f"setstoptime({params.target_time})")
            controller.run()
            
            # Poll until target time reached or simulation stops
            while True:
                current = controller.time()
                if current >= params.target_time:
                    controller.stop()
                    break
                await asyncio.sleep(0.1)

        end = controller.time()

        mode_str = "fast" if params.fast_mode else "real-time"
        return (
            f"✓ Simulation complete ({mode_str})\n"
            f"Start: {format_time(start)}\n"
            f"End: {format_time(end)}\n"
            f"Duration: {format_time(end - start)}"
        )
    except Exception as e:
        return format_error(e)


@mcp.tool()
async def flexsim_stop() -> str:
    """Stop the running simulation."""
    try:
        controller = await get_controller()
        controller.stop()
        time = controller.time()
        return f"✓ Stopped at {format_time(time)}"
    except Exception as e:
        return format_error(e)


@mcp.tool()
async def flexsim_get_time() -> str:
    """Get current simulation time."""
    try:
        controller = await get_controller()
        time = controller.time()
        return f"Time: {format_time(time)} ({time:.2f}s)"
    except Exception as e:
        return format_error(e)


@mcp.tool()
async def flexsim_step(params: StepInput) -> str:
    """Step through simulation events.

    Args:
        steps: Number of events to step (1-1000, default: 1)

    Example:
        steps=10  # Advance 10 events
    """
    try:
        controller = await get_controller()
        start = controller.time()

        # Use FlexScript step() command since Controller doesn't have native step method
        for _ in range(params.steps):
            controller.evaluate("step()")

        end = controller.time()

        return (
            f"✓ Stepped {params.steps} events\n"
            f"Time: {format_time(start)} → {format_time(end)}"
        )
    except Exception as e:
        return format_error(e)


@mcp.tool()
async def flexsim_evaluate(params: EvaluateScriptInput) -> str:
    """Execute FlexScript code.

    Args:
        script: FlexScript code to evaluate

    Examples:
        script='Model.find("Queue1").subnodes.length'  # Get queue content
        script='getmodeltime()'  # Get simulation time
    """
    try:
        controller = await get_controller()
        result = controller.evaluate(params.script)

        return f"Result: {result}"
    except Exception as e:
        return f"Script error: {format_error(e)}"


@mcp.tool()
async def flexsim_get_node_value(params: NodeAccessInput) -> str:
    """Get value from FlexSim tree node.

    Args:
        node_path: Path to node (e.g., "Model/Queue1/stats/input")
    """
    try:
        controller = await get_controller()
        script = f'getvalue(node("{params.node_path}"))'
        result = controller.evaluate(script)

        return f"{params.node_path} = {result}"
    except Exception as e:
        return format_error(e)


@mcp.tool()
async def flexsim_set_node_value(params: NodeAccessInput) -> str:
    """Set value in FlexSim tree node.

    Args:
        node_path: Path to node
        value: New value to set

    Example:
        node_path="Model/Processor1/variables/processtime"
        value=5.0
    """
    try:
        controller = await get_controller()

        if params.value is None:
            return "Error: No value provided"

        # Build script to set value
        if isinstance(params.value, str):
            script = f'setvalue(node("{params.node_path}"), "{params.value}")'
        else:
            script = f'setvalue(node("{params.node_path}"), {params.value})'

        controller.evaluate(script)

        # Verify
        verify = f'getvalue(node("{params.node_path}"))'
        new_value = controller.evaluate(verify)

        return f"✓ {params.node_path} = {new_value}"
    except Exception as e:
        return format_error(e)


@mcp.tool()
async def flexsim_save_model(params: SaveModelInput) -> str:
    """Save the current model.

    Args:
        save_path: Path to save (optional, uses current if not provided)

    Example:
        save_path="C:/Models/warehouse_v2.fsm"
    """
    try:
        controller = await get_controller()

        if params.save_path:
            script = f'savemodel("{params.save_path}")'
            location = params.save_path
        else:
            script = "savemodel()"
            location = "current location"

        controller.evaluate(script)
        return f"✓ Model saved to {location}"
    except Exception as e:
        return format_error(e)


@mcp.tool()
async def flexsim_new_model() -> str:
    """Create a new blank model."""
    try:
        controller = await get_controller()
        controller.evaluate("newmodel()")
        return "✓ New blank model created"
    except Exception as e:
        return format_error(e)


@mcp.tool()
async def flexsim_compile() -> str:
    """Compile the model (check for FlexScript errors)."""
    try:
        controller = await get_controller()
        result = controller.evaluate("compilemodel()")
        return f"✓ Compilation complete: {result}"
    except Exception as e:
        return format_error(e)


@mcp.tool()
async def flexsim_get_statistics() -> str:
    """Get simulation statistics and performance metrics."""
    try:
        controller = await get_controller()

        stats_script = """
        {
            "time": getmodeltime(),
            "run_speed": get(runspeed()),
            "objects": Model.subnodes.length,
            "events": geteventsprocessed()
        }
        """

        result = controller.evaluate(stats_script)
        return f"Statistics:\n```json\n{result}\n```"
    except Exception as e:
        return format_error(e)


@mcp.tool()
async def flexsim_export_results(params: ExportResultsInput) -> str:
    """Export simulation results to file.

    Args:
        export_path: Path to save results
        format: Export format (csv, xlsx, json)

    Example:
        export_path="C:/Results/output.csv"
        format="csv"
    """
    try:
        controller = await get_controller()

        # Build export script based on format
        fmt = params.format.lower()
        if fmt == "csv":
            script = f'exporttable("{params.export_path}")'
        elif fmt == "xlsx":
            script = f'exportexcel("{params.export_path}")'
        else:
            script = f'exportjson("{params.export_path}")'

        controller.evaluate(script)
        return f"✓ Results exported to {params.export_path}"
    except Exception as e:
        return format_error(e)

# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="FlexSim MCP Server")
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Run in test mode (keeps server alive for manual testing)"
    )
    args = parser.parse_args()

    if args.test_mode:
        # Test mode - keep server alive for manual interaction
        import asyncio

        async def test_mode():
            logger.info("Starting in TEST MODE")
            logger.info("Server will stay alive until Ctrl+C")

            # Launch FlexSim
            controller = await get_controller()
            logger.info("FlexSim launched and ready for testing")
            logger.info("Press Ctrl+C to exit")

            # Keep alive
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                logger.info("Stopped by user")

        try:
            asyncio.run(test_mode())
        except Exception as e:
            logger.error(f"Test mode error: {e}", exc_info=True)
            sys.exit(1)
    else:
        # Normal MCP mode - expects stdin/stdout communication
        try:
            logger.info("Starting MCP server (Ctrl+C to exit)")
            logger.info("Note: This server expects MCP protocol communication via stdin/stdout")
            logger.info("To run standalone for testing, use: --test-mode")
            mcp.run()
        except KeyboardInterrupt:
            logger.info("Stopped by user")
        except Exception as e:
            logger.error(f"Server crashed: {e}", exc_info=True)
            sys.exit(1)
        finally:
            logger.info("Server exiting")
