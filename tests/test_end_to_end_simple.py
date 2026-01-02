import json
import sys
import logging
from flexi.agents.architect import create_architect
from flexi.agents.graph_builder import DynamicResearchSystemBuilder

# Configure logging to show what's happening
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_end_to_end_simple():
    query = "What is the capital of France?"
    logger.info(f"Starting end-to-end test with query: '{query}'")

    # 1. Design System
    logger.info("Step 1: Architect designing system...")
    architect = create_architect()
    config = architect.design_system(query)
    
    logger.info(f"Architecture designed. Complexity: {config.agents.keys()}")
    
    # 2. Build and Run System
    # 2. Build and Run System
    logger.info("Step 2: Building and running research graph (stream mode)...")
    builder = DynamicResearchSystemBuilder(config)
    
    final_state = None
    execution_sequence = []
    
    # Initialize stats with Architect's cost
    all_stats = []
    total_cost = 0.0
    
    if config.stats:
        all_stats.append(config.stats)
        archi_cost = config.stats.get("cost", 0.0)
        total_cost += archi_cost
        print(f"  -> ARCHITECT STATS: Cost=${archi_cost:.4f}, Duration={config.stats.get('duration', 0.0):.2f}s")

    print("\n" + "="*50)
    print("LIVE EXECUTION LOGS")
    print("="*50)
    
    for event in builder.stream(query):
        for node_name, updates in event.items():
            execution_sequence.append(node_name)
            print(f"\n[ACTOR]: {node_name.upper()}")
            
            if "stats" in updates:
                new_stats = updates["stats"]
                for stat in new_stats:
                    cost = stat.get("cost", 0.0)
                    duration = stat.get("duration", 0.0)
                    total_cost += cost
                    all_stats.append(stat)
                    print(f"  -> STATS: Cost=${cost:.4f}, Duration={duration:.2f}s")

            if "findings" in updates:
                current_findings = updates.get("findings", {})
                for role, content in current_findings.items():
                    if role == node_name:
                        preview = str(content)[:200].replace('\n', ' ')
                        print(f"  -> FINDING: {preview}...")
            
            if "messages" in updates:
                last_msg = updates["messages"][-1]
                content_preview = str(last_msg.content)[:100].replace('\n', ' ')
                print(f"  -> MESSAGE: {content_preview}...")

            final_state = updates

    print("="*50 + "\n")
    
    # 3. Extract Results
    final_answer = "No output."
    if final_state:
        if "messages" in final_state:
            final_answer = final_state["messages"][-1].content
    
    # 4. Construct Output JSON
    output_data = {
        "query": query,
        "architecture": config.to_dict(),
        "execution_sequence": execution_sequence,
        "total_cost": round(total_cost, 6),
        "execution_stats": all_stats,
        "answer": final_answer
    }
    
    # Print JSON to stdout for the user
    print("\n" + "="*50)
    print("FINAL OUTPUT JSON:")
    print("="*50)
    json_str = json.dumps(output_data, indent=2)
    print(json_str)
    print("="*50 + "\n")
    
    # Save to file
    output_filename = "simple_test_output.json"
    print(f"TOTAL BILL (Architect + Agents): ${total_cost:.4f}")
    with open(output_filename, "w") as f:
        f.write(json_str)
    logger.info(f"Output saved to {output_filename}")

    # Basic assertions to ensure it worked
    assert output_data["answer"] is not None
    assert len(output_data["architecture"]["agents"]) > 0

if __name__ == "__main__":
    test_end_to_end_simple()
