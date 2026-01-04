# MCP Server Integration Guide

This project supports **Model Context Protocol (MCP)** servers, allowing agents to dynamically access external tools without hardcoding. MCP servers expose tools via a standardized JSON-RPC protocol over stdio.

## What is MCP?

MCP (Model Context Protocol) is a protocol that allows AI systems to interact with external tools and data sources. MCP servers are standalone processes that expose:
- **Tools**: Functions the AI can call (e.g., get weather, read files, query databases)
- **Resources**: Data the AI can access
- **Prompts**: Pre-defined prompt templates

Our integration currently supports **tools only**.

## Current MCP Server: Weather

The system is pre-configured with the **mcp-server-weather** tool, which provides:
- `get_forecast(latitude: float, longitude: float)`: Get weather forecast for coordinates
- `get_alerts(state: str)`: Get active weather alerts for a US state

## How It Works

### 1. Installation

MCP servers are typically installed via npm:

```bash
npm install -g mcp-server-weather
```

Verify installation:
```bash
mcp-server-weather --stdio
# Should output: "Weather MCP Server running on stdio"
```

Press `Ctrl+C` to exit.

### 2. Configuration

MCP servers are configured in [`src/flexi/config/settings.py`](file:///Users/mariusmoisescu/Projects/flexi-deep-research-langgraph/src/flexi/config/settings.py):

```python
MCP_SERVERS: Dict[str, Dict[str, Any]] = {
    "weather": {
        "command": "mcp-server-weather",  # Command to run
        "args": ["--stdio"],               # Arguments (always --stdio)
        "enabled": True                    # Enable/disable this server
    }
}
```

**That's it!** No other code changes needed.

### 3. Automatic Tool Discovery

When the application starts:
1. **MCPToolManager** spawns each enabled MCP server as a subprocess
2. Sends a `tools/list` JSON-RPC request to discover available tools
3. Parses the tool schemas (name, description, parameters)
4. Creates Python wrapper functions with proper type annotations
5. **Automatically registers** them in the `ToolsRegistry`

From the Architect's perspective, MCP tools are indistinguishable from native tools.

### 4. Agent Usage

Agents can now use MCP tools just like any other tool:

**Example Research Question:**
> "What is the weather forecast for San Francisco? Are there any active alerts?"

**What Happens:**
1. Architect assigns `get_forecast` and `get_alerts` to an agent
2. Agent calls: `get_forecast(latitude=37.7749, longitude=-122.4194)`
3. MCPToolManager sends JSON-RPC request to mcp-server-weather
4. Weather data is returned to the agent
5. Agent synthesizes the information into a report

## Adding a New MCP Server

### Step 1: Install the MCP Server

Find an MCP server (e.g., from [Awesome MCP Servers](https://github.com/punkpeye/awesome-mcp-servers)):

```bash
# Example: Filesystem server
npm install -g @modelcontextprotocol/server-filesystem

# Example: GitHub server
npm install -g @modelcontextprotocol/server-github
```

### Step 2: Test the Server

Verify it works:
```bash
mcp-server-filesystem --stdio
# Should start without errors
```

### Step 3: Add to Configuration

Edit [`src/flexi/config/settings.py`](file:///Users/mariusmoisescu/Projects/flexi-deep-research-langgraph/src/flexi/config/settings.py):

```python
MCP_SERVERS: Dict[str, Dict[str, Any]] = {
    "weather": {
        "command": "mcp-server-weather",
        "args": ["--stdio"],
        "enabled": True
    },
    # ADD YOUR NEW SERVER HERE
    "filesystem": {
        "command": "mcp-server-filesystem",
        "args": ["--stdio", "/path/to/allowed/directory"],  # Some servers need extra args
        "enabled": True
    }
}
```

**Configuration Fields:**
- **Key** (e.g., `"filesystem"`): Friendly name for the server
- **`command`**: The executable command
- **`args`**: Command-line arguments (always include `--stdio`)
- **`enabled`**: Set to `False` to temporarily disable

### Step 4: Restart the Application

That's it! The new tools will be automatically discovered and available to agents.

### Step 5: Verify Tools Were Registered

Run the integration test to see all available tools:

```bash
python tests/test_mcp_integration.py
```

You should see your new tools listed alongside existing ones.

## Registry Changes (Technical Details)

### What Happens Automatically

When you add an MCP server to `settings.py`, the following happens **automatically** on application startup:

1. **Subprocess Spawned**: [`MCPClient`](file:///Users/mariusmoisescu/Projects/flexi-deep-research-langgraph/src/flexi/core/mcp_client.py) spawns the MCP server process with stdio pipes

2. **Tool Discovery**: Sends JSON-RPC `tools/list` request:
   ```json
   {
     "jsonrpc": "2.0",
     "method": "tools/list",
     "id": 1
   }
   ```

3. **Schema Parsing**: Receives tool schemas:
   ```json
   {
     "tools": [
       {
         "name": "get-forecast",
         "description": "Get weather forecast for a location",
         "inputSchema": {
           "type": "object",
           "properties": {
             "latitude": {"type": "number"},
             "longitude": {"type": "number"}
           },
           "required": ["latitude", "longitude"]
         }
       }
     ]
   }
   ```

4. **Wrapper Generation**: [`MCPToolManager`](file:///Users/mariusmoisescu/Projects/flexi-deep-research-langgraph/src/flexi/core/mcp_manager.py) creates Python functions:
   ```python
   def get_forecast(latitude: float, longitude: float) -> str:
       # Calls MCP server via JSON-RPC
       ...
   ```

5. **Registry Insertion**: Tools are registered in `ToolsRegistry` with metadata:
   ```python
   tools_registry.register(
       use_cases=["weather data", "forecasts"],
       output_quality="medium",
       latency="medium",
       cost="free",
       reliability="beta"
   )(get_forecast)
   ```

### No Manual Registry Edits Needed

Unlike native tools, you **do not** need to:
- ❌ Write wrapper functions manually
- ❌ Add `@tools_registry.register()` decorators
- ❌ Define parameter types
- ❌ Import anything in `tools.py`

Everything is **automatic** based on the MCP server's schema.

## Troubleshooting

### Server Won't Start

**Error:** `Failed to register MCP server 'xyz'`

**Solutions:**
1. Verify the server is installed: `which mcp-server-xyz`
2. Test manually: `mcp-server-xyz --stdio`
3. Check the command name in `settings.py` matches exactly

### Tools Not Appearing

**Check the logs:**
```bash
python tests/test_mcp_integration.py
```

Look for:
- `MCPToolManager initialized`
- `Registering MCP server: xyz`
- `Found N tools from 'xyz'`
- `Registered MCP tool: tool_name from xyz`

### Tools Called But Failing

**Error:** `MCP error: Invalid arguments`

**Cause:** The LLM is not providing required parameters.

**Solution:** Check the tool's description is clear. You can manually improve it by editing the MCP server's source or creating a custom wrapper.

## Example: Adding GitHub MCP Server

```bash
# 1. Install
npm install -g @modelcontextprotocol/server-github

# 2. Test
export GITHUB_TOKEN=your_token_here
mcp-server-github --stdio

# 3. Configure
# Edit settings.py:
MCP_SERVERS = {
    "weather": {...},
    "github": {
        "command": "mcp-server-github",
        "args": ["--stdio"],
        "enabled": True
    }
}

# 4. Set environment variable (if needed)
# Add to .env:
GITHUB_TOKEN=your_token_here

# 5. Restart and verify
python tests/test_mcp_integration.py
```

Now agents can query GitHub repos, issues, PRs, etc.!

## Available MCP Servers

Popular MCP servers you can integrate:
- **mcp-server-weather**: Weather forecasts and alerts
- **@modelcontextprotocol/server-filesystem**: Read/write files
- **@modelcontextprotocol/server-github**: GitHub API access
- **@modelcontextprotocol/server-postgres**: PostgreSQL queries
- **@modelcontextprotocol/server-sqlite**: SQLite queries
- **@modelcontextprotocol/server-google-maps**: Maps and geocoding

Find more at: [Awesome MCP Servers](https://github.com/punkpeye/awesome-mcp-servers)

## Security Considerations

- **Filesystem Access**: Be careful with filesystem servers - only allow access to safe directories
- **API Keys**: Store sensitive tokens in `.env`, not in `settings.py`
- **Untrusted Servers**: Only use MCP servers from trusted sources
- **Subprocess Management**: MCP servers run as subprocesses - they have the same permissions as your application

## Architecture

```
┌─────────────────┐
│   Application   │
│    Startup      │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│   MCPToolManager (Singleton)│
│   - Reads MCP_SERVERS       │
│   - Spawns subprocesses     │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│   MCPClient (per server)    │
│   - stdio communication     │
│   - JSON-RPC protocol       │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│   Tool Discovery            │
│   - tools/list request      │
│   - Parse schemas           │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│   Wrapper Generation        │
│   - Create Python functions │
│   - Set __annotations__     │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│   ToolsRegistry             │
│   - MCP tools + Native tools│
│   - Available to Architect  │
└─────────────────────────────┘
```

## Summary

**To add a new MCP server:**
1. Install it: `npm install -g mcp-server-xyz`
2. Add to `settings.py` under `MCP_SERVERS`
3. Restart the application

**That's it!** Tools are automatically discovered and available to agents.
