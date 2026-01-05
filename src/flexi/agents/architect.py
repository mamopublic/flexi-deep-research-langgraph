from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import json
import re

from flexi.core.llm_provider import get_llm
from flexi.core.tools import tools_registry
from flexi.config.settings import prompts, settings

@dataclass
class AgentConfig:
    """Configuration for a single agent in the system."""
    role: str
    system_prompt: str
    tools: List[str] = field(default_factory=list)
    description: str = ""
    template_used: Optional[str] = None
    customization: Optional[Dict[str, Any]] = None
    context_dependencies: List[str] = field(default_factory=list) # Agents whose output this agent needs
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "system_prompt": self.system_prompt,
            "tools": self.tools,
            "description": self.description,
            "template_used": self.template_used,
            "customization": self.customization,
            "context_dependencies": self.context_dependencies
        }

import time

def _calculate_cost(model_name: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost based on model pricing (duplicate of graph_builder logic for independence)."""
    if model_name in settings.MODEL_COSTS:
        pricing = settings.MODEL_COSTS[model_name]
    else:
        pricing = settings.MODEL_COSTS["default"]
    
    input_cost = (input_tokens / 1_000_000) * pricing["input_cost_per_m"]
    output_cost = (output_tokens / 1_000_000) * pricing["output_cost_per_m"]
    return round(input_cost + output_cost, 6)

@dataclass
class ArchitectConfig:
    """Configuration for the entire agent system, emitted by the architect."""
    research_question: str
    reasoning: str
    agents: Dict[str, AgentConfig] = field(default_factory=dict)
    supervisor_mandatory: bool = True
    suggested_workflow: List[str] = field(default_factory=list) # Enhanced: Strategic plan
    complexity: str = "moderate"
    stats: Optional[Dict[str, Any]] = None # New stats field
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "research_question": self.research_question,
            "reasoning": self.reasoning,
            "agents": {role: config.to_dict() for role, config in self.agents.items()},
            "supervisor_mandatory": self.supervisor_mandatory,
            "suggested_workflow": self.suggested_workflow,
            "complexity": self.complexity,
            "stats": self.stats
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

class ArchitectAgent:
    """The architect agent that designs multi-agent deep research systems."""
    
    def __init__(self, model_name: str = None):
        # Architect always uses the STRATEGIC tier by default, as it's a crucial role
        self.model = model_name or settings.LLM_MODEL_STRATEGIC
        self.llm = get_llm(model_name=self.model, temperature=0.3)
        self.tool_names = list(tools_registry.tools.keys())
        self.tools_metadata_text = tools_registry.get_metadata_text()
    
    def _build_architect_prompt(self, research_question: str) -> str:
        """Build the system prompt using the configuration template."""
        template = prompts["architect"]["system_prompt_template"]
        role_templates = prompts.get("role_templates", {})
        
        # Format available role templates for the architect
        templates_text = ""
        for role, tmpl in role_templates.items():
            templates_text += f"TEMPLATE: {role}\n"
            templates_text += f"  Variables: {tmpl.get('variables', [])}\n"
            templates_text += f"  Base Prompt Preview: {tmpl.get('base_prompt', '')[:100].replace(chr(10), ' ')}...\n\n"
        
        return template.format(
            tool_catalog=self.tools_metadata_text,
            role_templates_text=templates_text,
            research_question=research_question
        )
    
    def design_system(self, research_question: str) -> ArchitectConfig:
        """Design a multi-agent system for the given research question."""
        prompt = self._build_architect_prompt(research_question)
        
        start_time = time.time()
        response = self.llm.invoke(prompt)
        end_time = time.time()
        duration = end_time - start_time
        
        # Extract usage
        usage = response.response_metadata.get("token_usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        cost = _calculate_cost(self.model, input_tokens, output_tokens)
        
        stats_record = {
            "agent": "architect",
            "model": self.model,
            "duration": round(duration, 2),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost
        }

        response_text = response.content.strip()
        
        try:
            # Handle markdown code blocks
            if "```" in response_text:
                json_match = re.search(r'```(?:json)?\n(.*?)\n```', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(1).strip()
                else:
                    response_text = response_text.replace("```json", "").replace("```", "").strip()
            
            config_dict = json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"Failed to parse architect response: {e}")
            raise
        
        config = self._parse_config_dict(config_dict, research_question)
        config.stats = stats_record
        return config
    
    def _parse_config_dict(self, config_dict: Dict[str, Any], original_question: str) -> ArchitectConfig:
        # Check complexity to infer defaults if needed, though we trust the specific field
        supervisor_mandatory = config_dict.get("supervisor_mandatory", True)
        
        architect_config = ArchitectConfig(
            research_question=original_question,
            reasoning=config_dict.get("reasoning", ""),
            supervisor_mandatory=supervisor_mandatory,
            suggested_workflow=config_dict.get("suggested_workflow", []),
            complexity=config_dict.get("complexity", "moderate")
        )
        
        # Defined default dependencies (Hybrid Model)
        default_dependencies = {
            "clarifier": [], # Only needs question
            "researcher": ["clarifier"], # Needs clarification
            "analyst": ["researcher"], # Needs research data
            "summarizer": ["researcher", "analyst"], # Needs findings and analysis
            "writer": ["summarizer"] # Needs synthesis
        }
        
        agents_dict = config_dict.get("agents", {})
        for name_key, agent_dict in agents_dict.items():
            # Standardize role identification
            # We strictly use the 'role' field as the identity key
            role_type = agent_dict.get("role", name_key)
            
            # Determine dependencies based on role type
            if role_type in default_dependencies:
                dependencies = default_dependencies[role_type]
            else:
                dependencies = agent_dict.get("context_dependencies", [])

            # COLLAPSE: Use role_type as the key, even if name_key was different
            architect_config.agents[role_type] = AgentConfig(
                role=role_type,
                system_prompt=agent_dict.get("system_prompt", ""),
                tools=agent_dict.get("tools", []),
                description=agent_dict.get("description", ""),
                template_used=agent_dict.get("template_used"),
                customization=agent_dict.get("customization"),
                context_dependencies=dependencies
            )
        
        # Inject Strategic Plan into Supervisor Prompt
        if architect_config.suggested_workflow and "supervisor" in architect_config.agents:
            supervisor_agent = architect_config.agents["supervisor"]
            
            # Format the workflow as a string
            workflow_text = "\n".join(architect_config.suggested_workflow)
            
            # Check if placeholder exists
            if "{suggested_workflow}" in supervisor_agent.system_prompt:
                supervisor_agent.system_prompt = supervisor_agent.system_prompt.replace(
                    "{suggested_workflow}", workflow_text
                )
            else:
                # Append if not present (and not already there in some other form)
                if "## STRATEGIC PLAN" not in supervisor_agent.system_prompt:
                    supervisor_agent.system_prompt += f"\n\n## STRATEGIC PLAN\nThe Architect has designed the following workflow for this specific team:\n{workflow_text}\n\nUse this as your primary guide."
        
        if architect_config.supervisor_mandatory and "supervisor" not in architect_config.agents:
            raise ValueError("Supervisor agent is mandatory but not present in config")
        
        return architect_config

def create_architect(model_name: str = None) -> ArchitectAgent:
    """Factory function to create an architect agent."""
    model = model_name or settings.LLM_MODEL_STRATEGIC
    return ArchitectAgent(model_name=model)
