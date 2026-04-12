from __future__ import annotations

from typing import Any

import requests

from config import settings


class LLMServiceError(Exception):
    """Raised when the upstream LLM API call fails."""


def _normalize_base_url(base_url: str) -> str:
    normalized = (base_url or "").strip().rstrip("/")
    if not normalized:
        normalized = "https://api.openai.com/v1"
    if not normalized.endswith("/v1"):
        normalized = f"{normalized}/v1"
    return normalized


def chat_completion(messages: list[dict[str, str]]) -> str:
    api_key = (settings.LLM_API_KEY or "").strip()
    if not api_key:
        raise LLMServiceError("LLM_API_KEY is not configured")

    url = f"{_normalize_base_url(settings.LLM_API_BASE_URL)}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": settings.LLM_MODEL,
        "messages": messages,
        "temperature": settings.LLM_TEMPERATURE,
        "max_tokens": settings.LLM_MAX_TOKENS,
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise LLMServiceError(f"Failed to connect to LLM API: {exc}") from exc

    if response.status_code >= 400:
        try:
            body = response.json()
        except Exception:
            body = {"raw": response.text[:400]}
        raise LLMServiceError(f"LLM API error {response.status_code}: {body}")

    try:
        data = response.json()
        content = data["choices"][0]["message"]["content"]
    except Exception as exc:
        raise LLMServiceError("Invalid LLM response format") from exc

    if not isinstance(content, str) or not content.strip():
        raise LLMServiceError("Empty LLM response")

    return content.strip()
