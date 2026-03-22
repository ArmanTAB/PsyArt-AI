"""
АртМинд — Единый модуль промптов v1.1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Все промпты для Vision LLM провайдеров (Groq и др.)
хранятся здесь. Устраняет дублирование и упрощает обновление.

v1.1: hybrid_merge пробрасывает evidenceChains из OpenCV
"""

import json
import re
from typing import Optional


# ══════════════════════════════════════════════════════════
# КОНСТАНТЫ
# ══════════════════════════════════════════════════════════

ALL_EMOTIONS = ["радость", "грусть", "тревога", "агрессия", "спокойствие"]


# ══════════════════════════════════════════════════════════
# СИСТЕМНЫЙ ПРОМПТ
# ══════════════════════════════════════════════════════════

SYSTEM_PROMPT = """Ты — опытный психолог-арт-терапевт, специализирующийся на анализе детских рисунков.
Твоя задача — определить психоэмоциональное состояние ребёнка по его рисунку.
Ты работаешь по методикам Люшера (цвет→эмоции), Маховер (зональный анализ) и арт-терапии Копытина.
Отвечай исключительно на русском языке."""


# ══════════════════════════════════════════════════════════
# ПОЛЬЗОВАТЕЛЬСКИЙ ПРОМПТ (Chain-of-Thought + JSON)
# ══════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════
# ПОСТРОЕНИЕ ПРОМПТА
# ══════════════════════════════════════════════════════════

def build_prompt(age: Optional[int], context: str) -> str:
    """Формирует пользовательский промпт с учётом возраста и контекста."""
    age_str     = f"\nВозраст ребёнка: {age} лет." if age else ""
    context_str = f"\nКонтекст от специалиста: {context}" if context and context.strip() else ""
    return USER_PROMPT_TEMPLATE.format(age_str=age_str, context_str=context_str)


# ══════════════════════════════════════════════════════════
# ИЗВЛЕЧЕНИЕ JSON ИЗ ОТВЕТА LLM
# ══════════════════════════════════════════════════════════

def extract_json(raw: str) -> dict:
    """
    Извлекает JSON из ответа LLM с Chain-of-Thought рассуждениями.
    5 стратегий парсинга с фолбэком.
    """
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

    # Попытка 4: последний валидный JSON-блок с ключевыми полями
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

    raise ValueError(f"Не удалось извлечь JSON из ответа LLM. Начало: {raw[:300]}")


# ══════════════════════════════════════════════════════════
# ВАЛИДАЦИЯ И НОРМАЛИЗАЦИЯ ОТВЕТА LLM
# ══════════════════════════════════════════════════════════

def validate_and_fix(data: dict, age: Optional[int], provider_name: str = "LLM") -> dict:
    """
    Проверяет структуру ответа LLM и заполняет пропущенные поля дефолтами.
    Единая валидация для всех провайдеров.
    """
    # ── Эмоции ──
    raw_em = {e["name"]: e["intensity"] for e in data.get("emotions", [])
              if isinstance(e, dict) and "name" in e and "intensity" in e}

    emotions_fixed = []
    for name in ALL_EMOTIONS:
        intensity = max(0, min(100, int(raw_em.get(name, 0))))
        emotions_fixed.append({
            "name":      name,
            "intensity": intensity,
            "evidence":  f"{provider_name}: визуальный анализ содержания рисунка",
        })
    emotions_fixed.sort(key=lambda x: -x["intensity"])
    data["emotions"] = [e for e in emotions_fixed if e["intensity"] >= 10][:5]

    # ── colorAnalysis ──
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

    # ── composition ──
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
        "style":          f"{comp.get('fillClass', 'средняя')} заполненность",
        "spaceUsage":     comp.get("fillClass", "средняя"),
        "interpretation": comp.get("interpretation", ""),
    }

    # ── zoneAnalysis ──
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

    # ── lineAnalysis ──
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

    # ── contentAnalysis ──
    data.setdefault("contentAnalysis", {
        "detectedObjects": [],
        "hasHuman": False, "hasSun": False,
        "hasHouse": False, "hasNature": False,
        "hasDarkElements": False, "hasSmile": False,
        "symbolism": "",
    })

    # ── overallState ──
    valid_states = {"норма", "требует_внимания", "требует_консультации"}
    if data.get("overallState") not in valid_states:
        n_risks = len(data.get("riskFactors", []))
        data["overallState"] = (
            "требует_консультации" if n_risks >= 3 else
            "требует_внимания"     if n_risks >= 1 else
            "норма"
        )

    return data


# ══════════════════════════════════════════════════════════
# ГИБРИДНАЯ АГРЕГАЦИЯ: LLM + OpenCV
# ══════════════════════════════════════════════════════════

def hybrid_merge(llm_result: dict, opencv_result: dict, llm_name: str = "LLM") -> dict:
    """
    LLM (65%) + OpenCV (35%) — семантика + точные метрики.
    Универсальная функция для любого LLM-провайдера.
    """
    merged = dict(llm_result)

    # ── Эмоции: взвешенное смешение ──
    llm_em    = {e["name"]: e["intensity"] for e in llm_result.get("emotions", [])}
    opencv_em = {e["name"]: e["intensity"] for e in opencv_result.get("emotions", [])}

    merged_emotions = []
    for name in ALL_EMOTIONS:
        blended = round(llm_em.get(name, 0) * 0.65 + opencv_em.get(name, 0) * 0.35)
        blended = max(0, min(100, blended))
        if blended >= 10:
            merged_emotions.append({
                "name":      name,
                "intensity": blended,
                "evidence":  f"{llm_name} {llm_em.get(name, 0)}% + OpenCV {opencv_em.get(name, 0)}% → гибрид",
            })
    merged_emotions.sort(key=lambda x: -x["intensity"])
    merged["emotions"] = merged_emotions[:5]

    # ── Числовые метрики цвета — из OpenCV (точнее) ──
    opencv_ca = opencv_result.get("colorAnalysis", {})
    llm_ca    = llm_result.get("colorAnalysis", {})
    merged["colorAnalysis"] = {
        **llm_ca,
        "brightnessValue": opencv_ca.get("brightnessValue", llm_ca.get("brightnessValue", 50)),
        "saturationValue": opencv_ca.get("saturationValue", llm_ca.get("saturationValue", 50)),
        "colorRatios":     opencv_ca.get("colorRatios",     llm_ca.get("colorRatios", {})),
        "colorCoverage":   opencv_ca.get("colorCoverage",   llm_ca.get("colorCoverage", 50)),
        "nVividColors":    opencv_ca.get("nVividColors",    llm_ca.get("nVividColors", 1)),
        "warmRatio":       opencv_ca.get("warmRatio",       llm_ca.get("warmRatio", 30)),
        "dominant":        opencv_ca.get("dominant",        llm_ca.get("dominant", [])),
        "interpretation":  llm_ca.get("interpretation",     ""),
    }

    # ── Линии и зоны — из OpenCV (точные метрики) ──
    merged["lineAnalysis"] = opencv_result.get("lineAnalysis", llm_result.get("lineAnalysis", {}))
    merged["zoneAnalysis"] = opencv_result.get("zoneAnalysis", llm_result.get("zoneAnalysis", {}))

    # ── Числовые поля композиции — из OpenCV ──
    opencv_comp = opencv_result.get("composition", {})
    llm_comp    = llm_result.get("composition", {})
    merged["composition"] = {
        **llm_comp,
        "fillRatio":   opencv_comp.get("fillRatio",   llm_comp.get("fillRatio", 40)),
        "numObjects":  opencv_comp.get("numObjects",  llm_comp.get("numObjects", 5)),
        "lineDensity": opencv_comp.get("lineDensity", llm_comp.get("lineDensity", 5)),
    }

    # ── contentAnalysis — объединяем через OR ──
    llm_content    = llm_result.get("contentAnalysis", {})
    opencv_content = opencv_result.get("contentAnalysis", {})
    merged_content = dict(llm_content)
    for flag in ["hasHuman", "hasSun", "hasHouse", "hasNature", "hasDarkElements", "hasSmile"]:
        merged_content[flag] = llm_content.get(flag, False) or opencv_content.get(flag, False)
    l_objs = set(llm_content.get("detectedObjects", []))
    o_objs = set(opencv_content.get("detectedObjects", []))
    merged_content["detectedObjects"] = list(l_objs | o_objs)
    merged["contentAnalysis"] = merged_content

    # ── Explainability: evidenceChains из OpenCV ──
    if "evidenceChains" in opencv_result:
        merged["evidenceChains"] = opencv_result["evidenceChains"]

    # ── Meta ──
    merged["confidence"] = min(96, round(
        llm_result.get("confidence", 88) * 0.6 +
        opencv_result.get("confidence", 70) * 0.4
    ))
    merged["moduleWeights"]   = {f"{llm_name.lower()}_vision": 0.65, "opencv_metrics": 0.35}
    merged["analysisMode"]    = "hybrid"
    merged["ageNormLabel"]    = opencv_result.get("ageNormLabel", "")
    merged["contextAnalysis"] = opencv_result.get("contextAnalysis", {})
    return merged