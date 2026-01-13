from typing import Dict, List, Any

def calculate_task_completion(state: Dict[str, Any]) -> bool:
    """Check if the supervisor reached the END condition."""
    decision = state.get("supervisor_decision")
    # Also valid if we have a substantial 'writer' finding
    has_report = "writer" in state.get("findings", {})
    return decision == "END" or has_report

def calculate_tool_efficiency(stats: List[Dict[str, Any]]) -> float:
    """
    Calculate tool efficiency score (1-5).
    Simple heuristic: reward diversity and lack of immediate redundancy.
    """
    if not stats:
        return 5.0
    
    total_calls = 0
    # agents_count = 0 
    
    # Filter stats to exclude system roles for efficiency calc
    research_stats = [s for s in stats if s.get("agent") not in ["architect", "supervisor"]]
    
    if not research_stats:
        return 5.0
        
    for stat in research_stats:
        iterations = stat.get("iterations", 0)
        total_calls += iterations
    
    if total_calls == 0:
        return 5.0
        
    avg_iters = total_calls / len(research_stats)
    
    # Heuristic: 
    # > 4 iters/agent = 1.0 (Stuck in loops)
    # > 3 iters/agent = 2.0 (Inefficient)
    # > 2 iters/agent = 3.0 (Okay)
    # <= 2 iters/agent = 5.0 (Efficient/Surgical)
    
    if avg_iters > 4: return 1.0
    if avg_iters > 3: return 2.0
    if avg_iters > 2: return 3.0
    return 5.0

def calculate_hallucination_rate(report: str, judgment: Dict[str, Any]) -> float:
    """Derived from judge's feedback."""
    return judgment.get("hallucination_score", 0.0)

def calculate_all_metrics(state: Dict[str, Any], judgment: Dict[str, Any]) -> Dict[str, float]:
    """Aggregate all available metrics."""
    stats = state.get("stats", [])
    
    return {
        "task_completion": 1.0 if calculate_task_completion(state) else 0.0,
        "tool_efficiency": calculate_tool_efficiency(stats),
        "hallucination_rate": calculate_hallucination_rate("", judgment),
        "clarity": judgment.get("clarity_score", 0),
        "citation": judgment.get("citation_score", 0),
        "reasoning": judgment.get("reasoning_score", 0)
    }
