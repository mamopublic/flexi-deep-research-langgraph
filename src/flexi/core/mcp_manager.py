"""
MCP Tool Manager for managing multiple MCP servers and registering their tools.

Handles tool discovery, wrapper creation, and integration with the ToolsRegistry.
"""

import logging
from typing import Dict, Any, List, Callable
from flexi.core.mcp_client import MCPClient, MCPToolSchema

logger = logging.getLogger(__name__)


class MCPToolManager:
    """
    Singleton manager for MCP servers and their tools.
    
    Discovers tools from MCP servers and registers them in the ToolsRegistry.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.servers: Dict[str, MCPClient] = {}
        self.tool_to_server: Dict[str, str] = {}  # Maps tool name to server name
        self._initialized = True
        logger.info("MCPToolManager initialized")
    
    def register_server(self, name: str, command: str, args: List[str] = None) -> bool:
        """
        Register and connect to an MCP server.
        
        Args:
            name: Friendly name for the server (e.g., "weather")
            command: Command to run (e.g., "mcp-server-weather")
            args: Additional arguments
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Registering MCP server '{name}': {command}")
            client = MCPClient(command, args)
            self.servers[name] = client
            logger.info(f"MCP server '{name}' registered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register MCP server '{name}': {e}")
            return False
    
    def discover_and_register_tools(self, tools_registry) -> int:
        """
        Discover tools from all registered MCP servers and register them.
        
        Args:
            tools_registry: The ToolsRegistry instance to register tools in
            
        Returns:
            Number of tools successfully registered
        """
        total_registered = 0
        
        for server_name, client in self.servers.items():
            try:
                logger.info(f"Discovering tools from MCP server '{server_name}'...")
                tool_schemas = client.list_tools()
                
                logger.info(f"Found {len(tool_schemas)} tools from '{server_name}'")
                
                for schema in tool_schemas:
                    try:
                        # Create wrapper function
                        wrapper = self._create_tool_wrapper(server_name, schema)
                        
                        # Map MCP schema to ToolMetadata
                        metadata = self._schema_to_metadata(schema, server_name)
                        
                        # Register with decorator pattern
                        decorated_wrapper = tools_registry.register(
                            use_cases=metadata["use_cases"],
                            output_quality=metadata["output_quality"],
                            latency=metadata["latency"],
                            cost=metadata["cost"],
                            reliability=metadata["reliability"],
                            best_for=metadata["best_for"],
                            avoid_when=metadata["avoid_when"]
                        )(wrapper)
                        
                        # Track mapping
                        self.tool_to_server[schema.name] = server_name
                        total_registered += 1
                        
                        logger.info(f"Registered MCP tool: {schema.name} from {server_name}")
                        
                    except Exception as e:
                        logger.error(f"Failed to register tool {schema.name}: {e}")
                        
            except Exception as e:
                logger.error(f"Failed to discover tools from '{server_name}': {e}")
        
        logger.info(f"Total MCP tools registered: {total_registered}")
        return total_registered
    
    def _create_tool_wrapper(self, server_name: str, schema: MCPToolSchema) -> Callable:
        """
        Create a Python function wrapper for an MCP tool with proper parameter annotations.
        
        Args:
            server_name: Name of the MCP server
            schema: Tool schema from MCP
            
        Returns:
            Callable wrapper function with __annotations__ for LangChain
        """
        # Extract parameter info from JSON schema
        properties = schema.input_schema.get("properties", {})
        required_params = schema.input_schema.get("required", [])
        
        # Build annotations dict for __annotations__
        annotations = {}
        for param_name, param_info in properties.items():
            param_type = param_info.get("type", "string")
            
            # Map JSON schema types to Python types
            if param_type == "number":
                annotations[param_name] = float
            elif param_type == "integer":
                annotations[param_name] = int
            elif param_type == "boolean":
                annotations[param_name] = bool
            else:
                annotations[param_name] = str
        
        annotations['return'] = str
        
        # Build parameter list for function signature
        params_list = []
        for param_name in properties.keys():
            if param_name in required_params:
                params_list.append(param_name)
            else:
                params_list.append(f"{param_name}=None")
        
        params_str = ", ".join(params_list)
        
        # Create function using exec to get proper signature
        func_code = f"""
def mcp_tool_wrapper({params_str}):
    '''Dynamically generated wrapper for MCP tool.'''
    client = manager.servers.get('{server_name}')
    if not client:
        return f"Error: MCP server '{server_name}' not available"
    
    kwargs = {{}}
"""
        for param_name in properties.keys():
            func_code += f"    if {param_name} is not None:\n"
            func_code += f"        kwargs['{param_name}'] = {param_name}\n"
        
        func_code += f"""
    try:
        result = client.call_tool('{schema.name}', kwargs)
        return result
    except Exception as e:
        return f"Error calling MCP tool {schema.name}: {{str(e)}}"
"""
        
        # Execute to create function
        local_vars = {'manager': self}
        exec(func_code, local_vars)
        tool_wrapper = local_vars['mcp_tool_wrapper']
        
        # Set metadata
        tool_wrapper.__name__ = schema.name.replace("-", "_")
        tool_wrapper.__doc__ = self._generate_docstring(schema, properties, required_params)
        tool_wrapper.__annotations__ = annotations
        
        return tool_wrapper
    
    def _generate_docstring(
        self, 
        schema: MCPToolSchema, 
        properties: Dict[str, Any], 
        required: List[str]
    ) -> str:
        """Generate a comprehensive docstring for the MCP tool wrapper."""
        lines = [schema.description, ""]
        
        if properties:
            lines.append("Parameters:")
            for param_name, param_info in properties.items():
                param_type = param_info.get("type", "any")
                param_desc = param_info.get("description", "")
                req_marker = " (required)" if param_name in required else " (optional)"
                lines.append(f"- {param_name} ({param_type}){req_marker}: {param_desc}")
        
        lines.append("")
        lines.append(f"Source: MCP tool '{schema.name}'")
        
        return "\n".join(lines)
    
    def _schema_to_metadata(self, schema: MCPToolSchema, server_name: str) -> Dict[str, Any]:
        """
        Map MCP tool schema to ToolMetadata fields.
        
        Args:
            schema: MCP tool schema
            server_name: Name of the server
            
        Returns:
            Dictionary with metadata fields
        """
        # Parse description for hints
        desc_lower = schema.description.lower()
        
        # Infer metadata from description keywords
        latency = "medium"
        if "fast" in desc_lower or "quick" in desc_lower:
            latency = "fast"
        elif "slow" in desc_lower:
            latency = "slow"
        
        cost = "cheap"
        if "expensive" in desc_lower or "paid" in desc_lower:
            cost = "expensive"
        elif "free" in desc_lower:
            cost = "free"
        
        # Default use cases based on server type
        use_cases = [f"mcp-{server_name}"]
        if "weather" in server_name.lower():
            use_cases = ["weather data", "forecasts", "alerts", "meteorology"]
        
        return {
            "use_cases": use_cases,
            "output_quality": "medium",  # Default, can be overridden
            "latency": latency,
            "cost": cost,
            "reliability": "beta",  # MCP tools are external, mark as beta
            "best_for": f"Accessing {server_name} data via MCP protocol",
            "avoid_when": "MCP server is unavailable or when native tools are sufficient"
        }
    
    def close_all(self):
        """Close all MCP server connections."""
        for name, client in self.servers.items():
            try:
                client.close()
                logger.info(f"Closed MCP server '{name}'")
            except Exception as e:
                logger.warning(f"Error closing MCP server '{name}': {e}")
        
        self.servers.clear()
        self.tool_to_server.clear()
    
    def __del__(self):
        """Cleanup on garbage collection."""
        self.close_all()
