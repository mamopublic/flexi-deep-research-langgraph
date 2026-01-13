"""
Test MCP integration with the weather server.

Verifies that MCP tools are discovered and can be called successfully.
"""

import logging

# Configure logging to see MCP debug info
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_mcp_weather_tools():
    """Test that MCP weather tools are registered and callable."""
    print("\n" + "="*60)
    print("Testing MCP Weather Integration")
    print("="*60 + "\n")
    
    # Import tools registry (this triggers MCP discovery)
    from flexi.core.tools import tools_registry
    
    # List all registered tools
    print("All registered tools:")
    for name in tools_registry.tools.keys():
        print(f"  - {name}")
    
    print("\n" + "-"*60 + "\n")
    
    # Check for weather tools
    expected_tools = ["get_alerts", "get_forecast"]
    found_tools = []
    
    for tool_name in expected_tools:
        # MCP tools have hyphens converted to underscores
        python_name = tool_name.replace("-", "_")
        if python_name in tools_registry.tools:
            found_tools.append(python_name)
            print(f"✓ Found MCP tool: {python_name}")
            
            # Print metadata
            metadata = tools_registry.metadata.get(python_name)
            if metadata:
                print(f"  Description: {metadata.description}")
                print(f"  Parameters: {metadata.parameters}")
                print(f"  Use cases: {metadata.use_cases}")
        else:
            print(f"✗ Missing MCP tool: {python_name}")
    
    print("\n" + "-"*60 + "\n")
    
    # Test calling get_forecast
    if "get_forecast" in tools_registry.tools:
        print("Testing get_forecast tool...")
        get_forecast = tools_registry.get_tool("get_forecast")
        
        try:
            # San Francisco coordinates
            result = get_forecast(latitude=37.7749, longitude=-122.4194)
            print(f"✓ get_forecast executed successfully")
            print(f"Result preview: {str(result)[:200]}...")
        except Exception as e:
            print(f"✗ get_forecast failed: {e}")
    
    print("\n" + "-"*60 + "\n")
    
    # Test calling get_alerts
    if "get_alerts" in tools_registry.tools:
        print("Testing get_alerts tool...")
        get_alerts = tools_registry.get_tool("get_alerts")
        
        try:
            # California
            result = get_alerts(state="CA")
            print(f"✓ get_alerts executed successfully")
            print(f"Result preview: {str(result)[:200]}...")
        except Exception as e:
            print(f"✗ get_alerts failed: {e}")
    
    print("\n" + "="*60)
    print(f"Test Summary: Found {len(found_tools)}/{len(expected_tools)} expected tools")
    print("="*60 + "\n")

if __name__ == "__main__":
    test_mcp_weather_tools()
