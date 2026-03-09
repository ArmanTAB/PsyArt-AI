"""
АртМинд — LLaVA Анализатор (Ollama)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Отправляет рисунок в локальную LLaVA через Ollama,
получает структурированный психологический анализ.

Требования:
  - Ollama установлена: https://ollama.com
  - Модель загружена: ollama pull llava:7b
  - Сервер запущен: ollama serve  (или работает как служба)
"""

import httpx
import base64
import json
import re
from typing import Optional

# ── Настройки ──────────────────────────────────────────────
OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llava:7b"
TIMEOUT_SEC  = 120   # GTX 1060 — до 60 сек, берём с запасом

# ── Промпт ─────────────────────────────────────────────────
# Критически важно: точная структура → стабильный JSON
SYSTEM_PROMPT = """Ты — психолог-арт-терапевт, специализирующийся на анализе детских рисунков.
Твоя задача — определить психоэмоциональное состояние ребёнка по его рисунку.
Всегда отвечай ТОЛЬКО валидным JSON без каких-либо пояснений, преамбул или markdown.
Используй исключительно русский язык в текстовых полях."""

USER_PROMPT_TEMPLATE = """Проанализируй этот детский рисунок как опытный психолог-арт-терапевт.{age_str}{context_str}

Верни результат строго в следующем JSON формате (без markdown, без пояснений, только JSON):

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
    "interpretation":  "Текстовое описание цветовой гаммы и её психологического значения"
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
    "balanceInterpretation": "Описание баланса по зонам листа"
  }},
  "lineAnalysis": {{
    "pressure":       "слабый|средний|сильный",
    "thickness":      "тонкие|средние|толстые",
    "character":      "плавные|прерывистые|угловатые",
    "chaos":          "низкая|средняя|высокая",
    "interpretation": "Описание характера линий"
  }},
  "contentAnalysis": {{
    "detectedObjects": ["список", "распознанных", "объектов"],
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
- intensity: целое число 0–100, отражающее выраженность эмоции
- Сумма всех intensity не обязана равняться 100
- Заполни ВСЕ поля, не пропускай ни одного
- riskFactors: список строк с описанием тревожных признаков (может быть пустым [])
- recommendations: список из 2–4 конкретных рекомендаций для педагога/родителя
- Учитывай ВСЁ: цвет, линии, объекты, символику, расположение, нажим"""


def _build_prompt(age: Optional[int], context: str) -> str:
    age_str     = f"\nВозраст ребёнка: {age} лет." if age else ""
    context_str = f"\nДополнительный контекст: {context}" if context and context.strip() else ""
    return USER_PROMPT_TEMPLATE.format(age_str=age_str, context_str=context_str)


def _image_to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


def _extract_json(raw: str) -> dict:
    """Извлекает JSON из ответа LLaVA, которая может добавить лишний текст."""
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

    # Попытка 3: ищем первый { ... } блок
    brace = re.search(r"\{.*\}", raw, re.DOTALL)
    if brace:
        try:
            return json.loads(brace.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Не удалось извлечь JSON из ответа LLaVA. Ответ: {raw[:300]}")


def _validate_and_fix(data: dict, age: Optional[int]) -> dict:
    """Проверяет структуру ответа и заполняет пропущенные поля дефолтами."""

    # emotions — гарантируем все 9 эмоций
    all_names = ["радость", "грусть", "тревога", "агрессия", "спокойствие"]

    raw_em = {e["name"]: e["intensity"] for e in data.get("emotions", [])
              if isinstance(e, dict) and "name" in e and "intensity" in e}

    emotions_fixed = []
    for name in all_names:
        intensity = int(raw_em.get(name, 0))
        intensity = max(0, min(100, intensity))
        # Добавляем evidence для совместимости с фронтендом
        emotions_fixed.append({
            "name":      name,
            "intensity": intensity,
            "evidence":  f"LLaVA анализ рисунка (уверенность модели)",
        })

    # Сортируем по убыванию, топ-5
    emotions_fixed.sort(key=lambda x: -x["intensity"])
    data["emotions"] = [e for e in emotions_fixed if e["intensity"] >= 10][:5]

    # colorAnalysis — дефолты
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

    # composition — дефолты
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

    # zoneAnalysis — дефолты
    za = data.get("zoneAnalysis", {})
    zc = za.get("zoneClasses", {})
    data["zoneAnalysis"] = {
        "zoneDensities":         {z: 15 for z in ["верх","центр","низ","лево","право"]},
        "zoneClasses":           {z: zc.get(z, "средняя") for z in ["верх","центр","низ","лево","право"]},
        "zoneInterpretations":   za.get("zoneInterpretations", {}),
        "verticalBalance":       float(za.get("verticalBalance", 0)),
        "horizontalBalance":     float(za.get("horizontalBalance", 0)),
        "balanceInterpretation": za.get("balanceInterpretation", ""),
    }

    # lineAnalysis — дефолты
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

    # contentAnalysis — новый блок только у LLaVA
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
        # вычисляем автоматически
        n_risks = len(data.get("riskFactors", []))
        data["overallState"] = (
            "требует_консультации" if n_risks >= 3 else
            "требует_внимания"     if n_risks >= 1 else
            "норма"
        )

    # meta
    data["confidence"]    = 88   # LLaVA понимает содержание — уверенность выше
    data["moduleWeights"] = {"llava_vision": 1.0}
    data["analysisMode"]  = "llava"

    return data


async def analyze_with_llava(
    image_bytes: bytes,
    child_age:   Optional[int] = None,
    context:     str = "",
) -> dict:
    """
    Основная функция: отправляет изображение в Ollama LLaVA,
    возвращает структурированный результат.

    Raises:
        httpx.ConnectError  — Ollama не запущена
        httpx.TimeoutException — модель слишком медленно отвечает
        ValueError          — LLaVA вернула невалидный JSON
    """
    img_b64 = _image_to_base64(image_bytes)
    prompt  = _build_prompt(child_age, context)

    payload = {
        "model":  OLLAMA_MODEL,
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "images": [img_b64],
        "stream": False,
        "options": {
            "temperature": 0.1,   # низкая температура = стабильный JSON
            "top_p":       0.9,
            "num_predict": 2048,  # достаточно для полного JSON
        },
    }

    async with httpx.AsyncClient(timeout=TIMEOUT_SEC) as client:
        response = await client.post(OLLAMA_URL, json=payload)
        response.raise_for_status()

    raw_text = response.json().get("response", "")
    parsed   = _extract_json(raw_text)
    result   = _validate_and_fix(parsed, child_age)
    return result


async def check_ollama_available() -> dict:
    """Проверяет доступность Ollama и наличие модели llava:7b."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get("http://localhost:11434/api/tags")
            if r.status_code != 200:
                return {"available": False, "reason": "Ollama не отвечает"}

            models = [m["name"] for m in r.json().get("models", [])]
            has_llava = any("llava" in m for m in models)

            return {
                "available":  True,
                "has_llava":  has_llava,
                "models":     models,
                "reason":     None if has_llava else "Модель llava не найдена. Выполните: ollama pull llava:7b",
            }
    except httpx.ConnectError:
        return {
            "available": False,
            "has_llava": False,
            "models":    [],
            "reason":    "Ollama не запущена. Запустите: ollama serve",
        }
    except Exception as e:
        return {"available": False, "has_llava": False, "models": [], "reason": str(e)}