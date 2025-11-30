#!/usr/bin/env python3
"""Integration test client for FlexSim MCP Server.

Tests the MCP server via stdio communication by:
1. Starting the server as a subprocess
2. Sending MCP protocol messages
3. Testing the flexsim_open_model tool
"""

import asyncio
import json
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "utility"))

from config import get_config


class MCPClient:
    """Simple MCP client for testing stdio communication."""

    def __init__(self, server_script: str):
        self.server_script = server_script
        self.process = None
        self.message_id = 0

    async def start(self):
        """Start the MCP server as subprocess."""
        print(f"Starting MCP server: {self.server_script}")

        self.process = await asyncio.create_subprocess_exec(
            sys.executable,
            self.server_script,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        print(f"Server started with PID: {self.process.pid}")
        # Give server time to initialize
        await asyncio.sleep(2)

    async def send_message(self, method: str, params: dict = None) -> dict:
        """Send JSON-RPC message to server and read response."""
        self.message_id += 1

        message = {
            "jsonrpc": "2.0",
            "id": self.message_id,
            "method": method,
        }

        if params:
            message["params"] = params

        # Send message
        message_str = json.dumps(message) + "\n"
        print(f"\n→ Sending: {message_str.strip()}")

        self.process.stdin.write(message_str.encode())
        await self.process.stdin.drain()

        # Read response
        response_line = await self.process.stdout.readline()

        if not response_line:
            raise Exception("No response from server")

        response = json.loads(response_line.decode())
        print(f"← Received: {json.dumps(response, indent=2)}")

        return response

    async def initialize(self):
        """Initialize MCP session."""
        print("\n=== Initializing MCP Session ===")
        response = await self.send_message(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        )

        print(f"Server capabilities: {response.get('result', {}).get('capabilities')}")

        # Send initialized notification
        await self.send_notification("notifications/initialized")

        return response

    async def send_notification(self, method: str, params: dict = None):
        """Send notification (no response expected)."""
        message = {
            "jsonrpc": "2.0",
            "method": method,
        }

        if params:
            message["params"] = params

        message_str = json.dumps(message) + "\n"
        print(f"→ Notification: {message_str.strip()}")

        self.process.stdin.write(message_str.encode())
        await self.process.stdin.drain()

    async def list_tools(self):
        """List available tools."""
        print("\n=== Listing Available Tools ===")
        response = await self.send_message("tools/list")

        tools = response.get("result", {}).get("tools", [])
        print(f"\nFound {len(tools)} tools:")
        for tool in tools:
            print(f"  - {tool['name']}: {tool.get('description', 'No description')[:80]}")

        return tools

    async def call_tool(self, tool_name: str, arguments: dict = None):
        """Call a tool."""
        print(f"\n=== Calling Tool: {tool_name} ===")

        params = {"name": tool_name}
        if arguments:
            # Wrap arguments in params for FastMCP format
            params["arguments"] = {"params": arguments}

        response = await self.send_message("tools/call", params)

        result = response.get("result")
        if result:
            content = result.get("content", [])
            for item in content:
                if item.get("type") == "text":
                    print(f"Tool result:\n{item.get('text')}")

        return response

    async def stop(self):
        """Stop the server."""
        if self.process:
            print("\n=== Stopping Server ===")
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                print("Force killing server...")
                self.process.kill()
                await self.process.wait()

            print(f"Server stopped (exit code: {self.process.returncode})")


async def test_flexsim_open_model():
    """Test the flexsim_open_model tool."""

    # Find server script
    script_dir = Path(__file__).parent.parent.parent
    server_script = script_dir / "mcp_server" / "flexsim_mcp.py"

    if not server_script.exists():
        print(f"ERROR: Server script not found: {server_script}")
        return False

    # Find a test model using config
    config = get_config()
    flexsimpy_path = config.get("build.flexsimpy_dir", "depends/FlexSimPy")
    flexsimpy_dir = script_dir / flexsimpy_path
    test_model = flexsimpy_dir / "TestFlexSimPy" / "PostOfficeModel.fsm"

    if not test_model.exists():
        print(f"ERROR: Test model not found: {test_model}")
        print("Please provide a valid .fsm file path")
        return False

    client = MCPClient(str(server_script))

    try:
        # Start server
        await client.start()

        # Initialize
        await client.initialize()

        # List tools
        tools = await client.list_tools()

        # Check if flexsim_open_model exists
        tool_names = [t["name"] for t in tools]
        if "flexsim_open_model" not in tool_names:
            print("\nERROR: flexsim_open_model tool not found!")
            return False

        print("\n✓ Found flexsim_open_model tool")

        # Test opening a model
        print(f"\nTesting with model: {test_model}")
        result = await client.call_tool(
            "flexsim_open_model",
            {"model_path": str(test_model)}
        )

        # Check result
        if "result" in result:
            print("\n✓ Tool call successful!")
            return True
        else:
            print(f"\n✗ Tool call failed: {result.get('error')}")
            return False

    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await client.stop()


async def test_flexsim_run():
    """Test the flexsim_run tool - run simulation for 20 seconds."""

    # Find server script
    script_dir = Path(__file__).parent.parent.parent
    server_script = script_dir / "mcp_server" / "flexsim_mcp.py"

    if not server_script.exists():
        print(f"ERROR: Server script not found: {server_script}")
        return False

    # Find a test model using config
    config = get_config()
    flexsimpy_path = config.get("build.flexsimpy_dir", "depends/FlexSimPy")
    flexsimpy_dir = script_dir / flexsimpy_path
    test_model = flexsimpy_dir / "TestFlexSimPy" / "PostOfficeModel.fsm"

    if not test_model.exists():
        print(f"ERROR: Test model not found: {test_model}")
        return False

    client = MCPClient(str(server_script))

    try:
        # Start server
        await client.start()

        # Initialize
        await client.initialize()

        # List tools
        tools = await client.list_tools()
        tool_names = [t["name"] for t in tools]

        # Check required tools exist
        required_tools = ["flexsim_open_model", "flexsim_reset", "flexsim_run",
                         "flexsim_stop", "flexsim_get_time"]
        for tool in required_tools:
            if tool not in tool_names:
                print(f"\nERROR: {tool} tool not found!")
                return False

        print("\n✓ All required tools found")

        # Open model
        print(f"\nOpening model: {test_model}")
        result = await client.call_tool(
            "flexsim_open_model",
            {"model_path": str(test_model)}
        )

        if "result" not in result:
            print(f"\n✗ Failed to open model: {result.get('error')}")
            return False

        print("✓ Model opened")

        # Reset simulation
        print("\nResetting simulation...")
        result = await client.call_tool("flexsim_reset")
        if "result" not in result:
            print(f"\n✗ Failed to reset: {result.get('error')}")
            return False

        print("✓ Simulation reset")

        # Get initial time
        print("\nGetting initial time...")
        result = await client.call_tool("flexsim_get_time")
        if "result" in result:
            content = result.get("result", {}).get("content", [])
            if content:
                print(f"Initial time: {content[0].get('text')}")

        # Start running
        print("\nStarting simulation run...")
        result = await client.call_tool("flexsim_run")

        if "result" not in result:
            print(f"\n✗ Failed to start run: {result.get('error')}")
            return False

        print("✓ Simulation started running")

        # Wait for 20 seconds
        print("\nWaiting 20 seconds...")
        await asyncio.sleep(20)

        # Stop simulation
        print("\nStopping simulation...")
        result = await client.call_tool("flexsim_stop")

        if "result" not in result:
            print(f"\n✗ Failed to stop: {result.get('error')}")
            return False

        # Get final time
        print("\nGetting final time...")
        result = await client.call_tool("flexsim_get_time")

        if "result" in result:
            content = result.get("result", {}).get("content", [])
            if content:
                final_time = content[0].get('text')
                print(f"Final time: {final_time}")

                # Verify simulation ran (time should be > 0)
                if "0.00s" in final_time and "Time: 0.00s" == final_time:
                    print("\n✗ Simulation did not advance (still at 0.00s)")
                    return False
                else:
                    print("\n✓ Simulation ran successfully!")
                    return True
        else:
            print(f"\n✗ Failed to get final time: {result.get('error')}")
            return False

    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await client.stop()


async def main():
    """Run integration tests."""
    print("=" * 70)
    print("FlexSim MCP Server Integration Tests")
    print("=" * 70)

    # Test 1: Open Model
    print("\n" + "=" * 70)
    print("TEST 1: flexsim_open_model")
    print("=" * 70)
    test1_result = await test_flexsim_open_model()

    # Test 2: Run Simulation
    print("\n" + "=" * 70)
    print("TEST 2: flexsim_run (20 seconds)")
    print("=" * 70)
    test2_result = await test_flexsim_run()

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Test 1 (flexsim_open_model): {'✓ PASSED' if test1_result else '✗ FAILED'}")
    print(f"Test 2 (flexsim_run):        {'✓ PASSED' if test2_result else '✗ FAILED'}")

    all_passed = test1_result and test2_result

    print("\n" + "=" * 70)
    if all_passed:
        print("✓ All tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
