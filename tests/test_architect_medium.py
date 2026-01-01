import pytest
from flexi.agents.architect import create_architect

def test_architect_medium_query():
    """Test architect with a medium complexity query."""
    question = "What are the best practices for secure API design in 2024?"
    architect = create_architect()
    
    config = architect.design_system(question)
    
    # Needs explicit research
    roles = config.agents.keys()
    assert "supervisor" in roles
    # Should likely have a researcher or security expert
    assert any("research" in r.lower() or "security" in r.lower() for r in roles)
    print("Test passed!")

if __name__ == "__main__":
    test_architect_medium_query()
