import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Project configuration settings."""
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None
    SERPER_API_KEY: Optional[str] = None
    JINA_API_KEY: Optional[str] = None
    
    # Tiered Model System (OpenRouter Slugs)
    LLM_MODEL_STRATEGIC: str = "anthropic/claude-sonnet-4"
    LLM_MODEL_ANALYTICAL: str = "anthropic/claude-haiku-4.5"
    LLM_MODEL_SYNTHESIS: str = "google/gemini-2.5-flash"
    
    DEFAULT_MODEL: str = "anthropic/claude-sonnet-4"
    OPENROUTER_MODEL_PREFIX: str = "anthropic/"
    
    # Role to Model Tier Mapping
    # Strategic: Roles that design, orchestrate, or gather new information
    # Analytical: Roles that process or analyze existing information
    # Synthesis: Roles that format or present information
    ROLE_MODEL_MAPPING: Dict[str, str] = {
        # Strategic Tier (Premium Models)
        "architect": "strategic",
        "supervisor": "strategic",
        "researcher": "strategic",  # Promoted - critical for quality
        
        # Analytical Tier (Mid-Tier Models)
        "analyst": "analytical",
        "clarifier": "analytical",
        
        # Synthesis Tier (Budget Models)
        "summarizer": "synthesis",
        "writer": "synthesis",
        "responder": "synthesis"
    }
    
    # Temperature Configuration by Role
    # Lower = more deterministic, Higher = more creative
    ROLE_TEMPERATURE_MAPPING: Dict[str, float] = {
        "architect": 0.3,      # Creative system design, controlled
        "supervisor": 0.2,     # Logical, deterministic delegation
        "researcher": 0.5,     # Creative search queries, balanced extraction
        "analyst": 0.3,        # Objective, analytical
        "clarifier": 0.4,      # Slight creativity for rephrasing
        "summarizer": 0.3,     # Factual condensation
        "writer": 0.6,         # More creative for engaging prose
        "responder": 0.2       # Direct factual answers
    }
    
    # Default temperature for roles not in mapping
    DEFAULT_TEMPERATURE: float = 0.5

    # Context Management
    # If True, subordinate agents receive curated context (saving tokens).
    # If False, they receive full conversation history.
    MANAGE_CONVERSATION: bool = True

    # Architect Customization Toggle
    ARCHITECT_ALLOW_CUSTOM_ROLES: bool = False
    ARCHITECT_MAX_CUSTOM_ROLES: int = 2

    # Chroma Knowledge Base Config
    CHROMA_DB_DIR: str = ".chroma_db"
    CHROMA_COLLECTION_NAME: str = "flexi_knowledge_base"
    
    # MCP Server Configuration
    MCP_SERVERS: Dict[str, Dict[str, Any]] = {
        "weather": {
            "command": "mcp-server-weather",
            "args": ["--stdio"],
            "enabled": True
        }
    }

    # Cost Configuration (Prices in USD per 1 Million Tokens)
    MODEL_COSTS: Dict[str, Dict[str, float]] = {
        "anthropic/claude-sonnet-4": {
            "input_cost_per_m": 3.00,
            "output_cost_per_m": 15.00
        },
        "anthropic/claude-haiku-4.5": {
            "input_cost_per_m": 1.00,
            "output_cost_per_m": 5.00
        },
        "google/gemini-2.5-flash": {
            "input_cost_per_m": 0.075,
            "output_cost_per_m": 0.30
        },
        # Legacy support keys
        "claude-3-5-sonnet-20241022": {
            "input_cost_per_m": 3.00,
            "output_cost_per_m": 15.00
        },
        # Fallback for unknown models
        "default": {
            "input_cost_per_m": 3.00,
            "output_cost_per_m": 15.00
        }
    }
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

def load_prompts() -> Dict[str, Any]:
    """Load prompts from YAML file."""
    prompts_path = Path(__file__).parent / "prompts.yaml"
    if not prompts_path.exists():
        raise FileNotFoundError(f"Prompts file not found at {prompts_path}")
    
    with open(prompts_path, "r") as f:
        return yaml.safe_load(f)

settings = Settings()
prompts = load_prompts()
