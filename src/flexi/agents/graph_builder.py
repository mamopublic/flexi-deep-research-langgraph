from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, AIMessage

from flexi.core.state import ResearchState
from flexi.core.llm_provider import get_llm
from flexi.core.tools import tools_registry
from flexi.agents.architect import ArchitectConfig, AgentConfig
import re

def create_agent_executor(agent_config: AgentConfig, model_name: str) -> callable:
    """Create an executor function for a single agent."""
    llm = get_llm(model_name=model_name, temperature=0.5)
    
    tool_descriptions = "\n".join([
        f"- {name}: {tools_registry.metadata[name].description}"
        for name in agent_config.tools
        if name in tools_registry.metadata
    ])
    
    def agent_executor(state: ResearchState) -> Dict[str, Any]:
        tools_context = f"You have access to these tools:\n{tool_descriptions}" if agent_config.tools else "No tools available."
        
        full_system_prompt = f"""{agent_config.system_prompt}

RESEARCH QUESTION: {state['research_question']}

{tools_context}

Previous findings from other agents:
{_format_findings(state['findings'])}

Your task: Perform your role as a '{agent_config.role}' and provide substantive output.
When you are finished, your findings will be sent back to the supervisor.
"""
        messages = list(state['messages'])
        messages.append(HumanMessage(content=f"Continue as {agent_config.role}:\n{full_system_prompt}"))
        
        response = llm.invoke(messages)
        return {
            "messages": [AIMessage(content=response.content)],
            "findings": {agent_config.role: response.content},
            "current_agent": agent_config.role
        }
    return agent_executor

def create_supervisor_executor(agent_config: AgentConfig, subordinate_roles: List[str], model_name: str) -> callable:
    """Create a supervisor that decides who to call next."""
    llm = get_llm(model_name=model_name, temperature=0.3)
    
    def supervisor_executor(state: ResearchState) -> Dict[str, Any]:
        system_prompt = f"""{agent_config.system_prompt}

RESEARCH QUESTION: {state['research_question']}

AVAILABLE AGENTS: {', '.join(subordinate_roles)}

FINDINGS SO FAR:
{_format_findings(state['findings'])}

Decide who should act next. If the research is complete, say 'FINISH'. 
Otherwise, start your response with 'NEXT: [agent_name]' followed by your reasoning.
"""
        messages = list(state['messages'])
        messages.append(HumanMessage(content=system_prompt))
        
        response = llm.invoke(messages)
        content = response.content
        
        next_agent = None
        if "NEXT:" in content:
            match = re.search(r'NEXT:\s*(\w+)', content)
            if match:
                candidate = match.group(1).strip()
                if candidate in subordinate_roles:
                    next_agent = candidate
        
        if "FINISH" in content.upper() and not next_agent:
            next_agent = "END"
            
        return {
            "messages": [AIMessage(content=content)],
            "supervisor_decision": next_agent,
            "current_agent": "supervisor"
        }
    return supervisor_executor

def _format_findings(findings: Dict[str, str]) -> str:
    if not findings:
        return "(No previous findings yet)"
    formatted = ""
    for role, content in findings.items():
        formatted += f"\n[{role}]:\n{str(content)[:500]}...\n"
    return formatted

class DynamicResearchSystemBuilder:
    """Builds a LangGraph-based system from an ArchitectConfig."""
    
    def __init__(self, config: ArchitectConfig, model_name: str = "claude-3-5-sonnet-20241022"):
        self.config = config
        self.model_name = model_name
        self.graph = None
        self.agents = {}
    
    
    def _resolve_model_for_role(self, role: str) -> str:
        """Resolve the appropriate LLM model for a given role based on tiered config."""
        from flexi.config.settings import settings
        
        # Determine the tier for this role (default to medium if unknown)
        tier_name = settings.ROLE_MODEL_MAPPING.get(role, "medium")
        
        # Map tier name to actual model ID
        if tier_name == "advanced":
            return settings.LLM_MODEL_ADVANCED
        elif tier_name == "basic":
            return settings.LLM_MODEL_BASIC
        else:
            return settings.LLM_MODEL_MEDIUM

    def build(self) -> callable:
        supervisor_role = "supervisor"
        has_supervisor = supervisor_role in self.config.agents
        
        # Create executors
        for role, agent_config in self.config.agents.items():
            model_for_agent = self._resolve_model_for_role(role)
            if role == supervisor_role:
                subordinate_roles = [r for r in self.config.agents.keys() if r != supervisor_role]
                self.agents[role] = create_supervisor_executor(agent_config, subordinate_roles, model_for_agent)
            else:
                self.agents[role] = create_agent_executor(agent_config, model_for_agent)
        
        # Build graph
        builder = StateGraph(ResearchState)
        for role, executor in self.agents.items():
            builder.add_node(role, executor)
            
        if has_supervisor:
            # STAR TOPOLOGY: Supervisor orchestrates everything
            subordinate_roles = [r for r in self.config.agents.keys() if r != supervisor_role]
            
            builder.add_edge(START, supervisor_role)
            
            def router(state: ResearchState) -> str:
                decision = state.get("supervisor_decision")
                if decision == "END" or not decision:
                    return END
                return decision
                
            builder.add_conditional_edges(
                supervisor_role,
                router,
                {END: END, **{r: r for r in subordinate_roles}}
            )
            
            for role in subordinate_roles:
                builder.add_edge(role, supervisor_role)
        
        else:
            # SINGLE AGENT TOPOLOGY: START -> Agent -> END
            # We assume there is exactly one agent in this case (or picking the first one)
            if not self.agents:
                raise ValueError("No agents defined in configuration")
                
            sole_agent_role = list(self.agents.keys())[0]
            builder.add_edge(START, sole_agent_role)
            builder.add_edge(sole_agent_role, END)
            
        self.graph = builder.compile()
        return self.graph

    def run(self, research_question: str) -> ResearchState:
        if not self.graph:
            self.build()
            
        initial_state = {
            "research_question": research_question,
            "messages": [HumanMessage(content=research_question)],
            "current_agent": "START",
            "findings": {},
            "final_report": "",
            "supervisor_decision": None
        }
        return self.graph.invoke(initial_state)
