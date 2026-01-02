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


class ResearchState(TypedDict):
    """
    State maintained throughout the research workflow.
    Uses Annotated with reducers to handle concurrent updates.
    """
    research_question: str
    messages: Annotated[List[BaseMessage], operator.add]
    current_agent: str
    supervisor_decision: Optional[str]
    findings: Annotated[Dict[str, str], merge_findings]
    stats: Annotated[List[Dict[str, Any]], merge_stats]
    final_report: Optional[str]


def merge_tool_calls(left: List[Dict[str, Any]], right: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Reducer for tool calls history."""
    return left + right


class AdvancedResearchState(TypedDict):
    """Enhanced state with tool tracking and robust reducers."""
    research_question: str
    messages: Annotated[List[BaseMessage], operator.add]
    current_agent: str
    current_agent_role: Optional[str]
    supervisor_decision: Optional[str]
    findings: Annotated[Dict[str, str], merge_findings]
    tool_calls_made: Annotated[List[Dict[str, Any]], merge_tool_calls]
