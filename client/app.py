#!/usr/bin/env python3
"""MCP Client for FlexSim simulation control using Gradio.

A minimal Gradio-based MCP client that connects to the FlexSim MCP server
via stdio transport and provides a chat interface for tool calling.

Primary LLM: Google Gemini
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import gradio as gr
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Load environment variables
load_dotenv()

# Google Gemini SDK
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class FlexSimMCPClient:
    """MCP Client wrapper for FlexSim server connection."""

    def __init__(self):
        self.session: ClientSession | None = None
        self.connected = False
        self.tools: list[dict] = []
        self._gemini_client = None
        
        # Initialize Gemini client
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if GEMINI_AVAILABLE and api_key:
            self._gemini_client = genai.Client(api_key=api_key)

    async def connect(self, working_dir: str, command: str, args: str) -> str:
        """Connect to the FlexSim MCP server via stdio."""
        try:
            # Parse arguments
            args_list = [a.strip() for a in args.split(",") if a.strip()]
            
            # Replace placeholder with actual directory
            args_list = [
                a.replace("<repo-flexsim_mcp>", working_dir) 
                for a in args_list
            ]

            server_params = StdioServerParameters(
                command=command,
                args=args_list,
                cwd=working_dir if working_dir else None
            )

            # Create stdio client context
            self._read, self._write = await stdio_client(server_params).__aenter__()
            self.session = await ClientSession(self._read, self._write).__aenter__()
            
            # Initialize session
            await self.session.initialize()
            
            # List available tools
            tools_response = await self.session.list_tools()
            self.tools = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                }
                for tool in tools_response.tools
            ]
            
            self.connected = True
            tools_list = "\n".join([f"  • {t['name']}" for t in self.tools])
            return f"✓ Connected to FlexSim MCP Server\n\nAvailable tools ({len(self.tools)}):\n{tools_list}"
            
        except Exception as e:
            self.connected = False
            return f"✗ Connection failed: {str(e)}"

    async def disconnect(self) -> str:
        """Disconnect from the MCP server."""
        if self.session:
            try:
                await self.session.__aexit__(None, None, None)
            except Exception:
                pass
        self.session = None
        self.connected = False
        self.tools = []
        return "Disconnected"

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        """Call a specific tool on the MCP server."""
        if not self.connected or not self.session:
            return "Error: Not connected to MCP server"
        
        try:
            result = await self.session.call_tool(tool_name, arguments)
            
            # Format result content
            if isinstance(result.content, list):
                return "\n".join(str(item.text if hasattr(item, 'text') else item) for item in result.content)
            return str(result.content)
            
        except Exception as e:
            return f"Tool error: {str(e)}"

    def _build_gemini_tools(self) -> list:
        """Build Gemini tool declarations from MCP tools."""
        gemini_tools = []
        for tool in self.tools:
            # Create FunctionDeclaration for each MCP tool
            func_decl = types.FunctionDeclaration(
                name=tool["name"],
                description=tool["description"] or f"Execute {tool['name']}",
                parameters_json_schema=tool["input_schema"] if tool["input_schema"] else {
                    "type": "object",
                    "properties": {}
                }
            )
            gemini_tools.append(func_decl)
        
        return [types.Tool(function_declarations=gemini_tools)] if gemini_tools else []

    async def process_with_llm(self, user_message: str, history: list) -> list:
        """Process user message with Google Gemini and tool calling."""
        if not self._gemini_client:
            return history + [{"role": "assistant", "content": "⚠️ Google Gemini API not configured. Set GOOGLE_API_KEY or GEMINI_API_KEY in .env file."}]
        
        if not self.connected:
            return history + [{"role": "assistant", "content": "⚠️ Not connected to MCP server. Please connect first."}]

        # Build conversation contents for Gemini
        contents = []
        for msg in history:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if isinstance(content, str) and content:
                # Gemini uses 'user' and 'model' roles
                gemini_role = "model" if role == "assistant" else "user"
                contents.append(types.Content(
                    role=gemini_role,
                    parts=[types.Part.from_text(text=content)]
                ))
        
        # Add current user message
        user_content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_message)]
        )
        contents.append(user_content)

        # Build Gemini tools
        gemini_tools = self._build_gemini_tools()

        result_messages = []
        
        try:
            # Call Gemini with tools (disable automatic function calling for manual control)
            response = self._gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    tools=gemini_tools,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        disable=True
                    ),
                    system_instruction="You are a FlexSim simulation assistant. Use the available tools to control and query FlexSim simulations. Be concise and helpful."
                )
            )

            # Check for function calls
            if response.function_calls:
                for fc in response.function_calls:
                    tool_name = fc.name
                    tool_args = dict(fc.args) if fc.args else {}
                    
                    # Show tool call
                    result_messages.append({
                        "role": "assistant",
                        "content": f"🔧 **Calling:** `{tool_name}`\n```json\n{json.dumps(tool_args, indent=2)}\n```"
                    })
                    
                    # Execute tool via MCP
                    tool_result = await self.session.call_tool(tool_name, tool_args)
                    result_content = "\n".join(
                        str(item.text if hasattr(item, 'text') else item) 
                        for item in (tool_result.content if isinstance(tool_result.content, list) else [tool_result.content])
                    )
                    
                    # Show result
                    result_messages.append({
                        "role": "assistant", 
                        "content": f"📋 **Result:**\n```\n{result_content}\n```"
                    })
                    
                    # Build function response for follow-up
                    function_response_part = types.Part.from_function_response(
                        name=tool_name,
                        response={"result": result_content}
                    )
                    function_response_content = types.Content(
                        role="tool",
                        parts=[function_response_part]
                    )
                    
                    # Get follow-up from Gemini with function result
                    follow_up_contents = contents + [
                        response.candidates[0].content,
                        function_response_content
                    ]
                    
                    follow_up = self._gemini_client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=follow_up_contents,
                        config=types.GenerateContentConfig(
                            tools=gemini_tools,
                            system_instruction="You are a FlexSim simulation assistant. Summarize the tool result concisely."
                        )
                    )
                    
                    if follow_up.text:
                        result_messages.append({
                            "role": "assistant",
                            "content": follow_up.text
                        })
            
            elif response.text:
                # Direct text response (no tool calls)
                result_messages.append({
                    "role": "assistant",
                    "content": response.text
                })
            else:
                result_messages.append({
                    "role": "assistant",
                    "content": "⚠️ No response from Gemini."
                })

        except Exception as e:
            result_messages.append({
                "role": "assistant",
                "content": f"❌ Error: {str(e)}"
            })
        
        return result_messages


# Global client instance
client = FlexSimMCPClient()


def get_default_config() -> tuple[str, str, str]:
    """Get default MCP server configuration."""
    repo_dir = str(Path(__file__).parent.parent.resolve())
    command = "uv"
    args = f"--directory, {repo_dir}, run, mcp_server/flexsim_mcp.py"
    return repo_dir, command, args


async def connect_server(working_dir: str, command: str, args: str):
    """Connect to MCP server."""
    return await client.connect(working_dir, command, args)


async def disconnect_server():
    """Disconnect from MCP server."""
    return await client.disconnect()


async def call_tool_direct(tool_name: str, args_json: str, history: list):
    """Call a tool directly without LLM."""
    try:
        args = json.loads(args_json) if args_json.strip() else {}
    except json.JSONDecodeError as e:
        return history + [{"role": "assistant", "content": f"❌ Invalid JSON: {e}"}]
    
    result = await client.call_tool(tool_name, args)
    return history + [
        {"role": "user", "content": f"🔧 Direct call: `{tool_name}`\n```json\n{json.dumps(args, indent=2)}\n```"},
        {"role": "assistant", "content": f"📋 **Result:**\n```\n{result}\n```"}
    ]


async def chat_with_llm(message: str, history: list):
    """Chat with LLM for tool calling."""
    new_history = history + [{"role": "user", "content": message}]
    responses = await client.process_with_llm(message, history)
    return new_history + responses, ""


def get_tools_list() -> list[str]:
    """Get list of available tool names."""
    return [t["name"] for t in client.tools] if client.tools else ["(not connected)"]


def refresh_tools() -> gr.Dropdown:
    """Refresh the tools dropdown."""
    return gr.Dropdown(choices=get_tools_list(), value=get_tools_list()[0] if client.tools else None)


# ============================================================================
# Gradio Interface
# ============================================================================

def create_interface():
    """Create the Gradio interface."""
    
    default_dir, default_cmd, default_args = get_default_config()
    
    with gr.Blocks(
        title="FlexSim MCP Client",
        theme=gr.themes.Base(
            primary_hue="blue",
            secondary_hue="slate",
            neutral_hue="slate",
            font=gr.themes.GoogleFont("JetBrains Mono"),
        ),
        css="""
        .container { max-width: 1200px; margin: auto; }
        .header { 
            background: linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%);
            padding: 1.5rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        }
        .header h1 { color: #ffffff; margin: 0; font-size: 1.8rem; }
        .header p { color: #bbdefb; margin: 0.5rem 0 0 0; font-size: 0.9rem; }
        .status-connected { color: #00ff88 !important; }
        .status-disconnected { color: #ff6b6b !important; }
        .tool-panel { 
            background: #1a1a2e; 
            border: 1px solid #16213e;
            border-radius: 8px;
            padding: 1rem;
        }
        """
    ) as demo:
        
        # Header
        gr.HTML("""
        <div class="header">
            <h1>⚙️ FlexSim MCP Client</h1>
            <p>Control FlexSim simulations via Model Context Protocol • Powered by Google Gemini</p>
        </div>
        """)
        
        with gr.Row():
            # Left Panel - Configuration
            with gr.Column(scale=1):
                gr.Markdown("### 🔌 Server Connection")
                
                working_dir = gr.Textbox(
                    label="Working Directory",
                    value=default_dir,
                    placeholder="Path to mcp_flexsim repository"
                )
                
                command = gr.Textbox(
                    label="Command",
                    value=default_cmd,
                    placeholder="e.g., uv, python"
                )
                
                args = gr.Textbox(
                    label="Arguments (comma-separated)",
                    value=default_args,
                    placeholder="--directory, /path, run, script.py"
                )
                
                with gr.Row():
                    connect_btn = gr.Button("Connect", variant="primary", scale=2)
                    disconnect_btn = gr.Button("Disconnect", variant="secondary", scale=1)
                
                status = gr.Textbox(
                    label="Status",
                    value="Not connected",
                    interactive=False,
                    lines=8
                )
                
                # Direct Tool Call Panel
                gr.Markdown("### 🔧 Direct Tool Call")
                
                tool_dropdown = gr.Dropdown(
                    label="Tool",
                    choices=["(not connected)"],
                    value="(not connected)",
                    interactive=True
                )
                
                refresh_btn = gr.Button("🔄 Refresh Tools", size="sm")
                
                tool_args = gr.Textbox(
                    label="Arguments (JSON)",
                    value="{}",
                    placeholder='{"params": {"model_path": "C:/model.fsm"}}',
                    lines=3
                )
                
                call_btn = gr.Button("Execute Tool", variant="primary")
            
            # Right Panel - Chat
            with gr.Column(scale=2):
                gr.Markdown("### 💬 Chat Interface (Gemini)")
                
                chatbot = gr.Chatbot(
                    value=[],
                    height=500,
                    type="messages",
                    show_copy_button=True,
                    avatar_images=("👤", "✨"),
                    bubble_full_width=False
                )
                
                with gr.Row():
                    msg_input = gr.Textbox(
                        label="Message",
                        placeholder="Ask about FlexSim or request tool operations...",
                        scale=4,
                        show_label=False
                    )
                    send_btn = gr.Button("Send", variant="primary", scale=1)
                
                with gr.Row():
                    clear_btn = gr.Button("🗑️ Clear Chat", size="sm")
                    
                gr.Markdown("""
                <small>
                💡 **Tips:** 
                - Connect to server first
                - Use direct tool calls for quick operations
                - Chat requires GOOGLE_API_KEY or GEMINI_API_KEY in .env
                </small>
                """)
        
        # Event handlers
        connect_btn.click(
            fn=connect_server,
            inputs=[working_dir, command, args],
            outputs=[status]
        ).then(
            fn=refresh_tools,
            outputs=[tool_dropdown]
        )
        
        disconnect_btn.click(
            fn=disconnect_server,
            outputs=[status]
        )
        
        refresh_btn.click(
            fn=refresh_tools,
            outputs=[tool_dropdown]
        )
        
        call_btn.click(
            fn=call_tool_direct,
            inputs=[tool_dropdown, tool_args, chatbot],
            outputs=[chatbot]
        )
        
        send_btn.click(
            fn=chat_with_llm,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input]
        )
        
        msg_input.submit(
            fn=chat_with_llm,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input]
        )
        
        clear_btn.click(
            fn=lambda: [],
            outputs=[chatbot]
        )
    
    return demo


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    if not GEMINI_AVAILABLE:
        print("⚠️  google-genai package not installed. LLM chat will be disabled.")
        print("   Install with: pip install google-genai")
    else:
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("⚠️  GOOGLE_API_KEY or GEMINI_API_KEY not found in environment.")
            print("   Create a .env file with: GOOGLE_API_KEY=your_key_here")
            print("   Get your API key at: https://aistudio.google.com/apikey")
    
    interface = create_interface()
    interface.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        debug=True
    )
