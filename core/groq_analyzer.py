"""
АртМинд — Groq Vision Анализатор v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Анализ детских рисунков через Groq API (llama-3.2-11b-vision).

Настройка (5 минут):
  1. Зарегистрируйся на console.groq.com
  2. API Keys → Create API Key
  3. Добавь в core/.env:  GROQ_API_KEY=gsk_...
  4. Установи: py -3.11 -m pip install groq python-dotenv

Лимиты бесплатного tier (на март 2026):
  - 30 запросов / минуту
  - 14 400 запросов / день
  - 1 000 000 токенов / день
  Достаточно для разработки, тестирования и демонстрации.

Модель: llama-3.2-11b-vision-preview
  - Понимает изображения (vision)
  - Очень быстрая (~2-4 сек на запрос)
  - Хорошо следует структурированным промптам
"""

import base64
import json
import re
import os
from typing import Optional
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from groq import Groq

# ── Настройки ──────────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

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
# ПРОМПТЫ
# ══════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """Ты — опытный психолог-арт-терапевт, специализирующийся на анализе детских рисунков.
Твоя задача — определить психоэмоциональное состояние ребёнка по его рисунку.
Ты работаешь по методикам Люшера (цвет→эмоции), Маховер (зональный анализ) и арт-терапии Копытина.
Отвечай исключительно на русском языке."""

USER_PROMPT_TEMPLATE = """Проанализируй этот детский рисунок как опытный психолог-арт-терапевт.{age_str}{context_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ШАГ 1 — ВИЗУАЛЬНОЕ ОПИСАНИЕ:
Опиши что конкретно нарисовано: объекты, цвета, линии, расположение на листе (2-3 предложения).

ШАГ 2 — ПСИХОЛОГИЧЕСКАЯ ИНТЕРПРЕТАЦИЯ:
Какие эмоции и состояния отражает рисунок? Что говорят цвета, линии, символы? (2-3 предложения)

ШАГ 3 — JSON РЕЗУЛЬТАТ:
Верни результат строго в следующем JSON формате. Только JSON, без markdown, без пояснений:

{{
  "emotions": [
    {{"name": "радость",     "intensity": 0}},
    {{"name": "грусть",      "intensity": 0}},
    {{"name": "тревога",     "intensity": 0}},
    {{"name": "агрессия",    "intensity": 0}},
    {{"name": "спокойствие", "intensity": 0}}
  ],
  "colorAnalysis": {{
    "dominant":        ["#hex1", "#hex2", "#hex3"],
    "palette":         "тёплая|холодная|смешанная|ахроматическая (серые тона)|многоцветная|природная",
    "brightnessClass": "тёмный|средний|светлый",
    "saturationClass": "серый|приглушён|яркий",
    "brightnessValue": 0,
    "saturationValue": 0,
    "interpretation":  "Психологическое значение цветовой гаммы"
  }},
  "composition": {{
    "fillRatio":      0,
    "fillClass":      "низкая|средняя|высокая",
    "location":       "центр|верх|низ|лево|право",
    "numObjects":     0,
    "complexity":     "низкая|средняя|высокая",
    "interpretation": "Описание композиции и расположения элементов"
  }},
  "zoneAnalysis": {{
    "zoneClasses": {{
      "верх":  "низкая|средняя|высокая",
      "центр": "низкая|средняя|высокая",
      "низ":   "низкая|средняя|высокая",
      "лево":  "низкая|средняя|высокая",
      "право": "низкая|средняя|высокая"
    }},
    "balanceInterpretation": "Описание баланса по зонам листа (методика Маховер)"
  }},
  "lineAnalysis": {{
    "pressure":       "слабый|средний|сильный",
    "thickness":      "тонкие|средние|толстые",
    "character":      "плавные|прерывистые|угловатые",
    "chaos":          "низкая|средняя|высокая",
    "interpretation": "Психологическое значение характера линий"
  }},
  "contentAnalysis": {{
    "detectedObjects": ["список", "объектов"],
    "hasHuman":        false,
    "hasSun":          false,
    "hasHouse":        false,
    "hasNature":       false,
    "hasDarkElements": false,
    "hasSmile":        false,
    "symbolism":       "Описание ключевых символов и их психологического значения"
  }},
  "psychologicalPortrait": "Развёрнутый психологический портрет ребёнка на основе рисунка (3-5 предложений)",
  "riskFactors": [],
  "recommendations": [],
  "overallState": "норма|требует_внимания|требует_консультации"
}}

Правила заполнения:
- intensity: целое число 0–100
- riskFactors: список строк с описанием тревожных признаков (может быть пустым [])
- recommendations: список из 2–4 конкретных рекомендаций для педагога/родителя
- Учитывай ВСЁ: цвет, линии, объекты, символику, расположение, нажим"""


def _build_prompt(age: Optional[int], context: str) -> str:
    age_str     = f"\nВозраст ребёнка: {age} лет." if age else ""
    context_str = f"\nКонтекст от специалиста: {context}" if context else ""
    return USER_PROMPT_TEMPLATE.format(age_str=age_str, context_str=context_str)


# ══════════════════════════════════════════════════════════════════════════
# ИЗВЛЕЧЕНИЕ И ВАЛИДАЦИЯ JSON
# ══════════════════════════════════════════════════════════════════════════

def _extract_json(raw: str) -> dict:
    """Извлекает JSON из ответа с CoT-рассуждениями. 5 попыток."""
    raw = raw.strip()

    # Попытка 1: весь ответ — чистый JSON
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Попытка 2: JSON внутри ```json ... ```
    md = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if md:
        try:
            return json.loads(md.group(1))
        except json.JSONDecodeError:
            pass

    # Попытка 3: блок после «ШАГ 3»
    step3 = re.search(r"(?:ШАГ\s*3|JSON)[^\{]*(\{.*\})", raw, re.DOTALL | re.IGNORECASE)
    if step3:
        try:
            return json.loads(step3.group(1))
        except json.JSONDecodeError:
            pass

    # Попытка 4: последний валидный JSON-блок с нужными полями
    for block in reversed(list(re.finditer(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", raw, re.DOTALL))):
        try:
            parsed = json.loads(block.group(0))
            if "emotions" in parsed or "overallState" in parsed:
                return parsed
        except json.JSONDecodeError:
            continue

    # Попытка 5: любой { ... }
    brace = re.search(r"\{.*\}", raw, re.DOTALL)
    if brace:
        try:
            return json.loads(brace.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Не удалось извлечь JSON из ответа Groq. Начало: {raw[:300]}")


def _validate_and_fix(data: dict, age: Optional[int]) -> dict:
    """Проверяет структуру и заполняет пропущенные поля дефолтами."""
    all_names = ["радость", "грусть", "тревога", "агрессия", "спокойствие"]

    raw_em = {e["name"]: e["intensity"] for e in data.get("emotions", [])
              if isinstance(e, dict) and "name" in e and "intensity" in e}

    emotions_fixed = []
    for name in all_names:
        intensity = max(0, min(100, int(raw_em.get(name, 0))))
        emotions_fixed.append({
            "name":      name,
            "intensity": intensity,
            "evidence":  "Groq: визуальный анализ содержания рисунка",
        })
    emotions_fixed.sort(key=lambda x: -x["intensity"])
    data["emotions"] = [e for e in emotions_fixed if e["intensity"] >= 10][:5]

    # colorAnalysis
    ca = data.get("colorAnalysis", {})
    data["colorAnalysis"] = {
        "dominant":        ca.get("dominant", ["#808080"]),
        "palette":         ca.get("palette", "смешанная"),
        "brightnessClass": ca.get("brightnessClass", "средний"),
        "saturationClass": ca.get("saturationClass", "приглушён"),
        "brightnessValue": float(ca.get("brightnessValue", 50)),
        "saturationValue": float(ca.get("saturationValue", 50)),
        "colorRatios":     ca.get("colorRatios", {}),
        "colorCoverage":   float(ca.get("colorCoverage", 50)),
        "nVividColors":    int(ca.get("nVividColors", 1)),
        "warmRatio":       float(ca.get("warmRatio", 30)),
        "coolRatio":       float(ca.get("coolRatio", 20)),
        "interpretation":  ca.get("interpretation", ""),
    }

    # composition
    comp = data.get("composition", {})
    data["composition"] = {
        "fillRatio":      float(comp.get("fillRatio", 40)),
        "fillClass":      comp.get("fillClass", "средняя"),
        "centerX":        float(comp.get("centerX", 0.5)),
        "centerY":        float(comp.get("centerY", 0.5)),
        "location":       comp.get("location", "центр"),
        "numObjects":     int(comp.get("numObjects", 5)),
        "complexity":     comp.get("complexity", "средняя"),
        "lineDensity":    float(comp.get("lineDensity", 5.0)),
        "style":          f"{comp.get('fillClass','средняя')} заполненность",
        "spaceUsage":     comp.get("fillClass", "средняя"),
        "interpretation": comp.get("interpretation", ""),
    }

    # zoneAnalysis
    za = data.get("zoneAnalysis", {})
    zc = za.get("zoneClasses", {})
    data["zoneAnalysis"] = {
        "zoneDensities":         {z: 15 for z in ["верх", "центр", "низ", "лево", "право"]},
        "zoneClasses":           {z: zc.get(z, "средняя") for z in ["верх", "центр", "низ", "лево", "право"]},
        "zoneInterpretations":   za.get("zoneInterpretations", {}),
        "verticalBalance":       float(za.get("verticalBalance", 0)),
        "horizontalBalance":     float(za.get("horizontalBalance", 0)),
        "balanceInterpretation": za.get("balanceInterpretation", ""),
    }

    # lineAnalysis
    la = data.get("lineAnalysis", {})
    data["lineAnalysis"] = {
        "pressure":       la.get("pressure", "средний"),
        "pressureValue":  0.5,
        "thickness":      la.get("thickness", "средние"),
        "thicknessRatio": 2.5,
        "character":      la.get("character", "плавные"),
        "fragmentRatio":  0.5,
        "chaos":          la.get("chaos", "низкая"),
        "chaosValue":     1.0,
        "interpretation": la.get("interpretation", ""),
    }

    # contentAnalysis
    data.setdefault("contentAnalysis", {
        "detectedObjects": [],
        "hasHuman": False, "hasSun": False,
        "hasHouse": False, "hasNature": False,
        "hasDarkElements": False, "hasSmile": False,
        "symbolism": "",
    })

    # overallState
    valid_states = {"норма", "требует_внимания", "требует_консультации"}
    if data.get("overallState") not in valid_states:
        n_risks = len(data.get("riskFactors", []))
        data["overallState"] = (
            "требует_консультации" if n_risks >= 3 else
            "требует_внимания"     if n_risks >= 1 else
            "норма"
        )

    data["confidence"]    = 88  # Groq/LLaMA — чуть ниже Gemini, но выше OpenCV
    data["moduleWeights"] = {"groq_vision": 1.0}
    data["analysisMode"]  = "groq"
    return data


# ══════════════════════════════════════════════════════════════════════════
# ГИБРИДНАЯ АГРЕГАЦИЯ: Groq + OpenCV
# ══════════════════════════════════════════════════════════════════════════

def _hybrid_merge(groq_result: dict, opencv_result: dict) -> dict:
    """Groq (65%) + OpenCV (35%) — семантика + точные метрики."""
    merged = dict(groq_result)

    # Эмоции: взвешенное смешение
    groq_em   = {e["name"]: e["intensity"] for e in groq_result.get("emotions", [])}
    opencv_em = {e["name"]: e["intensity"] for e in opencv_result.get("emotions", [])}

    all_names = ["радость", "грусть", "тревога", "агрессия", "спокойствие"]
    merged_emotions = []
    for name in all_names:
        blended = round(groq_em.get(name, 0) * 0.65 + opencv_em.get(name, 0) * 0.35)
        blended = max(0, min(100, blended))
        if blended >= 10:
            merged_emotions.append({
                "name":      name,
                "intensity": blended,
                "evidence":  f"Groq {groq_em.get(name,0)}% + OpenCV {opencv_em.get(name,0)}% → гибрид",
            })
    merged_emotions.sort(key=lambda x: -x["intensity"])
    merged["emotions"] = merged_emotions[:5]

    # Числовые метрики цвета — из OpenCV (точнее)
    opencv_ca = opencv_result.get("colorAnalysis", {})
    groq_ca   = groq_result.get("colorAnalysis", {})
    merged["colorAnalysis"] = {
        **groq_ca,
        "brightnessValue": opencv_ca.get("brightnessValue", groq_ca.get("brightnessValue", 50)),
        "saturationValue": opencv_ca.get("saturationValue", groq_ca.get("saturationValue", 50)),
        "colorRatios":     opencv_ca.get("colorRatios",     groq_ca.get("colorRatios", {})),
        "colorCoverage":   opencv_ca.get("colorCoverage",   groq_ca.get("colorCoverage", 50)),
        "nVividColors":    opencv_ca.get("nVividColors",    groq_ca.get("nVividColors", 1)),
        "warmRatio":       opencv_ca.get("warmRatio",       groq_ca.get("warmRatio", 30)),
        "dominant":        opencv_ca.get("dominant",        groq_ca.get("dominant", [])),
        "interpretation":  groq_ca.get("interpretation",    ""),
    }

    # Линии и зоны — из OpenCV (точные метрики)
    merged["lineAnalysis"] = opencv_result.get("lineAnalysis", groq_result.get("lineAnalysis", {}))
    merged["zoneAnalysis"] = opencv_result.get("zoneAnalysis", groq_result.get("zoneAnalysis", {}))

    # Числовые поля композиции — из OpenCV
    opencv_comp = opencv_result.get("composition", {})
    groq_comp   = groq_result.get("composition", {})
    merged["composition"] = {
        **groq_comp,
        "fillRatio":   opencv_comp.get("fillRatio",   groq_comp.get("fillRatio", 40)),
        "numObjects":  opencv_comp.get("numObjects",  groq_comp.get("numObjects", 5)),
        "lineDensity": opencv_comp.get("lineDensity", groq_comp.get("lineDensity", 5)),
    }

    # contentAnalysis — объединяем через OR
    groq_content   = groq_result.get("contentAnalysis", {})
    opencv_content = opencv_result.get("contentAnalysis", {})
    merged_content = dict(groq_content)
    for flag in ["hasHuman", "hasSun", "hasHouse", "hasNature", "hasDarkElements", "hasSmile"]:
        merged_content[flag] = groq_content.get(flag, False) or opencv_content.get(flag, False)
    g_objs = set(groq_content.get("detectedObjects", []))
    o_objs = set(opencv_content.get("detectedObjects", []))
    merged_content["detectedObjects"] = list(g_objs | o_objs)
    merged["contentAnalysis"] = merged_content

    # Meta
    merged["confidence"]    = min(96, round(
        groq_result.get("confidence", 88) * 0.6 +
        opencv_result.get("confidence", 70) * 0.4
    ))
    merged["moduleWeights"] = {"groq_vision": 0.65, "opencv_metrics": 0.35}
    merged["analysisMode"]  = "hybrid"
    merged["ageNormLabel"]  = opencv_result.get("ageNormLabel", "")
    merged["contextAnalysis"] = opencv_result.get("contextAnalysis", {})
    return merged


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
    prompt = _build_prompt(child_age, context)

    # Кодируем изображение в base64
    image_b64  = base64.b64encode(image_bytes).decode("utf-8")
    # Определяем тип изображения
    media_type = "image/jpeg"
    if image_bytes[:4] == b"\x89PNG":
        media_type = "image/png"

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
    parsed   = _extract_json(raw_text)
    result   = _validate_and_fix(parsed, child_age)
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