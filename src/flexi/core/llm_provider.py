import os
import logging
from typing import Optional
from langchain_core.language_models.base import BaseLanguageModel
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from pydantic import Field, SecretStr
from langchain_core.utils.utils import secret_from_env

from flexi.config.settings import settings

logger = logging.getLogger(__name__)


class ChatOpenRouter(ChatOpenAI):
    """ChatOpenRouter class for OpenRouter API integration."""
    
    openai_api_key: Optional[SecretStr] = Field(
        alias="api_key",
        default_factory=lambda: secret_from_env("OPENROUTER_API_KEY", default=None),
    )
    
    @property
    def lc_secrets(self) -> dict[str, str]:
        return {"openai_api_key": "OPENROUTER_API_KEY"}

    def __init__(self, openai_api_key: Optional[str] = None, **kwargs):
        openai_api_key = openai_api_key or settings.OPENROUTER_API_KEY
        super().__init__(
            base_url="https://openrouter.ai/api/v1",
            openai_api_key=openai_api_key,
            **kwargs
        )


def is_valid_key(api_key: Optional[str]) -> bool:
    """Check if the API key is set and not a placeholder."""
    return bool(api_key and "your_" not in api_key and "placeholder" not in api_key.lower())


def get_llm(model_name: str, 
            temperature: float = 0, 
            max_tokens: int = 4096) -> BaseLanguageModel:
    """
    Create a language model instance based on the model name,
    prioritizing OpenRouter if available.
    """
    openrouter_key = settings.OPENROUTER_API_KEY
    anthropic_key = settings.ANTHROPIC_API_KEY
    
    # 1. Try OpenRouter first
    if is_valid_key(openrouter_key):
        or_model_name = model_name
        # Map canonical Claude names to OpenRouter names if needed
        if model_name.startswith("claude-") and "/" not in model_name:
            if "3-5-sonnet" in model_name:
                or_model_name = "anthropic/claude-3.5-sonnet"
            elif "3-opus" in model_name:
                or_model_name = "anthropic/claude-3-opus"
            elif "3-haiku" in model_name:
                or_model_name = "anthropic/claude-3-haiku"
            else:
                or_model_name = f"anthropic/{model_name}"
        
        return ChatOpenRouter(
            model_name=or_model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            openai_api_key=openrouter_key
        )
    
    # 2. Fallback to Anthropic if applicable
    if model_name.startswith("claude") and is_valid_key(anthropic_key):
        return ChatAnthropic(
            model=model_name, 
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=anthropic_key
        )
    
    # 3. Error handling
    msg = f"Could not instantiate LLM for model '{model_name}'. Check your API keys."
    raise ValueError(msg)
