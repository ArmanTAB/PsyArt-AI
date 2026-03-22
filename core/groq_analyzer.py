"""
АртМинд — Groq Vision Анализатор v2.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Анализ детских рисунков через Groq API (LLaMA-4 Scout).

Настройка:
  1. Зарегистрируйся на console.groq.com
  2. API Keys → Create API Key
  3. Добавь в core/.env:  GROQ_API_KEY=gsk_...
  4. Установи: py -3.11 -m pip install groq python-dotenv

Лимиты бесплатного tier (на март 2026):
  - 30 запросов / минуту
  - 14 400 запросов / день
  - 1 000 000 токенов / день
"""

import base64
import os
from typing import Optional
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from groq import Groq

from prompts import (
    SYSTEM_PROMPT, build_prompt, extract_json,
    validate_and_fix, hybrid_merge,
)

# ── Настройки ──────────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = "meta-llama/llama-4-scout-17b-16e-instruct"

# ── Инициализация клиента ──────────────────────────────────────────────────
_client: Optional[Groq] = None

def _get_client() -> Groq:
    global _client
    if _client is None:
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY не найден в core/.env")
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


# ══════════════════════════════════════════════════════════════════════════
# ГИБРИДНАЯ АГРЕГАЦИЯ (обёртка для server.py)
# ══════════════════════════════════════════════════════════════════════════

def _hybrid_merge(groq_result: dict, opencv_result: dict) -> dict:
    """Groq (65%) + OpenCV (35%). Обёртка над универсальной функцией."""
    return hybrid_merge(groq_result, opencv_result, llm_name="Groq")


# ══════════════════════════════════════════════════════════════════════════
# ОСНОВНЫЕ ФУНКЦИИ
# ══════════════════════════════════════════════════════════════════════════

async def analyze_with_groq(
    image_bytes: bytes,
    child_age:   Optional[int] = None,
    context:     str = "",
) -> dict:
    """Анализирует рисунок через Groq Vision API."""
    client = _get_client()
    prompt = build_prompt(child_age, context)

    # Кодируем изображение в base64
    image_b64  = base64.b64encode(image_bytes).decode("utf-8")
    media_type = "image/png" if image_bytes[:4] == b"\x89PNG" else "image/jpeg"

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{image_b64}",
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            },
        ],
        temperature=0.2,
        max_tokens=3000,
    )

    raw_text = response.choices[0].message.content
    parsed   = extract_json(raw_text)
    result   = validate_and_fix(parsed, child_age, provider_name="Groq")
    result["confidence"]    = 88
    result["moduleWeights"] = {"groq_vision": 1.0}
    result["analysisMode"]  = "groq"
    return result


async def check_groq_available() -> dict:
    """Проверяет доступность Groq API."""
    if not GROQ_API_KEY:
        return {"available": False, "error": "GROQ_API_KEY не найден в core/.env"}
    try:
        client = _get_client()
        models = client.models.list()
        model_ids  = [m.id for m in models.data]
        has_vision = any("vision" in m for m in model_ids)
        return {
            "available":  True,
            "model":      GROQ_MODEL,
            "has_vision": has_vision,
        }
    except Exception as e:
        return {"available": False, "error": str(e)}