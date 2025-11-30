# FlexSim MCP Client (Gradio)

A minimal Gradio-based MCP client for interacting with the FlexSim MCP server.

## Features

- **Server Connection Panel**: Configure and connect to FlexSim MCP server via stdio transport
- **Direct Tool Calls**: Execute FlexSim tools directly without LLM
- **LLM Chat Interface**: Chat with Google Gemini to control FlexSim using natural language

## Setup

1. Install client dependencies:
```bash
# From repository root
uv sync --extra client
```

2. (Optional) Configure Google Gemini API for LLM chat:
```bash
# Create .env file in client directory
echo "GOOGLE_API_KEY=your_key_here" > client/.env
```

Get your API key at: https://aistudio.google.com/apikey

## Running

```bash
# From repository root
uv run python client/app.py
```

Open http://127.0.0.1:7860 in your browser.

## Usage

### Connecting to FlexSim MCP Server

1. The default configuration points to the local repository
2. Click **Connect** to start the MCP server and establish connection
3. Available tools will be listed in the status panel

### Direct Tool Calls

Use the tool dropdown to select a tool and provide JSON arguments:

```json
// Open a model
{"params": {"model_path": "C:/Models/warehouse.fsm"}}

// Run to time
{"params": {"target_time": 3600}}

// Evaluate FlexScript
{"params": {"script": "getmodeltime()"}}
```

### LLM Chat (Gemini)

With Google API configured, you can use natural language:

- "Open the warehouse model"
- "Run the simulation for 1 hour"
- "What's the current simulation time?"
- "Get statistics for the model"

The Gemini model will automatically identify which FlexSim tools to call based on your request.

## Configuration

Default server configuration (can be modified in the UI):

| Field | Default Value |
|-------|--------------|
| Working Directory | Repository root |
| Command | `uv` |
| Arguments | `--directory, <repo>, run, mcp_server/flexsim_mcp.py` |

### Environment Variables

| Variable | Description |
|----------|-------------|
| `GOOGLE_API_KEY` | Google AI Studio API key (primary) |
| `GEMINI_API_KEY` | Alternative API key variable |

## Troubleshooting

- **Connection failed**: Ensure FlexSim is installed and `config.toml` paths are correct
- **LLM chat disabled**: Install google-genai package and set GOOGLE_API_KEY
- **Tool errors**: Check `mcp_server/flexsim_mcp.log` for server-side errors

