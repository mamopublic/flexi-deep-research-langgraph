
import os
import time
import json
from flexi.agents.graph_builder import DynamicResearchSystemBuilder
from flexi.agents.architect import ArchitectConfig, AgentConfig

def test_deep_research_kb_flow():
    """
    Test a deep research flow that specifically requires accessing the 
    JavaScript and Engineering Standards knowledge bases.
    """
    research_question = (
        "Analyze the concept of 'closures' in JavaScript using the 'You Don't Know JS' knowledge base. "
        "Then, cross-reference this with Google's Engineering Practices regarding code readability and complexity. "
        "Synthesize a guideline on when to use closures effectively without harming readability."
    )
    
    print(f"\nXXX Starting Deep Research KB Test XXX\n")
    print(f"Research Question: {research_question}\n")
    
    # 1. Use Architect to design the system
    from flexi.agents.architect import create_architect
    print("Step 1: Architect designing system...")
    architect = create_architect()
    config = architect.design_system(research_question)
    print(f"Architecture designed. Agents: {list(config.agents.keys())}")
    
    # 2. Build and Run System (Streaming Mode)
    print("\nStep 2: Building and running research graph (Streaming Mode)...")
    builder = DynamicResearchSystemBuilder(config)
    
    total_cost = 0.0
    if config.stats:
        total_cost += config.stats.get("cost", 0.0)
    
    all_findings = {}
    execution_sequence = []
    
    print("\n" + "="*50)
    print("LIVE EXECUTION LOGS")
    print("="*50)
    
    for event in builder.stream(research_question):
        for node_name, updates in event.items():
            execution_sequence.append(node_name)
            print(f"\n[ACTOR]: {node_name.upper()}")
            
            # Accumulate Stats
            if "stats" in updates:
                for stat in updates["stats"]:
                    cost = stat.get("cost", 0.0)
                    total_cost += cost
                    print(f"  -> STATS: Cost=${cost:.4f}, Model={stat.get('model')}")
            
            # Accumulate Findings
            if "findings" in updates:
                current_findings = updates.get("findings", {})
                all_findings.update(current_findings)
                for role, content in current_findings.items():
                    if role == node_name:
                        preview = str(content)[:150].replace('\n', ' ')
                        print(f"  -> FINDING: {preview}...")
            
            # Print Supervisor Decision
            if "supervisor_decision" in updates:
                print(f"  -> DECISION: {updates['supervisor_decision']}")

    print("\n" + "="*50 + "\n")
    
    # 3. Extract and Save Report
    final_answer = "No output found."
    # Priority order for finding the "final" report
    for role in ["writer", "summarizer", "researcher"]:
        if role in all_findings:
            final_answer = all_findings[role]
            break
            
    print(f"TOTAL EXECUTION COST: ${total_cost:.4f}")
    
    # Save Report
    report_filename = "kb_test_report.md"
    with open(report_filename, "w") as f:
        f.write(final_answer)
    print(f"Full report saved to {report_filename}")
    
    # Save Stats/JSON for verification
    output_data = {
        "query": research_question,
        "total_cost": round(total_cost, 6),
        "execution_sequence": execution_sequence,
        "findings_keys": list(all_findings.keys())
    }
    with open("kb_test_output.json", "w") as f:
        json.dump(output_data, f, indent=2)
    print(f"Metadata saved to kb_test_output.json")

if __name__ == "__main__":
    test_deep_research_kb_flow()
