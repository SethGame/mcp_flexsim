# Repository Guidelines

## Project Structure & Module Organization
- `mcp_server/flexsim_mcp.py` hosts the FastMCP server and FlexSimPy controller logic; treat it as the single entry point for runtime changes.
- `utility/` contains shared helpers (`config.py`, build automation, integration harness) that are imported dynamically—update these with backwards compatibility in mind.
- `tests/integration/` provides stdio client tests that exercise live FlexSim interactions; add new end-to-end checks here.
- `depends/FlexSimPy` is a submodule for the FlexSimPy SDK, while `FlexSimDev/program` mirrors a local FlexSim installation used during builds.
- `config.toml` and `mcp_server_config.json` define install locations and MCP launch defaults; prefer editing copies rather than committing per-user paths.

## Build, Test, and Development Commands
- Install and lock dependencies with `uv sync` from the repo root; commit `uv.lock` when dependencies change.
- Run the MCP server interactively via `uv run mcp_server/flexsim_mcp.py --test-mode` to verify tool availability.
- Check FlexSimPy build status or trigger a rebuild with `uv run python utility/build_automation.py --status` or `--install`.
- Execute integration smoke tests using `uv run python tests/integration/test_mcp_client.py`; the script launches the server and validates tool calls.
- Use `uv run python utility/integration_test.py` when you need a GUI-backed FlexSim sanity check.

## Coding Style & Naming Conventions
- Python code uses 4-space indentation, type hints, and Pydantic models for inputs; mirror patterns already present in `flexsim_mcp.py`.
- Keep log messages concise and actionable—prefer `logger.info` / `logger.error` over prints inside server modules.
- Follow snake_case for functions and variables, PascalCase for Pydantic models, and prefix async tool functions with `flexsim_` to align with existing tool registry names.
- Run `uv run python -m compileall mcp_server utility` before large refactors when you need an extra syntax check.

## Testing Guidelines
- Integration coverage is expected for new tools; extend `tests/integration/test_mcp_client.py` with deterministic scenarios and guard long sleeps with timeouts.
- Tests should set up temporary models under `tests/integration/assets`; avoid pointing at licensed models committed to source.
- Favor human-readable assertions that echo the tool name and target node so failures map directly to FlexSim operations.

## Commit & Pull Request Guidelines
- Use imperative, present-tense summaries under 72 characters (e.g., `Add FlexSim reset helper`), matching the existing history.
- Reference FlexSim defects or GitHub issues in the body (`Fixes #123`) and note configuration quirks testers must apply.
- PRs should describe FlexSim prerequisites, include command snippets used for validation, and attach logs or screenshots when GUI behavior changes.

## FlexSim Configuration & Security
- Keep real installation paths outside version control by setting `FLEXSIM_CONFIG_PATH` or overriding `FLEXSIM_INSTALL_PATH` in your environment.
- Review generated `flexsim_mcp.log` before pushing; strip sensitive workstation paths or usernames.
- Verify that submodules such as `depends/FlexSimPy` are pinned to vetted commits and update the lockfile when SDK components change.
