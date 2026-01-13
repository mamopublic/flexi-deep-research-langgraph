import pytest
import logging
from flexi.agents.architect import create_architect
from flexi.agents.graph_builder import DynamicResearchSystemBuilder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_system_for_query(query: str):
    """Helper to run a full E2E cycle."""
    logger.info(f"Running E2E for: '{query}'")
    
    # 1. Design
    architect = create_architect()
    config = architect.design_system(query)
    
    # 2. Build
    builder = DynamicResearchSystemBuilder(config)
    
    # 3. Run (collect final state)
    state = builder.run(query)
    
    return config, state

@pytest.mark.integration
def test_e2e_simple_flow():
    """Test a simple query (should be fast, low cost)."""
    query = "What is the capital of France?"
    config, state = run_system_for_query(query)
    
    assert len(config.agents) >= 1
    # Check for *some* output
    findings = state.get("findings", {})
    assert findings, "No findings recorded"
    
    # Simple flow usually has a responder or researcher
    has_content = any(len(f) > 10 for f in findings.values())
    assert has_content, "Findings were empty"

@pytest.mark.integration
def test_e2e_moderate_flow():
    """Test a multi-agent flow (Supervisor + Researcher + Writer)."""
    # Using a slightly complex query to force Moderate complexity
    query = "Summarize the key differences between Python 3.11 and 3.12 performance."
    config, state = run_system_for_query(query)
    
    assert config.complexity in ["moderate", "complex"]
    assert "supervisor" in config.agents
    
    findings = state.get("findings", {})
    # Should have research notes AND a summary/report
    assert len(findings) >= 2 

    if "writer" in findings:
        assert len(findings["writer"]) > 100, "Writer report too short"

if __name__ == "__main__":
    test_e2e_simple_flow()
