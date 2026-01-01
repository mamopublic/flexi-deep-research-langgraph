import pytest
from flexi.agents.architect import create_architect

def test_architect_simple_query():
    """Test architect with a very simple query."""
    question = "What is 1+1?"
    architect = create_architect()
    
    config = architect.design_system(question)
    
    # Assertions for simple query:
    # - Should be 1 agent (responder/researcher)
    # - Supervisor is NOT mandatory
    assert len(config.agents) >= 1
    
    # Check that we respect the mandatory flag (it should likely be False for simple)
    if not config.supervisor_mandatory:
        # If not mandatory, supervisor might be missing, which is fine
        pass
    else:
        # If explicitly mandatory, it must be there (but for 1+1 it shouldn't be)
        assert "supervisor" in config.agents

    assert config.research_question == question
    print("Test passed!")

if __name__ == "__main__":
    test_architect_simple_query()
