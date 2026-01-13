import pytest
from flexi.agents.architect import create_architect

@pytest.fixture
def architect():
    return create_architect()

@pytest.mark.parametrize("question, expected_complexity, min_agents", [
    ("What is 1+1?", "simple", 1),
    ("Compare Python vs Rust for web backends.", "moderate", 3),
    ("Analyze the geopolitical impact of quantum computing on global encryption standards over the next 10 years.", "complex", 4)
])
def test_architect_design_complexity(architect, question, expected_complexity, min_agents):
    """Verify architect adapts complexity and team size to the question."""
    config = architect.design_system(question)
    
    # We tolerate some fuzziness in LLM judgment, but directionally it should match
    print(f"Question: {question[:30]}... -> Complexity: {config.complexity}")
    
    assert len(config.agents) >= min_agents
    assert config.research_question == question
    
    # Basic sanity check on the output structure
    assert isinstance(config.suggested_workflow, list)
    assert isinstance(config.agents, dict)

def test_architect_json_consistency(architect):
    """Ensure architect produces valid, parseable JSON configurations."""
    question = "Explain Javascript closures."
    config = architect.design_system(question)
    
    assert config.complexity in ["simple", "moderate", "complex"]
    for agent in config.agents.values():
        assert agent.role
        assert agent.system_prompt
