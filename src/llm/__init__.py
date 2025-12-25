"""
============================================================
MRD Agent - LLM Package
============================================================
Multi-LLM support for diverse AI models.

Supported Providers:
- OpenAI (GPT-4o, GPT-4o-mini)
- Google Gemini (gemini-1.5-pro, gemini-1.5-flash)
- Groq (llama-3.1-70b) [optional]
============================================================
"""

from src.llm.multi_llm import (
    call_llm,
    call_openai,
    call_gemini,
    synthesize_with_gemini,
    extract_structured_with_openai,
    get_llm_status,
    get_available_providers,
    LLMProvider,
    LLMTask,
    LLMResponse,
)

__all__ = [
    "call_llm",
    "call_openai",
    "call_gemini",
    "synthesize_with_gemini",
    "extract_structured_with_openai",
    "get_llm_status",
    "get_available_providers",
    "LLMProvider",
    "LLMTask",
    "LLMResponse",
]
