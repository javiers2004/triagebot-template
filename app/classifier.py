import json
import logging
import os

import httpx

FALLBACK_CLASSIFICATION: dict = {"category": "question", "priority": "P3", "tags": []}

_ALLOWED_CATEGORIES = {"bug", "feature_request", "question", "urgent"}
_ALLOWED_PRIORITIES = {"P1", "P2", "P3"}

_SYSTEM_PROMPT = (
    "Devuelve EXCLUSIVAMENTE un objeto JSON válido. "
    "Sin markdown, sin saludos, sin texto antes ni después. "
    "Los valores permitidos son: category ∈ {bug, feature_request, question, urgent}, "
    "priority ∈ {P1, P2, P3}. "
    "No inventes categorías. Máximo 5 tags. "
    'Formato exacto: {"category": "...", "priority": "...", "tags": ["..."]}'
)

_USER_PROMPT = "Title: {title}\nDescription: {description}"

_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
_MODEL = "openai/gpt-oss-120b"

_log = logging.getLogger(__name__)


def classify_ticket(title: str, description: str) -> dict:
    try:
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not api_key:
            _log.warning("OPENROUTER_API_KEY no está definida; usando clasificación de fallback")
            return FALLBACK_CLASSIFICATION
        response = httpx.post(
            _OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": _MODEL,
                "max_tokens": 256,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": _USER_PROMPT.format(title=title, description=description)},
                ],
            },
            timeout=15.0,
        )
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"]
        result = json.loads(raw)

        category = result.get("category")
        priority = result.get("priority")
        tags = result.get("tags", [])

        if category not in _ALLOWED_CATEGORIES or priority not in _ALLOWED_PRIORITIES:
            return FALLBACK_CLASSIFICATION

        if not isinstance(tags, list):
            tags = []

        return {"category": category, "priority": priority, "tags": [str(t) for t in tags[:5]]}
    except Exception:
        return FALLBACK_CLASSIFICATION
