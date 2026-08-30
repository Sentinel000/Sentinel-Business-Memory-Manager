"""LLM configuration for Sentinel Agent Layer."""

from langchain_openai import ChatOpenAI

from app.config import settings


def get_llm(temperature: float = 0.1) -> ChatOpenAI:
    """Instantiate the ChatOpenAI client pointing to the Qwen API endpoint."""
    return ChatOpenAI(
        model=settings.agent_model,
        api_key=settings.qwen_api_key,
        base_url=settings.qwen_api_base,
        temperature=temperature,
        max_retries=2,
    )
