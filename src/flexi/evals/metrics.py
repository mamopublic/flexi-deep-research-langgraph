from typing import Dict, List, Any

def calculate_task_completion(state: Dict[str, Any]) -> bool:
    """Check if the supervisor reached the END condition."""
    # In our graph_builder, we track the execution_sequence or supervisor_decision
    # For now, if we have a non-empty final_report or findings, we consider it a completion
    # A better check is looking at the 'messages' for a termination token or the decision
    decision = state.get("supervisor_decision")
    return decision == "END" or "writer" in state.get("findings", {})

def calculate_tool_efficiency(stats: List[Dict[str, Any]]) -> float:
    """
    Calculate tool efficiency score (1-5).
    Simple heuristic: reward diversity and lack of immediate redundancy.
    """
    if not stats:
        return 5.0
    
    total_calls = 0
    tools_used = set()
    
    for stat in stats:
        iterations = stat.get("iterations", 0)
        total_calls += iterations
        # We don't have the specific tool names in basic stats yet, 
        # but we can track iterations per agent.
    
    if total_calls == 0:
        return 5.0
        
    # Heuristic: if avg iterations per agent > 3, it might be inefficient looping
    avg_iters = total_calls / len([s for s in stats if s.get("agent") != "architect" and s.get("agent") != "supervisor"])
    if avg_iters > 4: return 2.0
    if avg_iters > 3: return 3.0
    return 5.0

def calculate_hallucination_rate(report: str, judgment: Dict[str, Any]) -> float:
    """Derived from judge's feedback."""
    return judgment.get("hallucination_score", 0.0)
