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
    
    # Models
    # User requested "Advanced/Medium/Basic" tiers.
    # Currently mapping all to "claude-3-5-sonnet-20241022" (representing "3.7")
    LLM_MODEL_ADVANCED: str = "claude-sonnet-4"
    LLM_MODEL_MEDIUM: str = "claude-sonnet-4"
    LLM_MODEL_BASIC: str = "claude-sonnet-4"  # Could be Haiku later
    
    DEFAULT_MODEL: str = "claude-sonnet-4"
    OPENROUTER_MODEL_PREFIX: str = "anthropic/"
    
    # Role to Model Tier Mapping
    # Advanced: Architect, Supervisor
    # Medium: Researcher, Analyst, Clarifier, Summarizer, Custom
    # Basic: Writer
    ROLE_MODEL_MAPPING: Dict[str, str] = {
        "architect": "advanced",
        "supervisor": "advanced",
        "researcher": "medium",
        "analyst": "medium",
        "clarifier": "medium",
        "summarizer": "medium", 
        "writer": "basic"
    }

    # Context Management
    # If If True, subordinate agents receive curated context (saving tokens).
    # If False, they receive full conversation history.
    MANAGE_CONVERSATION: bool = True

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
    # Using Claude 3.5 Sonnet pricing as reference
    MODEL_COSTS: Dict[str, Dict[str, float]] = {
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
