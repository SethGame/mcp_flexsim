---
title: FlexSim MCP Server
emoji: 👌
colorFrom: blue
colorTo: green
sdk: static
sdk_version: "0.1"
app_file: app.py
pinned: false
---

# FlexSim MCP Server (incl. FlexSimPy)

![Track](https://img.shields.io/badge/track-building--mcp--track--xx-blue)

Control and automate FlexSim simulations via the Model Context Protocol (MCP). This repository exposes a FastMCP server that launches FlexSim (via FlexSimPy) and provides tools to open models, run/stop, step, query/set node values, evaluate FlexScript, export results, and more.

Why this matters
- Bridges digital twins and AI assistants (Claude/Cursor) for manufacturing/warehouse analysis and “what-if” studies.
- Demonstrates robust systems engineering: GUI process orchestration, async I/O, protocol handling, Windows quirks, and reproducible automation.

---

## Design

```
┌─────────────────────┐       JSON-RPC        ┌─────────────────────┐
│    MCP Client       │◄────────────────────► │    MCP Server       │
│  (Claude/Cursor)    │     stdin/stdout      │  (flexsim_mcp.py)   │
└─────────────────────┘                       └──────────┬──────────┘
                                                         │
                                                         │ Python API
                                                         ▼
                                              ┌─────────────────────┐
                                              │     FlexSimPy       │
                                              │   (Python SDK)      │
                                              └──────────┬──────────┘
                                                         │
                                                         │ COM/IPC
                                                         ▼
                                              ┌─────────────────────┐
                                              │      FlexSim        │
                                              │  (Simulation Engine)│
                                              └─────────────────────┘
```

---

## Features

- MCP server entry point: `mcp_server/flexsim_mcp.py`
- Tools exposed:
  - Simulation control: `flexsim_open_model`, `flexsim_reset`, `flexsim_run`, `flexsim_run_to_time`, `flexsim_stop`, `flexsim_step`, `flexsim_get_time`
  - Model/script: `flexsim_evaluate`, `flexsim_compile`, `flexsim_save_model`, `flexsim_new_model`
  - Node access: `flexsim_get_node_value`, `flexsim_set_node_value`
  - Results/stats: `flexsim_get_statistics`, `flexsim_export_results`
- Logging: `mcp_server/flexsim_mcp.log`
- Reproducible environment: `uv sync`
- FlexSimPy build automation: `utility/build_automation.py`
- Integration tests: `tests/integration/test_mcp_client.py` (stdio-based MCP client)
- GUI sanity test: `utility/integration_test.py`
- Configurable behavior via `config.toml` and environment overrides

---

## Requirements

- OS: Windows
- Python: 3.12 (default; configurable via `config.toml` or `FLEXSIM_PYTHON_VERSION`)
- Package manager: `uv` (https://astral.sh)
- FlexSim:
  - Real runs require a local FlexSim installation (or repo-local mirror in `FlexSimDev/program`)
  - FlexSimPy SDK submodule is provided at `depends/FlexSimPy` (see `.gitmodules`)

---

## Quickstart

Guided setup (recommended)
```/dev/null/shell.sh#L1-11
# From the repo root
python setup_mcp_server.py

# The setup helper will:
# - Summarize your configuration (install locations, Python version, submodule presence)
# - Ensure `uv` is installed and run `uv sync`
# - Build/install FlexSimPy via `utility/build_automation.py`
# - Optionally run a GUI integration sanity test
# - Print next steps to run the MCP server and tests
```

Manual setup
```/dev/null/shell.sh#L1-15
# 1) Install dependencies
uv sync

# 2) Check (and optionally build) FlexSimPy
uv run python utility/build_automation.py --status
# To force a build with a specific Python version:
# uv run python utility/build_automation.py --python-version 3.12

# 3) Launch MCP server in test mode (keeps the process alive; launches FlexSim on first tool call)
uv run mcp_server/flexsim_mcp.py --test-mode

# 4) Run integration tests (spawns the server as a subprocess; stdio MCP client)
uv run python tests/integration/test_mcp_client.py
```

---

## Configuration

Primary configuration lives in `config.toml` (repo root). You can also override at runtime using environment variables.

Example (excerpt from `config.toml`):
```flexsim_mcp/config.toml#L1-36
[flexsim]
install_path = "FlexSimDev/program"
src_path = "C:\\Program Files\\FlexSim 2025 Update 2"

[python]
version = "3.12"

[server]
name = "FlexSimPy MCP Server"
version = "0.1.0"
http_endpoint = "http://127.0.0.1:8088/mcp"

[session]
reuse_policy = "singleton"

[logging]
level = "INFO"
log_file = "flexsim_mcp.log"

[build]
flexsimpy_dir = "depends/FlexSimPy"
auto_build = true
auto_install = true
```

Environment overrides (see `utility/config.py`):
- `FLEXSIM_CONFIG_PATH` – path to an alternate `config.toml`
- `FLEXSIM_INSTALL_PATH` – override FlexSim program path
- `FLEXSIM_PYTHON_VERSION` – override Python version for FlexSimPy
- `FLEXSIM_LOG_LEVEL` – override logging level

---

## Running the MCP server

Two modes:

- Test mode (interactive; no stdio protocol)
```/dev/null/shell.sh#L1-3
uv run mcp_server/flexsim_mcp.py --test-mode
# Keeps running; FlexSim launches on first tool call; intended for manual testing
```

- MCP stdio mode (default when no flags are passed)
```/dev/null/shell.sh#L1-3
uv run mcp_server/flexsim_mcp.py
# Expects MCP JSON-RPC messages via stdin/stdout; used by clients/tests
```

Client configuration (for Claude/Cursor/etc.):
```flexsim_mcp/mcp_server_config.json#L1-14
{
  "mcpServers": {
    "flexsim": {
      "command": "uv",
      "args": [
        "--directory",
        "<repo-flexsim_mcp>/",
        "run",
        "mcp_server/flexsim_mcp.py"
      ]
    }
  }
}
```

---

## Example tool calls (JSON-RPC via MCP)

Open a model
```/dev/null/jsonrpc.txt#L1-15
{"jsonrpc":"2.0","id":1,"method":"tools/call",
 "params":{
   "name":"flexsim_open_model",
   "arguments":{"params":{
     "model_path":"C:/path/to/Model.fsm"
   }}
 }}
```

Run to time and read time
```/dev/null/jsonrpc.txt#L1-30
{"jsonrpc":"2.0","id":2,"method":"tools/call",
 "params":{"name":"flexsim_run_to_time","arguments":{"params":{"target_time":300}}}}

{"jsonrpc":"2.0","id":3,"method":"tools/call",
 "params":{"name":"flexsim_get_time"}}
```

Evaluate FlexScript
```/dev/null/jsonrpc.txt#L1-16
{"jsonrpc":"2.0","id":4,"method":"tools/call",
 "params":{"name":"flexsim_evaluate","arguments":{"params":{
   "script":"getmodeltime()"
 }}}}
```

Get/Set node value
```/dev/null/jsonrpc.txt#L1-33
{"jsonrpc":"2.0","id":5,"method":"tools/call",
 "params":{"name":"flexsim_get_node_value","arguments":{"params":{
   "node_path":"Model/Queue1/stats/input"
 }}}}

{"jsonrpc":"2.0","id":6,"method":"tools/call",
 "params":{"name":"flexsim_set_node_value","arguments":{"params":{
   "node_path":"Model/Processor1/variables/processtime",
   "value":5.0
 }}}}
```

More FlexScript examples and behavior: see `eval-flexscript.md`.

---

## Tests

Integration tests (stdio client; verifies tools and basic run sequence):
```/dev/null/shell.sh#L1-2
uv run python tests/integration/test_mcp_client.py
# Test 1: open model; Test 2: run for 20s, stop, verify time > 0
```

GUI sanity test (manual, interactive menu):
```/dev/null/shell.sh#L1-2
uv run python utility/integration_test.py
# Launches FlexSim GUI and provides simple interactive actions
```

---

## Repository structure

- `mcp_server/flexsim_mcp.py` — FastMCP server and FlexSimPy controller logic (entry point)
- `utility/`
  - `config.py` — configuration loader with env overrides
  - `build_automation.py` — FlexSimPy build/install orchestration (MSBuild resolution, .pyd install)
  - `copy_flexsim.py` — copies a FlexSim installation into `FlexSimDev/` (uses `flexsim.src_path`)
  - `integration_test.py` — GUI-backed sanity test (suppresses CEF stderr, safe cleanup)
  - `utility.py` — helpers: suppress stderr, kill FlexSim processes, force exit
- `tests/integration/`
  - `test_mcp_client.py` — async stdio client that starts the server and calls tools
  - `README.md` — test descriptions and sample outputs
- `depends/FlexSimPy` — FlexSimPy SDK submodule
- `FlexSimDev/program` — optional repo-local mirror of FlexSim install
- `config.toml`, `mcp_server_config.json`, `AGENTS.md`, `eval-flexscript.md`

---

## Batch Experiment Orchestrator (Design)

A high-impact enhancement to run parameter sweeps with replications, gather metrics, and export a unified `summary.csv` (and `manifest.json`), enabling “what-if” studies at scale.

- Design document: `Batch_Experiment_Orchestrator.md`
- Status: design in-repo; implementation planned (not yet in `flexsim_mcp.py`)
- MVP tool (planned): `flexsim_run_experiments` with parameter list, seeds/replications, run_to_time, stats, artifact_dir

---

## Troubleshooting

- FlexSim not found:
  - Update `flexsim.install_path` in `config.toml` or set `FLEXSIM_INSTALL_PATH`
  - Optionally use `utility/copy_flexsim.py` to mirror an existing install into `FlexSimDev/`
- FlexSimPy unavailable:
  - Check status: `uv run python utility/build_automation.py --status`
  - Rebuild for the active Python version and ensure the `.pyd` is installed
- Stdio client issues:
  - Ensure you run the server without `--test-mode` when using stdio clients
  - Check `mcp_server/flexsim_mcp.log` for details
- GUI noise (CEF) or shutdown issues:
  - The utilities suppress CEF stderr and force a safe interpreter exit when needed
