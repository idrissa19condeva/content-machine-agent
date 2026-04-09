import json
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog
from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def llm_completion(
    prompt: str,
    system: str = "",
    response_format: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
) -> dict:
    """
    Appel unifié vers OpenAI ou Anthropic.
    Retourne un dict parsé si response_format='json', sinon {"text": "..."}.
    """
    provider = settings.llm_provider
    model = settings.llm_model

    if provider == "openai":
        return await _openai_call(prompt, system, response_format, temperature, max_tokens, model)
    elif provider == "anthropic":
        return await _anthropic_call(prompt, system, response_format, temperature, max_tokens, model)
    else:
        raise ValueError(f"LLM provider inconnu : {provider}")


async def _openai_call(prompt, system, response_format, temperature, max_tokens, model) -> dict:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    kwargs = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
    if response_format == "json":
        kwargs["response_format"] = {"type": "json_object"}

    response = await client.chat.completions.create(**kwargs)
    text = response.choices[0].message.content
    tokens = response.usage.total_tokens if response.usage else 0

    result = _parse_response(text, response_format)
    result["_tokens_used"] = tokens
    result["_cost_usd"] = _estimate_cost(tokens, model)
    return result


async def _anthropic_call(prompt, system, response_format, temperature, max_tokens, model) -> dict:
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system

    response = await client.messages.create(**kwargs)
    text = response.content[0].text
    tokens = (response.usage.input_tokens or 0) + (response.usage.output_tokens or 0)

    result = _parse_response(text, response_format)
    result["_tokens_used"] = tokens
    result["_cost_usd"] = _estimate_cost(tokens, model)
    return result


def _parse_response(text: str, response_format: Optional[str]) -> dict:
    if response_format == "json":
        clean = text.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(clean)
    return {"text": text}


def _estimate_cost(tokens: int, model: str) -> float:
    # Estimations grossières par 1K tokens
    rates = {
        "gpt-4o": 0.005,
        "gpt-4o-mini": 0.00015,
        "claude-sonnet-4-20250514": 0.003,
    }
    rate = rates.get(model, 0.005)
    return round(tokens / 1000 * rate, 6)
