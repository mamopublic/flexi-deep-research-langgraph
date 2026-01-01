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
