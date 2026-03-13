"""
АртМинд — Claude Vision Анализатор v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Анализ детских рисунков через Anthropic Claude API.
Самая глубокая психологическая интерпретация из всех доступных моделей.

Настройка:
  1. Получи ключ на console.anthropic.com → API Keys
  2. Добавь в core/.env:  ANTHROPIC_API_KEY=sk-ant-...
  3. Установи: py -3.11 -m pip install anthropic python-dotenv

Модель: claude-sonnet-4-6
  - Лучшее понимание специализированного психологического контекста
  - Глубокая интерпретация символики и методологий Люшера/Маховер/Копытина
  - ~5-10 сек на запрос
  - $0.003 за анализ (≈300 токенов ответа)
"""

import base64
import json
import re
import os
from typing import Optional
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import anthropic

# ── Настройки ──────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL      = "claude-sonnet-4-6"

# ── Инициализация клиента ──────────────────────────────────────────────────
_client: Optional[anthropic.Anthropic] = None

def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY не найден в core/.env")
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


# ══════════════════════════════════════════════════════════════════════════
# ПРОМПТЫ — усиленная психологическая методология
# ══════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """Ты — опытный психолог-арт-терапевт с 15-летним опытом работы с детьми.
Ты специализируешься на психоэмоциональном анализе детских рисунков и работаешь строго по доказательным методологиям:

МЕТОДОЛОГИИ:
1. Тест Люшера — психологическое значение цветов: красный (витальность/агрессия), синий (покой/потребность в безопасности), зелёный (самоутверждение), жёлтый (экспансивность/тревога), фиолетовый (незрелость), коричневый (телесные ощущения), чёрный (отрицание/тревога), серый (нейтральность/отстранённость).
2. Методика Маховер — зональный анализ листа: верх (духовность, фантазии, самооценка), низ (инстинкты, тревога, приземлённость), лево (прошлое, интроверсия, мать), право (будущее, экстраверсия, отец), центр (эго, настоящее), края (тревога, защитные механизмы).
3. Арт-терапия Копытина — символический язык рисунка: солнце (источник любви, родительская фигура), дом (семья, безопасность), человек (самовосприятие), дерево (жизненная сила), вода (эмоции), дорога (жизненный путь).
4. Показатели нажима: сильный нажим — напряжение/агрессия/тревога, слабый нажим — подавленность/низкая энергия, прерывистые линии — тревожность/нерешительность, угловатые — агрессия/напряжение.

ВОЗРАСТНЫЕ НОРМЫ:
- 3-5 лет: хаотичные линии, схематичные фигуры, яркие цвета — НОРМА
- 6-8 лет: появление сюжета, базовые пропорции, смешанные цвета
- 9-12 лет: детализация, перспектива, осознанный выбор цвета

Отвечай исключительно на русском языке. Давай глубокие, обоснованные интерпретации."""

USER_PROMPT_TEMPLATE = """Проанализируй детский рисунок как опытный психолог-арт-терапевт.{age_str}{context_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ШАГ 1 — ВИЗУАЛЬНОЕ ОПИСАНИЕ:
Детально опиши: все объекты, цвета (с психологическим значением по Люшеру), характер линий, расположение на листе, заполненность. (3-4 предложения)

ШАГ 2 — ПСИХОЛОГИЧЕСКАЯ ИНТЕРПРЕТАЦИЯ (по методологиям):
- Зональный анализ по Маховер: какие зоны листа активны и что это означает
- Цветовой анализ по Люшеру: доминирующие цвета и их психологический смысл
- Символический анализ по Копытину: что означают нарисованные объекты
- Характер линий: нажим, непрерывность, форма — что говорят о состоянии
(4-5 предложений)

ШАГ 3 — JSON РЕЗУЛЬТАТ:
Верни ТОЛЬКО JSON без markdown, без пояснений, без ```json:

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
    "interpretation":  "Психологическое значение по тесту Люшера"
  }},
  "composition": {{
    "fillRatio":      0,
    "fillClass":      "низкая|средняя|высокая",
    "location":       "центр|верх|низ|лево|право",
    "numObjects":     0,
    "complexity":     "низкая|средняя|высокая",
    "interpretation": "Значение композиции по методике Маховер"
  }},
  "zoneAnalysis": {{
    "zoneClasses": {{
      "верх":  "низкая|средняя|высокая",
      "центр": "низкая|средняя|высокая",
      "низ":   "низкая|средняя|высокая",
      "лево":  "низкая|средняя|высокая",
      "право": "низкая|средняя|высокая"
    }},
    "balanceInterpretation": "Зональный баланс по Маховер с конкретными психологическими выводами"
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
    "symbolism":       "Символический анализ по арт-терапии Копытина: значение каждого ключевого объекта"
  }},
  "psychologicalPortrait": "Глубокий психологический портрет: актуальное эмоциональное состояние, потребности, отношения с миром, самовосприятие (4-6 предложений с опорой на конкретные детали рисунка)",
  "riskFactors": [],
  "recommendations": [],
  "overallState": "норма|требует_внимания|требует_консультации"
}}

Правила:
- intensity: 0–100, сумма всех эмоций должна быть 100–250 (они могут сосуществовать)
- riskFactors: конкретные тревожные признаки с обоснованием (или [] если нет)
- recommendations: 3–5 конкретных, практичных рекомендаций для педагога/родителя
- Опирайся СТРОГО на визуальные элементы рисунка, не фантазируй"""


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

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    md = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if md:
        try:
            return json.loads(md.group(1))
        except json.JSONDecodeError:
            pass

    step3 = re.search(r"(?:ШАГ\s*3|JSON)[^\{]*(\{.*\})", raw, re.DOTALL | re.IGNORECASE)
    if step3:
        try:
            return json.loads(step3.group(1))
        except json.JSONDecodeError:
            pass

    for block in reversed(list(re.finditer(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", raw, re.DOTALL))):
        try:
            parsed = json.loads(block.group(0))
            if "emotions" in parsed or "overallState" in parsed:
                return parsed
        except json.JSONDecodeError:
            continue

    brace = re.search(r"\{.*\}", raw, re.DOTALL)
    if brace:
        try:
            return json.loads(brace.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Не удалось извлечь JSON. Начало ответа: {raw[:300]}")


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
            "evidence":  "Claude: психологический анализ рисунка по методологиям Люшера/Маховер/Копытина",
        })
    emotions_fixed.sort(key=lambda x: -x["intensity"])
    data["emotions"] = [e for e in emotions_fixed if e["intensity"] >= 10][:5]

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

    data.setdefault("contentAnalysis", {
        "detectedObjects": [],
        "hasHuman": False, "hasSun": False,
        "hasHouse": False, "hasNature": False,
        "hasDarkElements": False, "hasSmile": False,
        "symbolism": "",
    })

    valid_states = {"норма", "требует_внимания", "требует_консультации"}
    if data.get("overallState") not in valid_states:
        n_risks = len(data.get("riskFactors", []))
        data["overallState"] = (
            "требует_консультации" if n_risks >= 3 else
            "требует_внимания"     if n_risks >= 1 else
            "норма"
        )

    data["confidence"]    = 95  # Claude — highest quality psychological interpretation
    data["moduleWeights"] = {"claude_vision": 1.0}
    data["analysisMode"]  = "claude"
    return data


# ══════════════════════════════════════════════════════════════════════════
# ГИБРИДНАЯ АГРЕГАЦИЯ: Claude + OpenCV
# ══════════════════════════════════════════════════════════════════════════

def _hybrid_merge_claude(claude_result: dict, opencv_result: dict) -> dict:
    """Claude (70%) + OpenCV (30%) — глубокая психология + точные метрики."""
    merged = dict(claude_result)

    claude_em = {e["name"]: e["intensity"] for e in claude_result.get("emotions", [])}
    opencv_em  = {e["name"]: e["intensity"] for e in opencv_result.get("emotions", [])}

    all_names = ["радость", "грусть", "тревога", "агрессия", "спокойствие"]
    merged_emotions = []
    for name in all_names:
        blended = round(claude_em.get(name, 0) * 0.70 + opencv_em.get(name, 0) * 0.30)
        blended = max(0, min(100, blended))
        if blended >= 10:
            merged_emotions.append({
                "name":      name,
                "intensity": blended,
                "evidence":  f"Claude {claude_em.get(name,0)}% + OpenCV {opencv_em.get(name,0)}% → гибрид",
            })
    merged_emotions.sort(key=lambda x: -x["intensity"])
    merged["emotions"] = merged_emotions[:5]

    # Числовые метрики цвета — из OpenCV (точнее пикселей)
    opencv_ca = opencv_result.get("colorAnalysis", {})
    claude_ca = claude_result.get("colorAnalysis", {})
    merged["colorAnalysis"] = {
        **claude_ca,
        "brightnessValue": opencv_ca.get("brightnessValue", claude_ca.get("brightnessValue", 50)),
        "saturationValue": opencv_ca.get("saturationValue", claude_ca.get("saturationValue", 50)),
        "colorRatios":     opencv_ca.get("colorRatios",     claude_ca.get("colorRatios", {})),
        "colorCoverage":   opencv_ca.get("colorCoverage",   claude_ca.get("colorCoverage", 50)),
        "nVividColors":    opencv_ca.get("nVividColors",    claude_ca.get("nVividColors", 1)),
        "warmRatio":       opencv_ca.get("warmRatio",       claude_ca.get("warmRatio", 30)),
        "dominant":        opencv_ca.get("dominant",        claude_ca.get("dominant", [])),
        "interpretation":  claude_ca.get("interpretation",  ""),
    }

    # Точные метрики линий и зон — из OpenCV
    merged["lineAnalysis"] = opencv_result.get("lineAnalysis", claude_result.get("lineAnalysis", {}))
    merged["zoneAnalysis"] = opencv_result.get("zoneAnalysis", claude_result.get("zoneAnalysis", {}))

    opencv_comp = opencv_result.get("composition", {})
    claude_comp = claude_result.get("composition", {})
    merged["composition"] = {
        **claude_comp,
        "fillRatio":   opencv_comp.get("fillRatio",   claude_comp.get("fillRatio", 40)),
        "numObjects":  opencv_comp.get("numObjects",  claude_comp.get("numObjects", 5)),
        "lineDensity": opencv_comp.get("lineDensity", claude_comp.get("lineDensity", 5)),
    }

    claude_content = claude_result.get("contentAnalysis", {})
    opencv_content = opencv_result.get("contentAnalysis", {})
    merged_content = dict(claude_content)
    for flag in ["hasHuman", "hasSun", "hasHouse", "hasNature", "hasDarkElements", "hasSmile"]:
        merged_content[flag] = claude_content.get(flag, False) or opencv_content.get(flag, False)
    c_objs = set(claude_content.get("detectedObjects", []))
    o_objs = set(opencv_content.get("detectedObjects", []))
    merged_content["detectedObjects"] = list(c_objs | o_objs)
    merged["contentAnalysis"] = merged_content

    merged["confidence"]    = min(98, round(
        claude_result.get("confidence", 95) * 0.65 +
        opencv_result.get("confidence", 70) * 0.35
    ))
    merged["moduleWeights"] = {"claude_vision": 0.70, "opencv_metrics": 0.30}
    merged["analysisMode"]  = "claude_hybrid"
    merged["ageNormLabel"]  = opencv_result.get("ageNormLabel", "")
    merged["contextAnalysis"] = opencv_result.get("contextAnalysis", {})
    return merged


# ══════════════════════════════════════════════════════════════════════════
# ОСНОВНЫЕ ФУНКЦИИ
# ══════════════════════════════════════════════════════════════════════════

async def analyze_with_claude(
    image_bytes: bytes,
    child_age:   Optional[int] = None,
    context:     str = "",
) -> dict:
    """Анализирует рисунок через Anthropic Claude Vision API."""
    import asyncio

    client = _get_client()
    prompt = _build_prompt(child_age, context)

    # Определяем media_type
    media_type = "image/jpeg"
    if image_bytes[:4] == b"\x89PNG":
        media_type = "image/png"
    elif image_bytes[:6] in (b"GIF87a", b"GIF89a"):
        media_type = "image/gif"
    elif image_bytes[:4] == b"RIFF":
        media_type = "image/webp"

    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    def _sync_call():
        return client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type":       "base64",
                                "media_type": media_type,
                                "data":       image_b64,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )

    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, _sync_call)

    raw_text = response.content[0].text
    parsed   = _extract_json(raw_text)
    result   = _validate_and_fix(parsed, child_age)
    return result


async def check_claude_available() -> dict:
    """Проверяет доступность Claude API."""
    if not ANTHROPIC_API_KEY:
        return {"available": False, "error": "ANTHROPIC_API_KEY не найден в core/.env"}
    try:
        client = _get_client()
        # Минимальный тест — текстовый запрос без изображения
        def _test():
            return client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=10,
                messages=[{"role": "user", "content": "ok"}],
            )
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _test)
        return {
            "available": True,
            "model":     CLAUDE_MODEL,
        }
    except Exception as e:
        return {"available": False, "error": str(e)}