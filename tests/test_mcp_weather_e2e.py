import json
import logging
from flexi.agents.architect import create_architect
from flexi.agents.graph_builder import DynamicResearchSystemBuilder

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_mcp_weather_e2e():
    """
    End-to-end test using MCP weather tools.
    
    Tests that the Architect can design a system that uses MCP tools,
    and that agents can successfully call them during research.
    """
    query = "What is the current weather forecast for San Francisco, CA? Are there any active weather alerts?"
    logger.info(f"Starting MCP Weather E2E test with query: '{query}'")

    # 1. Design System
    logger.info("Step 1: Architect designing system...")
    architect = create_architect()
    config = architect.design_system(query)
    
    logger.info(f"Architecture designed. Agents: {list(config.agents.keys())}")
    
    # 2. Build and Run System
    logger.info("Step 2: Building and running research graph (Streaming Mode)...")
    builder = DynamicResearchSystemBuilder(config)
    
    # Store state and sequence
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

    all_findings = {}
    
    print("\n" + "="*50)
    print("LIVE EXECUTION LOGS")
    print("="*50)
    
    for event in builder.stream(query):
        # Event is a dict like {'node_name': {'key': 'new_value'}}
        for node_name, updates in event.items():
            execution_sequence.append(node_name)
            print(f"\n[ACTOR]: {node_name.upper()}")
            
            # Use 'stats' if present to print usage
            if "stats" in updates:
                new_stats = updates["stats"]
                for stat in new_stats:
                    cost = stat.get("cost", 0.0)
                    duration = stat.get("duration", 0.0)
                    agent = stat.get("agent", "unknown")
                    model = stat.get("model", "unknown")
                    tool_iters = stat.get("tool_iterations", 0)
                    
                    # Accumulate
                    total_cost += cost
                    all_stats.append(stat)
                    
                    print(f"  -> STATS: Cost=${cost:.4f}, Duration={duration:.2f}s, Model={model}, ToolCalls={tool_iters}")
            
            # Print decision if from supervisor
            if "supervisor_decision" in updates:
                decision = updates['supervisor_decision']
                print(f"  -> DECISION: {decision}")
                if decision:
                    print(f"  -> Next Agent: {decision}")
            
            # Print findings if any
            if "findings" in updates:
                current_findings = updates.get("findings", {})
                all_findings.update(current_findings) # Accumulate findings
                for role, content in current_findings.items():
                    if role == node_name:
                        preview = str(content)[:200].replace('\n', ' ')
                        print(f"  -> FINDING: {preview}...")
            
            # Print last message content if any
            if "messages" in updates:
                last_msg = updates["messages"][-1]
                content_preview = str(last_msg.content)[:100].replace('\n', ' ')
                print(f"  -> MESSAGE: {content_preview}...")

            # Update final state tracker
            final_state = updates

    print("="*50 + "\n")
    
    # 3. Extract Results
    final_answer = "No output."
    
    # Try to get the "writer" output specifically from ACCUMULATED findings
    if "writer" in all_findings:
        final_answer = all_findings["writer"]
    # Fallback to summarizer if writer not found
    elif "summarizer" in all_findings:
        final_answer = all_findings["summarizer"]
    # Fallback to researcher if it's a simple flow
    elif "researcher" in all_findings:
        final_answer = all_findings["researcher"]

    # If still empty, try the last message from the chain
    if final_answer == "No output." and final_state:
        if "messages" in final_state:
             final_answer = final_state["messages"][-1].content
    
    logger.info("Stream finished. Preparing output.")

    # 4. Construct Output JSON
    output_data = {
        "query": query,
        "complexity": "simple",
        "test_type": "mcp_weather",
        "architecture": config.to_dict(),
        "execution_sequence": execution_sequence,
        "total_cost": round(total_cost, 6),
        "execution_stats": all_stats,
        "final_report_preview": final_answer[:500] + "..."
    }
    
    # Print JSON to stdout
    print("\n" + "="*50)
    print("FINAL OUTPUT JSON:")
    print("="*50)
    json_str = json.dumps(output_data, indent=2)
    print(json_str)
    print("="*50)
    
    print(f"\nTOTAL BILL (Architect + Agents): ${total_cost:.4f}")
    print("="*50 + "\n")

    # Save JSON config
    output_filename = "mcp_weather_test_output.json"
    with open(output_filename, "w") as f:
        f.write(json_str)
    logger.info(f"Output saved to {output_filename}")
    
    # Save Full Report
    report_filename = "mcp_weather_test_report.md"
    with open(report_filename, "w") as f:
        f.write(final_answer)
    logger.info(f"Full report saved to {report_filename}")
    
    # Verify MCP tools were used
    print("\n" + "="*50)
    print("MCP TOOL USAGE VERIFICATION")
    print("="*50)
    
    # Check if weather data appears in findings
    weather_keywords = ["forecast", "temperature", "alert", "weather", "wind"]
    found_keywords = []
    
    for keyword in weather_keywords:
        if keyword.lower() in final_answer.lower():
            found_keywords.append(keyword)
    
    if found_keywords:
        print(f"✓ Weather data detected in output: {', '.join(found_keywords)}")
        print("✓ MCP tools likely used successfully")
    else:
        print("⚠ No weather-specific data detected in output")
        print("⚠ MCP tools may not have been called")
    
    print("="*50 + "\n")

if __name__ == "__main__":
    test_mcp_weather_e2e()
