
import os
import sys
from typing import Optional
from langchain_core.messages import HumanMessage
from flexi.core.llm_provider import get_llm
from flexi.config.settings import settings

def test_model_connectivity(model_name: str):
    """Simple test to check if a model endpoint is reachable and responding."""
    print(f"\n--- Testing Connectivity: {model_name} ---")
    
    try:
        # We use a very low temperature and small max tokens for a quick check
        llm = get_llm(model_name=model_name, temperature=0, max_tokens=10)
        
        print(f"Instantiated LLM for: {model_name}")
        
        start_time = os.times().elapsed
        response = llm.invoke([HumanMessage(content="Say 'hi' in one word.")])
        end_time = os.times().elapsed
        
        print(f"SUCCESS: Received response in {end_time - start_time:.2f}s")
        print(f"Response: '{response.content.strip()}'")
        
    except Exception as e:
        print(f"FAILURE: Could not connect to {model_name}")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")

if __name__ == "__main__":
    # Test models from settings
    models_to_test = [
        settings.LLM_MODEL_STRATEGIC,
        settings.LLM_MODEL_ANALYTICAL,
        settings.LLM_MODEL_SYNTHESIS
    ]
    
    # Allow command line overrides
    if len(sys.argv) > 1:
        models_to_test = sys.argv[1:]
    
    for model in models_to_test:
        test_model_connectivity(model)
