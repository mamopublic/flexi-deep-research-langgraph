import json
import logging
from flexi.agents.architect import create_architect
from flexi.agents.graph_builder import DynamicResearchSystemBuilder

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_end_to_end_medium():
    query = "Compare Python vs Rust for high-performance web backend development."
    logger.info(f"Starting end-to-end MEDIUM test with query: '{query}'")

    # 1. Design System
    logger.info("Step 1: Architect designing system...")
    architect = create_architect()
    config = architect.design_system(query)
    
    logger.info(f"Architecture designed. Agents: {list(config.agents.keys())}")
    
    # 2. Build and Run System
    logger.info("Step 2: Building and running research graph...")
    builder = DynamicResearchSystemBuilder(config)
    result_state = builder.run(query)
    
    # 3. Extract Results
    final_answer = result_state.get("final_report")
    if not final_answer:
        # Fallback to last message
        messages = result_state.get("messages", [])
        if messages:
            final_answer = messages[-1].content
        else:
            final_answer = "No response generated."

    # 4. Construct Output JSON
    output_data = {
        "query": query,
        "complexity": "medium",
        "architecture": config.to_dict(),
        "answer": final_answer
    }
    
    # Print JSON to stdout
    print("\n" + "="*50)
    print("FINAL OUTPUT JSON:")
    print("="*50)
    json_str = json.dumps(output_data, indent=2)
    print(json_str)
    print("="*50 + "\n")

    # Save to file
    output_filename = "medium_test_output.json"
    with open(output_filename, "w") as f:
        f.write(json_str)
    logger.info(f"Output saved to {output_filename}")

if __name__ == "__main__":
    test_end_to_end_medium()
