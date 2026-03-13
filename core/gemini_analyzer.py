"""
АртМинд — Google Gemini Анализатор v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Заменяет llava_analyzer.py — использует Google Gemini вместо локальной LLaVA.
Не требует Ollama и мощного GPU — работает через облачный API.

Настройка:
  1. Получи ключ на aistudio.google.com
  2. Добавь в core/.env:  GEMINI_API_KEY=AIzaSy...
  3. Установи: py -3.11 -m pip install google-generativeai python-dotenv

Лимиты бесплатного tier:
  - 15 запросов / минуту
  - 1500 запросов / день
  - Достаточно для разработки и демонстрации
"""

import base64
import json
import re
import os
from typing import Optional
from pathlib import Path

# Загружаем .env из папки core/
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import google.generativeai as genai

# ── Настройки ──────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = "gemini-2.0-flash"   # бесплатный, быстрый, отлично видит изображения

# ── Инициализация клиента ──────────────────────────────────
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# ══════════════════════════════════════════════════════════
# ПРОМПТ — Chain-of-thought + JSON
# ══════════════════════════════════════════════════════════

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
    "symbolism":       "Психологическое значение символов"
  }},
  "psychologicalPortrait": "Развёрнутый психологический портрет ребёнка (3-5 предложений)",
  "riskFactors": [],
  "recommendations": [],
  "overallState": "норма|требует_внимания|требует_консультации"
}}

Правила:
- intensity: целое число 0–100
- riskFactors: конкретные тревожные признаки (может быть [])
- recommendations: 2–4 практические рекомендации для педагога или родителя
- Учитывай всё что описал в шагах 1 и 2"""


def _build_prompt(age: Optional[int], context: str) -> str:
    age_str     = f"\nВозраст ребёнка: {age} лет." if age else ""
    context_str = f"\nКонтекст педагога: {context}" if context and context.strip() else ""
    return USER_PROMPT_TEMPLATE.format(age_str=age_str, context_str=context_str)


def _extract_json(raw: str) -> dict:
    """Извлекает JSON из ответа с CoT-рассуждениями."""
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

    # Попытка 3: блок после "ШАГ 3"
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

    raise ValueError(f"Не удалось извлечь JSON из ответа Gemini. Начало: {raw[:300]}")


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
            "evidence":  "Gemini: визуальный анализ содержания рисунка",
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

    data["confidence"]    = 90  # Gemini видит содержание очень хорошо
    data["moduleWeights"] = {"gemini_vision": 1.0}
    data["analysisMode"]  = "gemini"
    return data


# ══════════════════════════════════════════════════════════
# ГИБРИДНАЯ АГРЕГАЦИЯ: Gemini + OpenCV
# ══════════════════════════════════════════════════════════

def _hybrid_merge(gemini_result: dict, opencv_result: dict) -> dict:
    """Gemini (65%) + OpenCV (35%) — семантика + точные метрики."""
    merged = dict(gemini_result)

    # Эмоции: взвешенное смешение
    gemini_em = {e["name"]: e["intensity"] for e in gemini_result.get("emotions", [])}
    opencv_em  = {e["name"]: e["intensity"] for e in opencv_result.get("emotions", [])}

    all_names = ["радость", "грусть", "тревога", "агрессия", "спокойствие"]
    merged_emotions = []
    for name in all_names:
        blended = round(gemini_em.get(name, 0) * 0.65 + opencv_em.get(name, 0) * 0.35)
        blended = max(0, min(100, blended))
        if blended >= 10:
            merged_emotions.append({
                "name":      name,
                "intensity": blended,
                "evidence":  f"Gemini {gemini_em.get(name,0)}% + OpenCV {opencv_em.get(name,0)}% → гибрид",
            })
    merged_emotions.sort(key=lambda x: -x["intensity"])
    merged["emotions"] = merged_emotions[:5]

    # Числовые метрики цвета — из OpenCV (точнее)
    opencv_ca = opencv_result.get("colorAnalysis", {})
    gemini_ca = gemini_result.get("colorAnalysis", {})
    merged["colorAnalysis"] = {
        **gemini_ca,
        "brightnessValue": opencv_ca.get("brightnessValue", gemini_ca.get("brightnessValue", 50)),
        "saturationValue": opencv_ca.get("saturationValue", gemini_ca.get("saturationValue", 50)),
        "colorRatios":     opencv_ca.get("colorRatios",     gemini_ca.get("colorRatios", {})),
        "colorCoverage":   opencv_ca.get("colorCoverage",   gemini_ca.get("colorCoverage", 50)),
        "nVividColors":    opencv_ca.get("nVividColors",    gemini_ca.get("nVividColors", 1)),
        "warmRatio":       opencv_ca.get("warmRatio",       gemini_ca.get("warmRatio", 30)),
        "dominant":        opencv_ca.get("dominant",        gemini_ca.get("dominant", [])),
        "interpretation":  gemini_ca.get("interpretation",  ""),
    }

    # Линии и зоны — из OpenCV (точнее)
    merged["lineAnalysis"] = opencv_result.get("lineAnalysis", gemini_result.get("lineAnalysis", {}))
    merged["zoneAnalysis"] = opencv_result.get("zoneAnalysis", gemini_result.get("zoneAnalysis", {}))

    # Числовые поля композиции — из OpenCV
    opencv_comp = opencv_result.get("composition", {})
    gemini_comp = gemini_result.get("composition", {})
    merged["composition"] = {
        **gemini_comp,
        "fillRatio":   opencv_comp.get("fillRatio",   gemini_comp.get("fillRatio", 40)),
        "numObjects":  opencv_comp.get("numObjects",  gemini_comp.get("numObjects", 5)),
        "lineDensity": opencv_comp.get("lineDensity", gemini_comp.get("lineDensity", 5)),
    }

    # contentAnalysis — объединяем Gemini и OpenCV через OR
    gemini_content = gemini_result.get("contentAnalysis", {})
    opencv_content = opencv_result.get("contentAnalysis", {})
    merged_content = dict(gemini_content)
    for flag in ["hasHuman", "hasSun", "hasHouse", "hasNature", "hasDarkElements", "hasSmile"]:
        merged_content[flag] = gemini_content.get(flag, False) or opencv_content.get(flag, False)
    g_objs = set(gemini_content.get("detectedObjects", []))
    o_objs = set(opencv_content.get("detectedObjects", []))
    merged_content["detectedObjects"] = list(g_objs | o_objs)
    merged["contentAnalysis"] = merged_content

    # Meta
    merged["confidence"]    = min(96, round(
        gemini_result.get("confidence", 90) * 0.6 +
        opencv_result.get("confidence", 70) * 0.4
    ))
    merged["moduleWeights"] = {"gemini_vision": 0.65, "opencv_metrics": 0.35}
    merged["analysisMode"]  = "hybrid"
    merged["ageNormLabel"]  = opencv_result.get("ageNormLabel", "")
    merged["contextAnalysis"] = opencv_result.get("contextAnalysis", {})
    return merged


# ══════════════════════════════════════════════════════════
# ОСНОВНАЯ ФУНКЦИЯ
# ══════════════════════════════════════════════════════════

async def analyze_with_gemini(
    image_bytes: bytes,
    child_age:   Optional[int] = None,
    context:     str = "",
) -> dict:
    """Анализирует рисунок через Google Gemini Vision."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY не найден в .env файле")

    model  = genai.GenerativeModel(GEMINI_MODEL)
    prompt = _build_prompt(child_age, context)

    # Передаём изображение как bytes напрямую
    import PIL.Image
    import io
    pil_image = PIL.Image.open(io.BytesIO(image_bytes))

    response = model.generate_content(
        [SYSTEM_PROMPT + "\n\n" + prompt, pil_image],
        generation_config=genai.types.GenerationConfig(
            temperature=0.2,
            max_output_tokens=3000,
        ),
    )

    raw_text = response.text
    parsed   = _extract_json(raw_text)
    result   = _validate_and_fix(parsed, child_age)
    return result


async def check_gemini_available() -> dict:
    """Проверяет доступность Gemini API."""
    if not GEMINI_API_KEY:
        return {"available": False, "error": "GEMINI_API_KEY не найден в core/.env"}
    try:
        # Быстрая проверка — список моделей
        models = [m.name for m in genai.list_models()]
        has_flash = any("flash" in m for m in models)
        return {
            "available": True,
            "model":     GEMINI_MODEL,
            "has_flash": has_flash,
        }
    except Exception as e:
        return {"available": False, "error": str(e)}