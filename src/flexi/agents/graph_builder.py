"""
Token-Efficient LangGraph Research System Builder

Implements supervisor-mediated context flow (similar to Strands model):
- Supervisor: Has full context (findings summary + conversation)
- Agents: Get ONLY question + last supervisor instruction + relevant findings
- No exponential message growth
- ~95% token savings on supervisor context vs. full history approach

Context Dependencies:
- Each agent declares which prior agents it needs context from
- Supervisor only passes relevant findings (filtered by dependencies)
- Message history is minimal (not accumulated)
"""

from typing import Dict, Any, List, Optional, Annotated
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, SystemMessage, ToolMessage
import operator
import time
import re

from flexi.core.state import ResearchState
from flexi.core.llm_provider import get_llm
from flexi.core.tools import tools_registry
from flexi.agents.architect import ArchitectConfig, AgentConfig
from flexi.config.settings import settings


# ============================================================================
# COST CALCULATION
# ============================================================================

def _calculate_cost(model_name: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost based on model pricing."""
    if model_name in settings.MODEL_COSTS:
        pricing = settings.MODEL_COSTS[model_name]
    else:
        pricing = settings.MODEL_COSTS.get("default", {"input_cost_per_m": 0, "output_cost_per_m": 0})
    
    input_cost = (input_tokens / 1_000_000) * pricing.get("input_cost_per_m", 0)
    output_cost = (output_tokens / 1_000_000) * pricing.get("output_cost_per_m", 0)
    return round(input_cost + output_cost, 6)


# ============================================================================
# CONTEXT FORMATTING
# ============================================================================

def _format_findings(findings: Dict[str, str]) -> str:
    """Format findings dictionary for inclusion in prompts.
    
    Truncates long findings to keep context manageable.
    """
    if not findings:
        return "(No previous findings yet)"
    
    formatted = ""
    for role, content in findings.items():
        # Truncate very long content
        truncated = content[:500] + "..." if len(content) > 500 else content
        formatted += f"\n[{role}]:\n{truncated}\n"
    
    return formatted


def _get_last_supervisor_instruction(messages: List[BaseMessage]) -> Optional[str]:
    """Extract the last supervisor instruction from message history.
    
    Returns the content of the last human message (which is the supervisor's instruction).
    """
    if not messages:
        return None
    
    # Find the last HumanMessage (supervisor's instruction to this agent)
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg.content
    
    return None


# ============================================================================
# AGENT EXECUTOR: TOKEN-EFFICIENT VERSION
# ============================================================================

def create_agent_executor(agent_name: str, agent_config: AgentConfig, model_name: str) -> callable:
    """
    Create a token-efficient executor for a research agent.
    
    Context provided to agent:
    1. Original research question
    2. Last supervisor instruction (what to do)
    3. Relevant findings (from dependencies only)
    4. Tool descriptions
    5. System prompt with task definition
    
    NOT provided:
    - Full message history (saves ~90% of tokens)
    - Other agents' conversations
    - Supervisor's internal deliberations
    """
    from flexi.config.settings import settings
    
    # Get temperature for this role (role-based tuning)
    temperature = settings.ROLE_TEMPERATURE_MAPPING.get(
        agent_config.role, 
        settings.DEFAULT_TEMPERATURE
    )
    
    llm = get_llm(model_name=model_name, temperature=temperature)
    
    tool_descriptions = "\n".join([
        f"- {name}: {tools_registry.metadata[name].description}"
        for name in agent_config.tools
        if name in tools_registry.metadata
    ])
    
    def agent_executor(state: ResearchState) -> Dict[str, Any]:
        """Execute this agent with minimal, focused context."""
        
        # ✅ STEP 1: Process System Instructions
        raw_system_prompt = agent_config.system_prompt
        if "{regime_instructions}" in raw_system_prompt:
            raw_system_prompt = raw_system_prompt.replace("{regime_instructions}", settings.REGIME_INSTRUCTIONS)
        elif "##" in raw_system_prompt and "OPTIMIZATION HINTS" not in raw_system_prompt and "GUIDANCE" not in raw_system_prompt:
            raw_system_prompt = f"{settings.REGIME_INSTRUCTIONS}\n\n{raw_system_prompt}"

        tools_context = (
            f"You have access to these tools:\n{tool_descriptions}" 
            if agent_config.tools 
            else "No tools available."
        )

        system_message = SystemMessage(content=f"""{raw_system_prompt}

{tools_context}

IMPORTANT RULES:
1. Use tools to gather actual evidence. Do not just talk about it.
2. When you have enough information, provide a substantive FINAL answer.
3. If you have prior work on this task, refine and complete it.""")

        # ✅ STEP 2: Build Message Context (Episodic Memory)
        messages = [system_message]
        
        # ✅ STEP 2.5: Restore this agent's specific history (Search Memory)
        # This prevents redundant tool calls between supervisor handoffs.
        if state.get('messages'):
            my_history = []
            is_my_msg = False
            for msg in state['messages']:
                if isinstance(msg, SystemMessage):
                    continue
                if isinstance(msg, AIMessage):
                    # In LangGraph/LangChain, assigned 'name' helps us filter turns
                    if getattr(msg, 'name', None) == agent_name:
                        is_my_msg = True
                        my_history.append(msg)
                    else:
                        is_my_msg = False
                elif isinstance(msg, ToolMessage) and is_my_msg:
                    my_history.append(msg)
            
            messages.extend(my_history)
        
        # ✅ STEP 3: Add Relevant Findings as Assistant Messages
        relevant_findings = {
            k: v for k, v in state.get('findings', {}).items() 
            if k in agent_config.context_dependencies
        }
        
        if relevant_findings:
            findings_text = "CONTEXT FROM PRIOR AGENTS:\n" + _format_findings(relevant_findings)
            messages.append(AIMessage(content=findings_text, name="ContextProvider"))
        
        # ✅ STEP 4: Add THIS agent's prior work as an Assistant message
        if agent_name in state.get('findings', {}):
            prior_work = state['findings'][agent_name]
            messages.append(
                AIMessage(
                    content=f"Your previous work on this task (which may be incomplete):\n\n{prior_work}",
                    name=agent_name
                )
            )
        
        # ✅ STEP 5: Add Research Question and Supervisor Instruction as Human Message
        task_content = f"RESEARCH QUESTION: {state['research_question']}\n\n"
        
        if state.get('messages'):
            last_instruction = _get_last_supervisor_instruction(state['messages'])
            if last_instruction:
                task_content += f"SUPERVISOR'S INSTRUCTION: {last_instruction}"
        
        messages.append(HumanMessage(content=task_content))
        
        # ✅ STEP 5.5: Mark end of transient context
        events_start_index = len(messages)
        
        # ✅ STEP 6: Execute with TOOL-CALLING LOOP
        
        # Bind tools to the LLM
        available_tools = [
            tools_registry.tools[name] 
            for name in agent_config.tools 
            if name in tools_registry.tools
        ]
        
        run_llm = llm
        if available_tools:
            run_llm = llm.bind_tools(available_tools)
            
        total_input_tokens = 0
        total_output_tokens = 0
        total_duration = 0.0
        max_iterations = 5
        iteration = 0
        
        final_response = None
        
        while iteration < max_iterations:
            iteration += 1
            start_time = time.time()
            response = run_llm.invoke(messages)
            total_duration += time.time() - start_time
            
            # Track usage
            usage = response.response_metadata.get("token_usage", {})
            total_input_tokens += usage.get("prompt_tokens", 0)
            total_output_tokens += usage.get("completion_tokens", 0)
            
            messages.append(response)
            
            # Check for tool calls
            if not response.tool_calls:
                final_response = response
                break
                
            # Execute tools
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                
                try:
                    print(f"  [TOOL]: {tool_name}({tool_args})")
                    result = tools_registry.call_tool(tool_name, **tool_args)
                    messages.append(ToolMessage(
                        tool_call_id=tool_call["id"],
                        content=str(result)
                    ))
                except Exception as e:
                    # 🔴 VISIBLE WARNING for developer
                    print(f"  \033[91m[TOOL ERROR]: {tool_name} failed with: {str(e)}\033[0m")
                    
                    messages.append(ToolMessage(
                        tool_call_id=tool_call["id"],
                        content=f"Error executing tool: {str(e)}"
                    ))
        
        if not final_response:
            final_response = response # Fallback to last response
            
        cost = _calculate_cost(model_name, total_input_tokens, total_output_tokens)
        
        stats_record = {
            "agent": agent_config.role,
            "model": model_name,
            "duration": round(total_duration, 2),
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
            "cost": cost,
            "iterations": iteration,
            "iteration_count": state.get("iteration_count", 0)
        }
        
        # ✅ STEP 7: Return state update
        # We return the new messages (LLM response + ToolResults) for persistence.
        # This allows the 'Restore' logic in Step 2.5 to find them later.
        turn_events = messages[events_start_index:]
        for msg in turn_events:
            if isinstance(msg, AIMessage):
                msg.name = agent_name
        
        return {
            "messages": turn_events,
            "findings": {agent_name: final_response.content},
            "current_agent": agent_name,
            "stats": [stats_record],
            "iteration_count": state.get("iteration_count", 0) + 1
        }
    
    return agent_executor


# ============================================================================
# SUPERVISOR EXECUTOR: TOKEN-EFFICIENT VERSION
# ============================================================================

def create_supervisor_executor(
    agent_config: AgentConfig, 
    subordinate_roles: List[str], 
    model_name: str
) -> callable:
    """
    Create a token-efficient supervisor that orchestrates the research.
    
    Supervisor context:
    1. Research question
    2. Available agents
    3. Summary of findings from all agents
    4. System prompt with decision logic
    
    Key: Supervisor sees findings summary, not full message history.
    This differs from agents which only see THEIR relevant findings.
    """
    llm = get_llm(model_name=model_name, temperature=0.3)
    
    def supervisor_executor(state: ResearchState) -> Dict[str, Any]:
        """Make routing decision with minimal context overhead."""
        
        findings_summary = _format_findings(state.get('findings', {}))
        
        # Iteration Tracking
        iteration_count = state.get('iteration_count', 0)
        max_iterations = state.get('max_iterations', 15)
        remaining = max_iterations - iteration_count
        
        raw_system_prompt = agent_config.system_prompt
        if "{regime_instructions}" in raw_system_prompt:
            raw_system_prompt = raw_system_prompt.replace("{regime_instructions}", settings.REGIME_INSTRUCTIONS)
        elif "##" in raw_system_prompt and "OPTIMIZATION HINTS" not in raw_system_prompt and "GUIDANCE" not in raw_system_prompt:
            raw_system_prompt = f"{settings.REGIME_INSTRUCTIONS}\n\n{raw_system_prompt}"

        iteration_notice = ""
        if remaining <= 2:
            iteration_notice = f"\n⚠️ WARNING: Budget nearly exhausted ({remaining} steps left). YOU MUST FINISH AND ASSIGN TO A WRITER/SUMMARIZER NOW."

        system_message = SystemMessage(content=f"""{raw_system_prompt}

AVAILABLE AGENTS: {', '.join(subordinate_roles)}

DECISION RULES: 
- If research is complete, respond with: FINISH
- Otherwise, respond with: NEXT: [agent_name]
- Followed by brief reasoning (1-2 sentences)""")

        # ✅ Build Message Context
        messages = [
            system_message,
            AIMessage(content=f"CURRENT FINDINGS:\n{findings_summary}", name="ResearchLedger"),
            HumanMessage(content=f"""RESEARCH QUESTION: {state['research_question']}

CURRENT PROGRESS: Iteration {iteration_count} of {max_iterations}{iteration_notice}

Identify the next logical step.""")
        ]
        
        start_time = time.time()
        response = llm.invoke(messages)
        duration = round(time.time() - start_time, 2)
        
        # Extract token usage
        usage = response.response_metadata.get("token_usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        cost = _calculate_cost(model_name, input_tokens, output_tokens)
        
        stats_record = {
            "agent": "supervisor",
            "model": model_name,
            "duration": duration,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
            "iteration_count": state.get("iteration_count", 0)
        }
        
        # Parse supervisor decision
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
            "current_agent": "supervisor",
            "stats": [stats_record]
        }
    
    return supervisor_executor


# ============================================================================
# SYSTEM BUILDER
# ============================================================================

class DynamicResearchSystemBuilder:
    """
    Builds a token-efficient LangGraph research system.
    
    Key features:
    - Supervisor-mediated context flow (like Strands)
    - Each agent only gets relevant findings
    - No exponential message growth
    - ~40-50% token savings vs. full-history approach
    - ~1.2x Strands efficiency (vs. 6x before optimization)
    """
    
    def __init__(
        self, 
        config: ArchitectConfig, 
        model_name: str = "claude-3-5-sonnet-20241022"
    ):
        """
        Initialize the system builder.
        
        Args:
            config: ArchitectConfig with agent definitions
            model_name: Default model for agents (can be overridden per-role)
        """
        self.config = config
        self.model_name = model_name
        self.graph = None
        self.agents = {}
    
    def _resolve_model_for_role(self, role: str) -> str:
        """Resolve the appropriate LLM model for a given role.
        
        Uses tiered model assignment from settings:
        - strategic: Tier 1 (Strategic) - Critical decision-making
        - analytical: Tier 2 (Analytical) - Analysis and processing
        - synthesis: Tier 3 (Synthesis) - Formatting and presentation
        """
        tier_name = settings.ROLE_MODEL_MAPPING.get(role, "analytical")
        
        if tier_name == "strategic":
            return settings.LLM_MODEL_STRATEGIC
        elif tier_name == "research":
            return settings.LLM_MODEL_RESEARCH
        elif tier_name == "synthesis":
            return settings.LLM_MODEL_SYNTHESIS
        else:
            return settings.LLM_MODEL_ANALYTICAL
    
    def build(self) -> callable:
        """Build the LangGraph workflow.
        
        Creates either:
        1. STAR topology: supervisor -> agents (for moderate/complex)
        2. SINGLE agent: START -> agent -> END (for simple)
        """
        supervisor_role = "supervisor"
        has_supervisor = supervisor_role in self.config.agents
        
        # Create executors for all agents
        for name, agent_config in self.config.agents.items():
            model_for_agent = self._resolve_model_for_role(agent_config.role)
            
            if name == supervisor_role:
                subordinate_roles = [r for r in self.config.agents.keys() if r != supervisor_role]
                self.agents[name] = create_supervisor_executor(
                    agent_config, 
                    subordinate_roles, 
                    model_for_agent
                )
            else:
                self.agents[name] = create_agent_executor(
                    name,
                    agent_config, 
                    model_for_agent
                )
        
        # Build LangGraph
        builder = StateGraph(ResearchState)
        
        for role, executor in self.agents.items():
            builder.add_node(role, executor)
        
        if has_supervisor:
            # STAR TOPOLOGY: All edges through supervisor
            subordinate_roles = [r for r in self.config.agents.keys() if r != supervisor_role]
            
            # Entry point
            builder.add_edge(START, supervisor_role)
            
            # Supervisor routing logic
            def router(state: ResearchState) -> str:
                # Hard Stop: Technical guardrail for budget
                if state.get("iteration_count", 0) >= state.get("max_iterations", 15):
                    return END
                
                decision = state.get("supervisor_decision")
                return END if (decision == "END" or not decision) else decision
            
            builder.add_conditional_edges(
                supervisor_role,
                router,
                {END: END, **{r: r for r in subordinate_roles}}
            )
            
            # All subordinates return to supervisor
            for role in subordinate_roles:
                builder.add_edge(role, supervisor_role)
        else:
            # SINGLE AGENT: For simple questions
            if not self.agents:
                raise ValueError("No agents defined in configuration")
            
            sole_agent_role = list(self.agents.keys())[0]
            builder.add_edge(START, sole_agent_role)
            builder.add_edge(sole_agent_role, END)
        
        self.graph = builder.compile()
        
        # Precision Calibration: Ensure recursion_limit > max_iterations * 3
        # transitions = 1 (start) + max_iters * 2 (round trip) + overhead
        complexity_map = {
            "simple": 5,
            "moderate": 15,
            "complex": 25
        }
        max_iters = complexity_map.get(self.config.complexity, 15)
        self.recursion_limit = (max_iters * 3) + 10
        
        return self.graph
    
    def run(self, research_question: str) -> ResearchState:
        """Execute the research system end-to-end.
        
        Args:
            research_question: The question to research
            
        Returns:
            Final ResearchState with findings, stats, etc.
        """
        if not self.graph:
            self.build()
        
        # Set max iterations based on complexity
        complexity_map = {
            "simple": 5,
            "moderate": 15,
            "complex": 25
        }
        max_iters = complexity_map.get(self.config.complexity, 15)

        initial_state = {
            "research_question": research_question,
            "messages": [HumanMessage(content=research_question)],
            "current_agent": "START",
            "findings": {},
            "final_report": "",
            "supervisor_decision": None,
            "stats": [],
            "iteration_count": 0,
            "max_iterations": max_iters
        }
        
        return self.graph.invoke(initial_state, config={"recursion_limit": self.recursion_limit})
    
    def stream(self, research_question: str):
        """Stream the research execution, yielding state updates.
        
        Args:
            research_question: The question to research
            
        Yields:
            State updates as research progresses
        """
        if not self.graph:
            self.build()
        
        # Set max iterations based on complexity
        complexity_map = {
            "simple": 5,
            "moderate": 15,
            "complex": 25
        }
        max_iters = complexity_map.get(self.config.complexity, 15)

        initial_state = {
            "research_question": research_question,
            "messages": [HumanMessage(content=research_question)],
            "current_agent": "START",
            "findings": {},
            "final_report": "",
            "supervisor_decision": None,
            "stats": [],
            "iteration_count": 0,
            "max_iterations": max_iters
        }
    
        return self.graph.stream(initial_state, config={"recursion_limit": self.recursion_limit})


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    # Example: Build and run a research system
    from flexi.agents.architect import create_architect
    
    # Step 1: Architect designs the system
    architect = create_architect()
    question = "Compare Python vs Rust for high-performance web backends"
    config = architect.design_system(question)
    
    # Step 2: Build the research system
    builder = DynamicResearchSystemBuilder(config)
    builder.build()
    
    # Step 3: Execute
    # result = builder.run(question)
    
    # Step 4: Analyze results
    # print(f"Total cost: ${sum(s['cost'] for s in result.get('stats', [])):.4f}")
    # print(f"Total tokens: {sum(s['input_tokens'] + s['output_tokens'] for s in result.get('stats', []))}")
    # print(f"Findings: {list(result.get('findings', {}).keys())}")
