import operator
from typing import Dict, List, Optional, Any, Annotated
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage


def merge_findings(left: Dict[str, str], right: Dict[str, str]) -> Dict[str, str]:
    """Reducer for merging findings dictionaries."""
    new_findings = left.copy()
    new_findings.update(right)
    return new_findings


def merge_stats(left: List[Dict[str, Any]], right: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Reducer for usage stats."""
    if left is None: left = []
    if right is None: right = []
    return left + right


def increment_counter(left: int, right: int) -> int:
    """Reducer for counting completions. -1 acts as a reset signal."""
    if right == -1: return 0
    return (left or 0) + (right or 0)


def reduce_current_agent(left: str, right: str) -> str:
    """Reducer for current_agent: right (new) wins, fallback to left."""
    return right or left


def reduce_max_iterations(left: int, right: int) -> int:
    """Reducer for iteration_count: keeps the maximum value."""
    return max(left or 0, right or 0)


class ResearchState(TypedDict):
    """
    State maintained throughout the research workflow.
    Uses Annotated with reducers to handle concurrent updates.
    """
    research_question: str
    messages: Annotated[List[BaseMessage], operator.add]
    current_agent: Annotated[str, reduce_current_agent]
    supervisor_decision: Optional[str]
    findings: Annotated[Dict[str, str], merge_findings]
    stats: Annotated[List[Dict[str, Any]], merge_stats]
    final_report: Optional[str]
    iteration_count: Annotated[int, reduce_max_iterations]
    max_iterations: int
    next_tasks: List[Dict[str, Any]] # For parallel fan-out
    active_branches: int # Set by supervisor
    completed_branches: Annotated[int, increment_counter] # Incremented by researchers


def merge_tool_calls(left: List[Dict[str, Any]], right: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Reducer for tool calls history."""
    return left + right


class AdvancedResearchState(TypedDict):
    """Enhanced state with tool tracking and robust reducers."""
    research_question: str
    messages: Annotated[List[BaseMessage], operator.add]
    current_agent: Annotated[str, reduce_current_agent]
    current_agent_role: Optional[str]
    supervisor_decision: Optional[str]
    findings: Annotated[Dict[str, str], merge_findings]
    tool_calls_made: Annotated[List[Dict[str, Any]], merge_tool_calls]
