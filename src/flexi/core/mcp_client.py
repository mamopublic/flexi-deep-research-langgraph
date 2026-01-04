"""
MCP Client for JSON-RPC stdio communication with Model Context Protocol servers.

Handles subprocess management, request/response handling, and tool discovery.
"""

import subprocess
import json
import threading
import queue
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MCPToolSchema:
    """Schema for an MCP tool."""
    name: str
    description: str
    input_schema: Dict[str, Any]


class MCPClient:
    """
    Client for communicating with an MCP server via stdio.
    
    Manages the subprocess lifecycle and JSON-RPC communication.
    """
    
    def __init__(self, command: str, args: List[str] = None):
        """
        Initialize MCP client and spawn the server process.
        
        Args:
            command: Command to run (e.g., "mcp-server-weather")
            args: Additional arguments (e.g., ["--stdio"])
        """
        self.command = command
        self.args = args or []
        self.process: Optional[subprocess.Popen] = None
        self.request_id = 0
        self.response_queue: queue.Queue = queue.Queue()
        self.reader_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        self._start_process()
    
    def _start_process(self):
        """Start the MCP server subprocess."""
        try:
            full_command = [self.command] + self.args
            logger.info(f"Starting MCP server: {' '.join(full_command)}")
            
            self.process = subprocess.Popen(
                full_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Start background thread to read responses
            self.reader_thread = threading.Thread(target=self._read_responses, daemon=True)
            self.reader_thread.start()
            
            logger.info(f"MCP server started successfully: {self.command}")
            
        except Exception as e:
            logger.error(f"Failed to start MCP server {self.command}: {e}")
            raise
    
    def _read_responses(self):
        """Background thread to read JSON-RPC responses from stdout."""
        try:
            while self.process and self.process.poll() is None:
                line = self.process.stdout.readline()
                if not line:
                    break
                
                try:
                    response = json.loads(line.strip())
                    self.response_queue.put(response)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse MCP response: {line.strip()} - {e}")
                    
        except Exception as e:
            logger.error(f"Error in MCP response reader: {e}")
    
    def send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Send a JSON-RPC request to the MCP server.
        
        Args:
            method: JSON-RPC method name (e.g., "tools/list", "tools/call")
            params: Method parameters
            
        Returns:
            Response from the server
        """
        with self._lock:
            self.request_id += 1
            request = {
                "jsonrpc": "2.0",
                "id": self.request_id,
                "method": method,
                "params": params or {}
            }
            
            try:
                # Send request
                request_line = json.dumps(request) + "\n"
                self.process.stdin.write(request_line)
                self.process.stdin.flush()
                
                # Wait for response (with timeout)
                import time
                timeout = 10  # seconds
                start_time = time.time()
                
                while time.time() - start_time < timeout:
                    try:
                        response = self.response_queue.get(timeout=0.1)
                        if response.get("id") == self.request_id:
                            if "error" in response:
                                raise Exception(f"MCP error: {response['error']}")
                            return response.get("result", {})
                    except queue.Empty:
                        continue
                
                raise TimeoutError(f"MCP request timed out: {method}")
                
            except Exception as e:
                logger.error(f"Error sending MCP request {method}: {e}")
                raise
    
    def list_tools(self) -> List[MCPToolSchema]:
        """
        Query the MCP server for available tools.
        
        Returns:
            List of tool schemas
        """
        try:
            result = self.send_request("tools/list")
            tools = result.get("tools", [])
            
            return [
                MCPToolSchema(
                    name=tool["name"],
                    description=tool.get("description", ""),
                    input_schema=tool.get("inputSchema", {})
                )
                for tool in tools
            ]
            
        except Exception as e:
            logger.error(f"Failed to list tools from MCP server: {e}")
            return []
    
    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute a tool on the MCP server.
        
        Args:
            name: Tool name
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        try:
            result = self.send_request("tools/call", {
                "name": name,
                "arguments": arguments
            })
            
            # MCP tools/call returns {"content": [...]}
            content = result.get("content", [])
            
            # Extract text from content blocks
            if content:
                # Content is a list of blocks, typically [{"type": "text", "text": "..."}]
                text_parts = []
                for block in content:
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                return "\n".join(text_parts) if text_parts else str(content)
            
            return str(result)
            
        except Exception as e:
            logger.error(f"Failed to call MCP tool {name}: {e}")
            return f"Error calling tool {name}: {str(e)}"
    
    def close(self):
        """Shutdown the MCP server process."""
        if self.process:
            try:
                self.process.stdin.close()
                self.process.terminate()
                self.process.wait(timeout=5)
                logger.info(f"MCP server {self.command} terminated")
            except Exception as e:
                logger.warning(f"Error closing MCP server: {e}")
                self.process.kill()
    
    def __del__(self):
        """Cleanup on garbage collection."""
        self.close()
