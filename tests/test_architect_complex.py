import pytest
from flexi.agents.architect import create_architect

def test_architect_complex_query():
    """Test architect with a complex comparison query."""
    question = "Compare the architectural differences between LangGraph, AutoGen, and CrewAI for building multi-agent systems."
    architect = create_architect()
    
    config = architect.design_system(question)
    
    roles = config.agents.keys()
    assert "supervisor" in roles
    # Should have roles for analysis or comparison
    assert len(config.agents) >= 3
    
    # Check if tools are assigned
    all_tools = []
    for agent in config.agents.values():
        all_tools.extend(agent.tools)
    
    assert len(all_tools) > 0
    assert "search_tavily" in all_tools or "search_serper" in all_tools
    print("Test passed!")

if __name__ == "__main__":
    test_architect_complex_query()
