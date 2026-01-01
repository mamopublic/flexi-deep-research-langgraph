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
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "system_prompt": self.system_prompt,
            "tools": self.tools,
            "description": self.description,
            "template_used": self.template_used,
            "customization": self.customization
        }

@dataclass
class ArchitectConfig:
    """Configuration for the entire agent system, emitted by the architect."""
    research_question: str
    reasoning: str
    agents: Dict[str, AgentConfig] = field(default_factory=dict)
    supervisor_mandatory: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "research_question": self.research_question,
            "reasoning": self.reasoning,
            "agents": {role: config.to_dict() for role, config in self.agents.items()},
            "supervisor_mandatory": self.supervisor_mandatory
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

class ArchitectAgent:
    """The architect agent that designs multi-agent deep research systems."""
    
    def __init__(self, model_name: str = None):
        # Architect always uses the ADVANCED tier by default, as it's a crucial role
        self.model = model_name or settings.LLM_MODEL_ADVANCED
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
        response = self.llm.invoke(prompt)
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
        
        return self._parse_config_dict(config_dict, research_question)
    
    def _parse_config_dict(self, config_dict: Dict[str, Any], original_question: str) -> ArchitectConfig:
        # Check complexity to infer defaults if needed, though we trust the specific field
        supervisor_mandatory = config_dict.get("supervisor_mandatory", True)
        
        # For simple complexity, we might default supervisor_mandatory to False if not explicitly set?
        # But let's rely on what's in the dict or default to True.
        # Actually, if the LLM follows the 'simple' design (1 agent), it might omit supervisor_mandatory or set it to false.
        # Let's trust the boolean if present.
        
        architect_config = ArchitectConfig(
            research_question=original_question,
            reasoning=config_dict.get("reasoning", ""),
            supervisor_mandatory=supervisor_mandatory
        )
        
        agents_dict = config_dict.get("agents", {})
        for role_str, agent_dict in agents_dict.items():
            architect_config.agents[role_str] = AgentConfig(
                role=role_str,
                system_prompt=agent_dict.get("system_prompt", ""),
                tools=agent_dict.get("tools", []),
                description=agent_dict.get("description", ""),
                template_used=agent_dict.get("template_used"),
                customization=agent_dict.get("customization")
            )
        
        if architect_config.supervisor_mandatory and "supervisor" not in architect_config.agents:
            raise ValueError("Supervisor agent is mandatory but not present in config")
        
        return architect_config

def create_architect(model_name: str = None) -> ArchitectAgent:
    """Factory function to create an architect agent."""
    model = model_name or settings.LLM_MODEL_ADVANCED
    return ArchitectAgent(model_name=model)
