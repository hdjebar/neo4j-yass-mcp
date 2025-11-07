"""
LLM Configuration Module

Supports multiple LLM providers through LangChain:
- OpenAI
- Anthropic (Claude)
- Google Generative AI (Gemini)
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class LLMConfig:
    """Configuration for LLM providers"""

    provider: str  # "openai", "anthropic", or "google-genai"
    model: str
    temperature: float
    api_key: str
    streaming: bool = False  # Enable token-by-token streaming


def chatLLM(config: LLMConfig) -> Any:
    """
    Create a chat LLM instance based on the provider configuration.

    Args:
        config: LLMConfig containing provider, model, temperature, and API key

    Returns:
        A LangChain chat model instance

    Raises:
        ValueError: If the provider is not supported

    Examples:
        >>> config = LLMConfig(
        ...     provider="openai",
        ...     model="gpt-4",
        ...     temperature=0.0,
        ...     api_key="sk-..."
        ... )
        >>> llm = chatLLM(config)
    """
    if config.provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=config.model,
            temperature=config.temperature,
            openai_api_key=config.api_key,
            streaming=config.streaming,
        )

    elif config.provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=config.model,
            temperature=config.temperature,
            anthropic_api_key=config.api_key,
            streaming=config.streaming,
        )

    elif config.provider == "google-genai":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=config.model,
            temperature=config.temperature,
            google_api_key=config.api_key,
            streaming=config.streaming,
        )

    else:
        raise ValueError(
            f"Unknown provider: {config.provider}. Supported providers: openai, anthropic, google-genai"
        )
