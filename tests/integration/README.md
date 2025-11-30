# FlexSim MCP Server Integration Tests

Integration tests for the FlexSim MCP Server that verify stdio communication and tool functionality.

## Test Suite

### Test 1: `flexsim_open_model`
Tests opening a FlexSim model file via MCP.

**Steps:**
1. Start MCP server as subprocess
2. Initialize MCP session
3. List available tools
4. Call `flexsim_open_model` with PostOfficeModel.fsm
5. Verify successful response

**Expected Result:** Model opens successfully at time 0.00s

### Test 2: `flexsim_run`
Tests running a simulation for 20 seconds.

**Steps:**
1. Start MCP server and initialize session
2. Open PostOfficeModel.fsm
3. Reset simulation to time 0
4. Start continuous simulation run
5. Wait 20 seconds (real time)
6. Stop simulation
7. Verify simulation time advanced beyond 0

**Expected Result:** Simulation runs and advances time (e.g., ~80 seconds simulation time)

## Running Tests

```bash
# Run all integration tests
uv run tests/integration/test_mcp_client.py
```

## Test Results

**✓ All tests passed!**

```
TEST SUMMARY
Test 1 (flexsim_open_model): ✓ PASSED
Test 2 (flexsim_run):        ✓ PASSED
```

### Sample Output

**Test 1 - Open Model:**
```
✓ Opened: PostOfficeModel
Time: 0.00s
```

**Test 2 - Run Simulation:**
```
Initial time: Time: 0.00s (0.00s)
✓ Simulation started running
Waiting 20 seconds...
✓ Stopped at 1.33m
Final time: Time: 1.33m (80.02s)
✓ Simulation ran successfully!
```

## Architecture

### MCPClient Class
Simple MCP client implementation that:
- Manages subprocess communication via stdin/stdout
- Sends JSON-RPC 2.0 formatted messages
- Handles MCP protocol (initialize, tools/list, tools/call)
- Supports both requests and notifications

### Key Components

**Initialization:**
```python
client = MCPClient(server_script)
await client.start()
await client.initialize()
```

**Listing Tools:**
```python
tools = await client.list_tools()
```

**Calling Tools:**
```python
result = await client.call_tool(
    "flexsim_open_model",
    {"model_path": "path/to/model.fsm"}
)
```

## Notes

- Tests start a fresh MCP server instance for each test
- FlexSim GUI is launched on server startup (as configured)
- Server uses evaluation license mode
- Async subprocess management for non-blocking I/O
- UTF-8 encoding configured for Windows console compatibility

## Dependencies

- Python 3.10+
- asyncio
- json
- FlexSim MCP Server
- FlexSimPy module

## Future Tests

Potential additional tests:
- `flexsim_run_to_time` - Run to specific simulation time
- `flexsim_step` - Step through events
- `flexsim_evaluate` - Execute FlexScript
- `flexsim_get_node_value` / `flexsim_set_node_value` - Tree node access
- `flexsim_get_statistics` - Performance metrics
- Error handling scenarios
