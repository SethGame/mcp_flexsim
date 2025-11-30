#!/usr/bin/env python3
"""FlexSim MCP Server - Landing Page & Documentation.

A Gradio-based interactive documentation app explaining the project.
"""

import gradio as gr

# ============================================================================
# Content
# ============================================================================

HERO_HTML = """
<div style="
    background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
    padding: 3rem 2rem;
    border-radius: 16px;
    text-align: center;
    margin-bottom: 2rem;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
">
    <h1 style="
        font-size: 2.8rem;
        color: #00d4ff;
        margin: 0 0 0.5rem 0;
        text-shadow: 0 0 20px rgba(0,212,255,0.5);
        font-family: 'Segoe UI', system-ui, sans-serif;
    ">⚙️ FlexSim MCP Server</h1>
    <p style="
        font-size: 1.3rem;
        color: #a0d2db;
        margin: 0;
        font-weight: 300;
    ">Bridge Digital Twins with AI Assistants</p>
    <p style="
        font-size: 0.95rem;
        color: #7fb3b5;
        margin-top: 1rem;
    ">Control FlexSim simulations via Model Context Protocol (MCP)</p>
</div>
"""

WHY_CONTENT = """
## 🎯 The Problem

**Manufacturing and logistics simulation** is powerful but traditionally isolated:

- FlexSim models contain rich operational data
- Engineers manually run scenarios and extract insights
- No direct bridge to AI assistants or automated analysis

## 💡 The Solution

**FlexSim MCP Server** creates a standardized interface between:

| Component | Role |
|-----------|------|
| **FlexSim** | Industry-leading discrete event simulation engine |
| **MCP Protocol** | Anthropic's Model Context Protocol for AI tool integration |
| **AI Assistants** | Claude, Cursor, or custom LLM clients |

## 🚀 What This Enables

### For Engineers
- **Natural Language Control**: "Run the simulation for 8 hours and show me queue statistics"
- **Rapid What-If Analysis**: Ask AI to modify parameters and compare results
- **Automated Reporting**: Generate insights without manual data extraction

### For Developers
- **Standardized API**: MCP protocol works with any compliant client
- **Extensible Tools**: Add custom FlexScript operations easily
- **Reproducible Automation**: Script complex simulation workflows

### For Organizations
- **Digital Twin Integration**: Connect simulations to AI-powered decision support
- **Knowledge Capture**: AI assistants can query and explain model behavior
- **Accelerated Innovation**: Faster iteration on simulation scenarios
"""

ARCHITECTURE_CONTENT = """
## 🏗️ System Architecture

```
┌─────────────────────────┐         JSON-RPC          ┌─────────────────────────┐
│                         │                           │                         │
│      MCP Client         │◄────────────────────────► │      MCP Server         │
│   (Claude / Cursor /    │       stdin/stdout        │   (flexsim_mcp.py)      │
│    Gradio Client)       │                           │                         │
│                         │                           │                         │
└─────────────────────────┘                           └───────────┬─────────────┘
                                                                  │
                                                                  │ Python API
                                                                  ▼
                                                      ┌─────────────────────────┐
                                                      │                         │
                                                      │       FlexSimPy         │
                                                      │     (Python SDK)        │
                                                      │                         │
                                                      └───────────┬─────────────┘
                                                                  │
                                                                  │ COM / IPC
                                                                  ▼
                                                      ┌─────────────────────────┐
                                                      │                         │
                                                      │        FlexSim          │
                                                      │   (Simulation Engine)   │
                                                      │                         │
                                                      └─────────────────────────┘
```

## 📦 Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **MCP Server** | `mcp_server/flexsim_mcp.py` | FastMCP server exposing FlexSim tools |
| **FlexSimPy** | `depends/FlexSimPy/` | Python SDK for FlexSim automation |
| **Gradio Client** | `client/app.py` | Web UI for interactive control |
| **Configuration** | `config.toml` | Paths, logging, session settings |

## 🔧 Exposed Tools

### Simulation Control
| Tool | Description |
|------|-------------|
| `flexsim_open_model` | Open .fsm or .fsx model file |
| `flexsim_reset` | Reset simulation to time 0 |
| `flexsim_run` | Start continuous simulation |
| `flexsim_run_to_time` | Run until target time (fast or real-time) |
| `flexsim_stop` | Pause running simulation |
| `flexsim_step` | Advance by N events |
| `flexsim_get_time` | Query current simulation time |

### Model & Script
| Tool | Description |
|------|-------------|
| `flexsim_evaluate` | Execute FlexScript code |
| `flexsim_compile` | Check model for script errors |
| `flexsim_save_model` | Save current model |
| `flexsim_new_model` | Create blank model |

### Data Access
| Tool | Description |
|------|-------------|
| `flexsim_get_node_value` | Read value from model tree |
| `flexsim_set_node_value` | Write value to model tree |
| `flexsim_get_statistics` | Get performance metrics |
| `flexsim_export_results` | Export to CSV/XLSX/JSON |
"""

USAGE_CONTENT = """
## 📋 Prerequisites

| Requirement | Details |
|-------------|---------|
| **OS** | Windows (FlexSim requirement) |
| **Python** | 3.12 |
| **Package Manager** | [uv](https://astral.sh) |
| **FlexSim** | Local installation or evaluation license |

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd mcp_flexsim

# Run guided setup
python setup_mcp_server.py
```

### 2. Configure FlexSim Path

Edit `config.toml`:

```toml
[flexsim]
install_path = "FlexSimDev/program"
src_path = "C:\\\\Program Files\\\\FlexSim 2025"
```

### 3. Run the MCP Server

**Test Mode** (interactive, for debugging):
```bash
uv run mcp_server/flexsim_mcp.py --test-mode
```

**MCP Mode** (for clients):
```bash
uv run mcp_server/flexsim_mcp.py
```

## 🖥️ Using the Gradio Client

### Setup

```bash
# Install client dependencies
uv sync --extra client

# Set up Google Gemini API key
echo "GOOGLE_API_KEY=your_key" > client/.env
```

### Launch

```bash
uv run python client/app.py
```

Open http://127.0.0.1:7860 in your browser.

### Features

1. **Connect** to MCP server via stdio
2. **Direct Tool Calls** - Execute tools with JSON arguments
3. **Chat Interface** - Natural language control via Google Gemini

## 🔌 Configuring Claude Desktop / Cursor

Add to your MCP client configuration:

```json
{
  "mcpServers": {
    "flexsim": {
      "command": "uv",
      "args": [
        "--directory",
        "C:/path/to/mcp_flexsim",
        "run",
        "mcp_server/flexsim_mcp.py"
      ]
    }
  }
}
```

## 💬 Example Conversations

**User**: "Open the warehouse model and run it for 1 hour"

**AI**: *Calls `flexsim_open_model` → `flexsim_run_to_time`*
> ✓ Opened warehouse model. Simulation ran to 3600s.

**User**: "What's the average queue length at Station 1?"

**AI**: *Calls `flexsim_evaluate` with FlexScript query*
> The average queue content at Station 1 is 4.7 items.

**User**: "Double the processing time and compare throughput"

**AI**: *Calls `flexsim_set_node_value` → `flexsim_reset` → `flexsim_run_to_time` → `flexsim_get_statistics`*
> With doubled processing time, throughput decreased by 38%.
"""

RESOURCES_CONTENT = """
## 📁 Repository Structure

```
mcp_flexsim/
├── app.py                    # This documentation app
├── config.toml               # Main configuration
├── mcp_server_config.json    # Client config template
├── setup_mcp_server.py       # Guided setup script
│
├── mcp_server/
│   └── flexsim_mcp.py        # MCP server entry point
│
├── client/
│   ├── app.py                # Gradio MCP client
│   └── README.md             # Client documentation
│
├── utility/
│   ├── config.py             # Configuration loader
│   ├── build_automation.py   # FlexSimPy build script
│   ├── integration_test.py   # GUI sanity test
│   └── utility.py            # Helper functions
│
├── tests/integration/
│   └── test_mcp_client.py    # Automated integration tests
│
└── depends/
    └── FlexSimPy/            # Python SDK submodule
```

## 🔗 Useful Links

| Resource | URL |
|----------|-----|
| **Model Context Protocol** | https://modelcontextprotocol.io |
| **FlexSim** | https://www.flexsim.com |
| **FastMCP** | https://github.com/jlowin/fastmcp |
| **uv Package Manager** | https://astral.sh |
| **Google AI Studio** | https://aistudio.google.com |

## 🧪 Running Tests

```bash
# Integration tests (requires FlexSim)
uv run python tests/integration/test_mcp_client.py

# GUI sanity test (interactive)
uv run python utility/integration_test.py

# Check FlexSimPy build status
uv run python utility/build_automation.py --status
```

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| FlexSim not found | Update `flexsim.install_path` in `config.toml` |
| FlexSimPy unavailable | Run `uv run python utility/build_automation.py --install` |
| Connection failed | Check `mcp_server/flexsim_mcp.log` for errors |
| CEF/GPU errors | These are cosmetic; utilities suppress them |

## 📜 License

MIT License - See LICENSE file for details.
"""

# ============================================================================
# Gradio Interface
# ============================================================================

def create_app():
    """Create the documentation Gradio app."""
    
    with gr.Blocks(
        title="FlexSim MCP Server",
        theme=gr.themes.Base(
            primary_hue="cyan",
            secondary_hue="slate",
            neutral_hue="slate",
            font=gr.themes.GoogleFont("IBM Plex Sans"),
            font_mono=gr.themes.GoogleFont("IBM Plex Mono"),
        ),
        css="""
        .main-container { max-width: 1000px; margin: auto; }
        .tab-nav button { font-size: 1rem !important; padding: 0.8rem 1.5rem !important; }
        .prose { line-height: 1.7; }
        .prose h2 { color: #00d4ff; border-bottom: 2px solid #203a43; padding-bottom: 0.5rem; }
        .prose table { width: 100%; margin: 1rem 0; }
        .prose th { background: #1a2a3a; color: #00d4ff; }
        .prose td, .prose th { padding: 0.5rem 1rem; border: 1px solid #2c3e50; }
        .prose code { background: #1a2a3a; padding: 0.2rem 0.4rem; border-radius: 4px; }
        .prose pre { background: #0d1a24 !important; border: 1px solid #2c3e50; border-radius: 8px; }
        footer { display: none !important; }
        """
    ) as app:
        
        gr.HTML(HERO_HTML)
        
        with gr.Tabs() as tabs:
            with gr.Tab("🎯 Why This Project", id="why"):
                gr.Markdown(WHY_CONTENT, elem_classes="prose")
            
            with gr.Tab("🏗️ Architecture", id="arch"):
                gr.Markdown(ARCHITECTURE_CONTENT, elem_classes="prose")
            
            with gr.Tab("🚀 How to Use", id="usage"):
                gr.Markdown(USAGE_CONTENT, elem_classes="prose")
            
            with gr.Tab("📚 Resources", id="resources"):
                gr.Markdown(RESOURCES_CONTENT, elem_classes="prose")
            
            with gr.Tab("🖥️ Launch Client", id="client"):
                gr.Markdown("""
                ## Launch the Interactive Client
                
                The MCP client provides a web interface to control FlexSim simulations.
                """)
                
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("""
                        ### Quick Launch
                        
                        Run this command in your terminal:
                        
                        ```bash
                        uv run python client/app.py
                        ```
                        
                        Then open http://127.0.0.1:7860
                        """)
                    
                    with gr.Column():
                        gr.Markdown("""
                        ### Features
                        
                        - ✅ Connect to FlexSim MCP server
                        - ✅ Execute tools directly  
                        - ✅ Chat with Google Gemini
                        - ✅ View tool call results
                        """)
                
                gr.Markdown("""
                ---
                
                ### Prerequisites
                
                1. **Install dependencies**: `uv sync --extra client`
                2. **Set API key**: Create `client/.env` with `GOOGLE_API_KEY=your_key`
                3. **Ensure FlexSim** is installed and configured in `config.toml`
                """)
        
        gr.HTML("""
        <div style="
            text-align: center;
            padding: 2rem;
            margin-top: 2rem;
            border-top: 1px solid #2c3e50;
            color: #5a7a8a;
        ">
            <p style="margin: 0;">
                FlexSim MCP Server • 
                <a href="https://modelcontextprotocol.io" style="color: #00d4ff;">MCP Protocol</a> • 
                <a href="https://www.flexsim.com" style="color: #00d4ff;">FlexSim</a>
            </p>
        </div>
        """)
    
    return app


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    app = create_app()
    app.launch(
        server_name="127.0.0.1",
        server_port=7861,
        share=False,
        show_error=True
    )

