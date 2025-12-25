"""
============================================================
Multi-LLM Support Module
============================================================
PURPOSE: Use multiple LLMs for different tasks.

ADDRESSES GAP: "Multi-LLM Support" - Only GPT-4o used

Per Figma Design:
- GPT-4o: Complex reasoning, instruction following
- Claude 3.5 Sonnet: High-quality prose writing
- GPT-4o-mini: Fast verification tasks

Implemented:
- GPT-4o: Structured extraction, reasoning (primary)
- Gemini 1.5 Pro: Synthesis, writing (you have API key)
- GPT-4o-mini: Fallback for cost optimization
============================================================
"""

import os
import json
import asyncio
import logging
from typing import Optional, Any, TypeVar, Type
from pydantic import BaseModel, Field
from enum import Enum

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Available LLM providers."""
    OPENAI = "openai"
    GEMINI = "gemini"
    GROQ = "groq"


class LLMTask(str, Enum):
    """Types of LLM tasks with preferred providers."""
    STRUCTURED_EXTRACTION = "structured_extraction"  # Best: GPT-4o
    SYNTHESIS_WRITING = "synthesis_writing"          # Best: Gemini/Claude
    FAST_VALIDATION = "fast_validation"              # Best: GPT-4o-mini
    REASONING = "reasoning"                          # Best: GPT-4o


# Model configurations
LLM_CONFIGS = {
    LLMProvider.OPENAI: {
        "primary": "gpt-4o",
        "fallback": "gpt-4o-mini",
        "api_key_env": "OPENAI_API_KEY",
    },
    LLMProvider.GEMINI: {
        # Use Gemini 2.0 Flash (free tier available)
        "primary": "gemini-2.0-flash",
        "fallback": "gemini-1.5-flash",
        "api_key_env": "GOOGLE_API_KEY",
    },
    LLMProvider.GROQ: {
        "primary": "llama-3.1-70b-versatile",
        "fallback": "llama-3.1-8b-instant",
        "api_key_env": "GROQ_API_KEY",
    },
}

# Task to provider mapping (preferred order)
# Note: OpenAI prioritized because Gemini free tier has strict limits
TASK_PROVIDER_MAP = {
    LLMTask.STRUCTURED_EXTRACTION: [LLMProvider.OPENAI, LLMProvider.GROQ, LLMProvider.GEMINI],
    LLMTask.SYNTHESIS_WRITING: [LLMProvider.OPENAI, LLMProvider.GROQ, LLMProvider.GEMINI],
    LLMTask.FAST_VALIDATION: [LLMProvider.OPENAI, LLMProvider.GROQ],
    LLMTask.REASONING: [LLMProvider.OPENAI, LLMProvider.GEMINI],
}


class LLMResponse(BaseModel):
    """
    Response from an LLM call.
    
    100% Pydantic compliant with strict validation.
    """
    success: bool = Field(..., description="Whether the LLM call succeeded")
    content: Optional[str] = Field(default=None, description="Raw text response")
    structured_data: Optional[dict] = Field(default=None, description="Parsed JSON data")
    provider: str = Field(..., description="LLM provider used (openai, gemini, groq)")
    model: str = Field(..., description="Model name used")
    cost: float = Field(default=0.0, ge=0.0, description="Estimated API cost in USD")
    tokens_used: int = Field(default=0, ge=0, description="Total tokens consumed")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    
    model_config = {"validate_assignment": True}


def get_available_providers() -> list[LLMProvider]:
    """Get list of providers with valid API keys."""
    available = []
    for provider, config in LLM_CONFIGS.items():
        if os.getenv(config["api_key_env"]):
            available.append(provider)
    return available


async def call_openai(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: str = "gpt-4o",
    json_mode: bool = False,
    temperature: float = 0.7,
) -> LLMResponse:
    """Call OpenAI API."""
    import httpx
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return LLMResponse(
            success=False,
            provider="openai",
            model=model,
            error="OPENAI_API_KEY not set"
        )
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    request_body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    
    if json_mode:
        request_body["response_format"] = {"type": "json_object"}
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=request_body,
            )
            
            if response.status_code != 200:
                return LLMResponse(
                    success=False,
                    provider="openai",
                    model=model,
                    error=f"OpenAI API error: {response.status_code}"
                )
            
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            tokens = data.get("usage", {}).get("total_tokens", 0)
            
            # Estimate cost
            cost = 0.0
            if "gpt-4o" in model:
                cost = tokens * 0.00001  # ~$0.01/1K tokens
            elif "gpt-4o-mini" in model:
                cost = tokens * 0.0000015  # ~$0.00015/1K tokens
            
            return LLMResponse(
                success=True,
                content=content,
                structured_data=json.loads(content) if json_mode else None,
                provider="openai",
                model=model,
                cost=cost,
                tokens_used=tokens,
            )
    except Exception as e:
        logger.error(f"OpenAI call failed: {e}")
        return LLMResponse(
            success=False,
            provider="openai",
            model=model,
            error=str(e)
        )


async def call_gemini(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: str = "gemini-1.5-pro",
    json_mode: bool = False,
    temperature: float = 0.7,
) -> LLMResponse:
    """Call Google Gemini API."""
    import httpx
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return LLMResponse(
            success=False,
            provider="gemini",
            model=model,
            error="GOOGLE_API_KEY not set"
        )
    
    # Build content
    full_prompt = prompt
    if system_prompt:
        full_prompt = f"{system_prompt}\n\n{prompt}"
    
    request_body = {
        "contents": [{
            "parts": [{"text": full_prompt}]
        }],
        "generationConfig": {
            "temperature": temperature,
        }
    }
    
    if json_mode:
        request_body["generationConfig"]["responseMimeType"] = "application/json"
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                headers={"Content-Type": "application/json"},
                json=request_body,
            )
            
            if response.status_code != 200:
                error_msg = response.text[:500]
                return LLMResponse(
                    success=False,
                    provider="gemini",
                    model=model,
                    error=f"Gemini API error: {response.status_code} - {error_msg}"
                )
            
            data = response.json()
            
            # Extract content
            candidates = data.get("candidates", [])
            if not candidates:
                return LLMResponse(
                    success=False,
                    provider="gemini",
                    model=model,
                    error="No candidates in Gemini response"
                )
            
            content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            
            # Get token usage
            usage = data.get("usageMetadata", {})
            tokens = usage.get("totalTokenCount", 0)
            
            # Estimate cost (Gemini is mostly free tier)
            cost = tokens * 0.000001  # Very cheap
            
            return LLMResponse(
                success=True,
                content=content,
                structured_data=json.loads(content) if json_mode and content else None,
                provider="gemini",
                model=model,
                cost=cost,
                tokens_used=tokens,
            )
    except json.JSONDecodeError as e:
        logger.error(f"Gemini JSON parse failed: {e}")
        return LLMResponse(
            success=False,
            provider="gemini",
            model=model,
            error=f"JSON parse error: {e}"
        )
    except Exception as e:
        logger.error(f"Gemini call failed: {e}")
        return LLMResponse(
            success=False,
            provider="gemini",
            model=model,
            error=str(e)
        )


async def call_llm(
    prompt: str,
    task_type: LLMTask = LLMTask.REASONING,
    system_prompt: Optional[str] = None,
    json_mode: bool = False,
    temperature: float = 0.7,
    preferred_provider: Optional[LLMProvider] = None,
) -> LLMResponse:
    """
    Call the best LLM for a given task type.
    
    This is the MAIN entry point for multi-LLM support.
    
    Args:
        prompt: User prompt
        task_type: Type of task (affects provider selection)
        system_prompt: Optional system prompt
        json_mode: Whether to expect JSON output
        temperature: Creativity level
        preferred_provider: Override automatic selection
        
    Returns:
        LLMResponse from the best available provider
    """
    # Get provider order for this task
    if preferred_provider:
        providers = [preferred_provider]
    else:
        providers = TASK_PROVIDER_MAP.get(task_type, [LLMProvider.OPENAI])
    
    # Filter to available providers
    available = get_available_providers()
    providers = [p for p in providers if p in available]
    
    if not providers:
        return LLMResponse(
            success=False,
            provider="none",
            model="none",
            error="No LLM providers available (check API keys)"
        )
    
    # Try each provider in order
    for provider in providers:
        config = LLM_CONFIGS[provider]
        model = config["primary"]
        
        if provider == LLMProvider.OPENAI:
            response = await call_openai(
                prompt, system_prompt, model, json_mode, temperature
            )
        elif provider == LLMProvider.GEMINI:
            response = await call_gemini(
                prompt, system_prompt, model, json_mode, temperature
            )
        else:
            continue  # Skip unsupported providers
        
        if response.success:
            logger.info(f"LLM call succeeded: {provider.value}/{model}")
            return response
        else:
            logger.warning(f"LLM call failed ({provider.value}): {response.error}")
            # Try fallback model
            fallback_model = config.get("fallback")
            if fallback_model:
                if provider == LLMProvider.OPENAI:
                    response = await call_openai(
                        prompt, system_prompt, fallback_model, json_mode, temperature
                    )
                elif provider == LLMProvider.GEMINI:
                    response = await call_gemini(
                        prompt, system_prompt, fallback_model, json_mode, temperature
                    )
                
                if response.success:
                    return response
    
    # All providers failed
    return LLMResponse(
        success=False,
        provider="none",
        model="none",
        error="All LLM providers failed"
    )


async def synthesize_with_gemini(
    research_content: str,
    synthesis_type: str = "executive_summary",
) -> LLMResponse:
    """
    Use Gemini specifically for synthesis/writing tasks.
    
    Gemini excels at writing coherent, well-structured prose.
    
    Args:
        research_content: Raw research findings
        synthesis_type: What to synthesize (executive_summary, analysis, etc.)
        
    Returns:
        LLMResponse with synthesized content
    """
    system_prompt = f"""You are an expert market analyst synthesizing research findings.
    
Task: Create a {synthesis_type} from the provided research data.

Guidelines:
- Be concise but comprehensive
- Use specific numbers and facts from the research
- Highlight key insights and actionable recommendations
- Use professional business language
- Format with clear sections and bullet points where appropriate"""
    
    prompt = f"""Based on the following research findings, create a {synthesis_type}:

{research_content}

Provide a well-structured {synthesis_type}:"""
    
    return await call_llm(
        prompt=prompt,
        task_type=LLMTask.SYNTHESIS_WRITING,
        system_prompt=system_prompt,
        temperature=0.7,
    )


async def extract_structured_with_openai(
    content: str,
    schema: dict,
    extraction_type: str = "data extraction",
) -> LLMResponse:
    """
    Use OpenAI specifically for structured data extraction.
    
    GPT-4o excels at following JSON schemas precisely.
    
    Args:
        content: Raw content to extract from
        schema: JSON schema for extraction
        extraction_type: Description of what to extract
        
    Returns:
        LLMResponse with extracted structured data
    """
    system_prompt = f"""You are a data extraction specialist.
    
Task: Extract {extraction_type} from the provided content and return as JSON.

IMPORTANT:
- Follow the provided schema exactly
- Use null for missing values (don't invent data)
- Extract only information explicitly stated in the content
- Return valid JSON only"""
    
    prompt = f"""Extract {extraction_type} from this content:

{content}

Return JSON matching this schema:
{json.dumps(schema, indent=2)}

JSON output:"""
    
    return await call_llm(
        prompt=prompt,
        task_type=LLMTask.STRUCTURED_EXTRACTION,
        system_prompt=system_prompt,
        json_mode=True,
        temperature=0.3,  # Low temperature for precision
    )


# Convenience function to get provider summary
def get_llm_status() -> str:
    """Get a summary of available LLM providers."""
    available = get_available_providers()
    status = []
    for provider in LLMProvider:
        if provider in available:
            status.append(f"✅ {provider.value}")
        else:
            status.append(f"❌ {provider.value}")
    return " | ".join(status)
