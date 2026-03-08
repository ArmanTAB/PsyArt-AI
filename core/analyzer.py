"""
АртМинд — Модуль психоэмоционального анализа детских рисунков
Методологическая база: тест Люшера, арт-терапия, теория цвета
Стек: OpenCV + Pillow + scikit-learn (rule-based expert system)
"""

import cv2
import numpy as np
from PIL import Image
from sklearn.cluster import KMeans
import io
from typing import List, Dict

# ─────────────────────────────────────────────
# ТАБЛИЦЫ ПСИХОЛОГИИ ЦВЕТА (по Люшеру / арт-терапии)
# ─────────────────────────────────────────────

COLOR_RANGES = {
    "красный":       [(0, 10), (170, 180)],
    "оранжевый":     [(10, 20)],
    "жёлтый":        [(20, 35)],
    "жёлто-зелёный": [(35, 50)],
    "зелёный":       [(50, 80)],
    "голубой":       [(80, 100)],
    "синий":         [(100, 130)],
    "фиолетовый":    [(130, 155)],
    "розовый":       [(155, 170)],
}

COLOR_EMOTION_MAP = {
    "красный":       {"агрессия": 0.7, "радость": 0.3, "энергия": 0.5},
    "оранжевый":     {"радость": 0.7, "энергия": 0.5},
    "жёлтый":        {"радость": 0.9, "энергия": 0.4},
    "жёлто-зелёный": {"тревога": 0.5, "страх": 0.2},
    "зелёный":       {"спокойствие": 0.8, "радость": 0.3},
    "голубой":       {"спокойствие": 0.6, "грусть": 0.2},
    "синий":         {"грусть": 0.5, "спокойствие": 0.5, "тревога": 0.2},
    "фиолетовый":    {"тревога": 0.7, "страх": 0.5, "одиночество": 0.4},
    "розовый":       {"любовь": 0.9, "радость": 0.4},
}

BRIGHTNESS_MODIFIERS = {
    "тёмный":  {"страх": +25, "грусть": +20, "тревога": +15, "радость": -20},
    "средний": {},
    "светлый": {"радость": +15, "спокойствие": +10, "страх": -15},
}

SATURATION_MODIFIERS = {
    "серый":     {"грусть": +20, "одиночество": +25, "спокойствие": -10},
    "приглушён": {"грусть": +10, "спокойствие": +5},
    "яркий":     {"радость": +20, "агрессия": +10, "энергия": +15},
}

COMPOSITION_MAP = {
    "заполненность": {
        "высокая": "Активное использование пространства — высокая энергетика, экстраверсия",
        "средняя": "Умеренное использование пространства — сбалансированное состояние",
        "низкая":  "Малое заполнение листа — возможна замкнутость, низкая энергетика",
    },
    "расположение": {
        "верх":   "Рисунок в верхней части — оптимизм, устремлённость к мечте",
        "низ":    "Рисунок в нижней части — тревожность, заземлённость",
        "лево":   "Смещение влево — ориентация на прошлое, интроверсия",
        "право":  "Смещение вправо — устремлённость в будущее, экстраверсия",
        "центр":  "Центральное расположение — потребность во внимании, эгоцентричность",
    },
    "сложность": {
        "высокая": "Богатая детализация — высокий интеллект, развитое воображение",
        "средняя": "Умеренная детализация — нормативное развитие",
        "низкая":  "Минимальная детализация — возможна тревога или усталость",
    },
}

ALL_EMOTIONS = [
    "радость", "грусть", "тревога", "страх",
    "агрессия", "спокойствие", "одиночество", "любовь", "энергия",
]


# ─────────────────────────────────────────────
# КЛАСС АНАЛИЗАТОРА
# ─────────────────────────────────────────────

class DrawingAnalyzer:

    def analyze(self, image_bytes: bytes, child_age: int = None, context: str = "") -> dict:
        img_bgr  = self._load_image(image_bytes)
        img_hsv  = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

        color_data   = self._analyze_colors(img_bgr, img_hsv)
        comp_data    = self._analyze_composition(img_gray, img_bgr)
        emotions     = self._compute_emotions(color_data, comp_data, child_age)
        portrait     = self._build_portrait(emotions, color_data, comp_data, child_age)
        recs         = self._generate_recommendations(emotions, comp_data, child_age)
        risks        = self._detect_risk_factors(emotions, color_data, comp_data)
        state        = self._assess_overall_state(emotions, risks)
        confidence   = self._estimate_confidence(color_data, comp_data)

        return {
            "colorAnalysis":        color_data,
            "composition":          comp_data,
            "emotions":             emotions,
            "psychologicalPortrait": portrait,
            "riskFactors":          risks,
            "recommendations":      recs,
            "overallState":         state,
            "confidence":           confidence,
        }

    # ── Загрузка ─────────────────────────────
    def _load_image(self, image_bytes: bytes) -> np.ndarray:
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        pil_img = pil_img.resize((512, 512), Image.LANCZOS)
        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    # ── Цветовой анализ ───────────────────────
    def _analyze_colors(self, img_bgr: np.ndarray, img_hsv: np.ndarray) -> dict:
        h, s, v = img_hsv[:, :, 0], img_hsv[:, :, 1], img_hsv[:, :, 2]

        brightness_mean = float(v.mean())
        saturation_mean = float(s.mean())

        if brightness_mean < 80:
            brightness_class = "тёмный"
        elif brightness_mean < 180:
            brightness_class = "средний"
        else:
            brightness_class = "светлый"

        if saturation_mean < 40:
            saturation_class = "серый"
        elif saturation_mean < 100:
            saturation_class = "приглушён"
        else:
            saturation_class = "яркий"

        # K-Means для доминирующих цветов
        pixels = img_bgr.reshape(-1, 3).astype(np.float32)
        sample = pixels[np.random.choice(len(pixels), min(3000, len(pixels)), replace=False)]
        kmeans = KMeans(n_clusters=5, n_init=5, max_iter=100, random_state=42)
        kmeans.fit(sample)
        centers_bgr = kmeans.cluster_centers_.astype(int)

        dominant_colors = []
        for bgr in centers_bgr:
            hex_color = "#{:02x}{:02x}{:02x}".format(int(bgr[2]), int(bgr[1]), int(bgr[0]))
            dominant_colors.append(hex_color)

        color_ratios = self._compute_color_ratios(h, s)

        warm = sum(color_ratios.get(c, 0) for c in ["красный", "оранжевый", "жёлтый"])
        cool = sum(color_ratios.get(c, 0) for c in ["синий", "голубой", "фиолетовый"])

        if saturation_mean < 40:
            palette_type = "ахроматическая (серые тона)"
        elif warm > cool + 0.15:
            palette_type = "тёплая"
        elif cool > warm + 0.15:
            palette_type = "холодная"
        else:
            palette_type = "смешанная"

        interp = self._interpret_colors(brightness_class, saturation_class, color_ratios, palette_type)

        return {
            "dominant":        dominant_colors[:3],
            "palette":         palette_type,
            "brightnessClass": brightness_class,
            "saturationClass": saturation_class,
            "brightnessValue": round(brightness_mean / 255 * 100, 1),
            "saturationValue": round(saturation_mean / 255 * 100, 1),
            "colorRatios":     {k: round(v * 100, 1) for k, v in color_ratios.items() if v > 0.01},
            "interpretation":  interp,
        }

    def _compute_color_ratios(self, h: np.ndarray, s: np.ndarray) -> dict:
        mask_colored = s > 30
        total = mask_colored.sum() + 1
        ratios = {}
        for color_name, ranges in COLOR_RANGES.items():
            mask = np.zeros_like(h, dtype=bool)
            for lo, hi in ranges:
                mask |= (h >= lo) & (h <= hi)
            mask &= mask_colored
            ratios[color_name] = float(mask.sum()) / total
        return ratios

    def _interpret_colors(self, brightness: str, saturation: str, ratios: dict, palette: str) -> str:
        parts = []
        if brightness == "тёмный":
            parts.append("Преобладание тёмных тонов указывает на подавленное настроение или внутреннее напряжение.")
        elif brightness == "светлый":
            parts.append("Светлая палитра свидетельствует об открытости и позитивном эмоциональном фоне.")

        if saturation == "серый":
            parts.append("Ахроматическая гамма может говорить об эмоциональной закрытости или усталости.")
        elif saturation == "яркий":
            parts.append("Насыщенные цвета отражают высокую эмоциональную активность.")

        top = sorted(ratios.items(), key=lambda x: -x[1])[:2]
        for name, ratio in top:
            if ratio > 0.05:
                parts.append(f"Значительная доля {name} цвета ({ratio:.0f}%) несёт соответствующую символику.")

        return " ".join(parts) if parts else f"Палитра {palette}, без явных аномалий."

    # ── Анализ композиции ─────────────────────
    def _analyze_composition(self, gray: np.ndarray, bgr: np.ndarray) -> dict:
        _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)

        fill_ratio = float(np.count_nonzero(binary)) / binary.size

        M = cv2.moments(binary)
        if M["m00"] > 0:
            cx = M["m10"] / M["m00"] / gray.shape[1]
            cy = M["m01"] / M["m00"] / gray.shape[0]
        else:
            cx, cy = 0.5, 0.5

        if cy < 0.4:
            vertical = "верх"
        elif cy > 0.6:
            vertical = "низ"
        else:
            vertical = "центр_вертикаль"

        if cx < 0.4:
            horizontal = "лево"
        elif cx > 0.6:
            horizontal = "право"
        else:
            horizontal = "центр"

        if vertical == "центр_вертикаль" and horizontal == "центр":
            location_key = "центр"
        elif vertical == "верх":
            location_key = "верх"
        elif vertical == "низ":
            location_key = "низ"
        else:
            location_key = horizontal

        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        num_objects = len([c for c in contours if cv2.contourArea(c) > 50])

        if num_objects > 15:
            complexity = "высокая"
        elif num_objects > 5:
            complexity = "средняя"
        else:
            complexity = "низкая"

        edges = cv2.Canny(gray, 50, 150)
        line_density = float(np.count_nonzero(edges)) / edges.size

        if fill_ratio > 0.35:
            fill_class = "высокая"
        elif fill_ratio > 0.12:
            fill_class = "средняя"
        else:
            fill_class = "низкая"

        interp_fill       = COMPOSITION_MAP["заполненность"][fill_class]
        interp_loc        = COMPOSITION_MAP["расположение"].get(location_key, "Центральное расположение.")
        interp_complexity = COMPOSITION_MAP["сложность"][complexity]

        return {
            "fillRatio":   round(fill_ratio * 100, 1),
            "fillClass":   fill_class,
            "centerX":     round(cx, 2),
            "centerY":     round(cy, 2),
            "location":    location_key,
            "numObjects":  num_objects,
            "complexity":  complexity,
            "lineDensity": round(line_density * 100, 2),
            "style":       f"{fill_class} заполненность, {complexity} детализация",
            "spaceUsage":  fill_class,
            "interpretation": f"{interp_fill} {interp_loc} {interp_complexity}",
        }

    # ── Вычисление эмоций ─────────────────────
    def _compute_emotions(self, color_data: dict, comp_data: dict, age: int) -> list:
        scores = {e: 0.0 for e in ALL_EMOTIONS}

        for color_name, ratio in color_data.get("colorRatios", {}).items():
            ratio_frac = ratio / 100.0
            if color_name in COLOR_EMOTION_MAP:
                for emotion, weight in COLOR_EMOTION_MAP[color_name].items():
                    if emotion in scores:
                        scores[emotion] += ratio_frac * weight * 100

        for emotion, delta in BRIGHTNESS_MODIFIERS.get(color_data["brightnessClass"], {}).items():
            if emotion in scores:
                scores[emotion] += delta

        for emotion, delta in SATURATION_MODIFIERS.get(color_data["saturationClass"], {}).items():
            if emotion in scores:
                scores[emotion] += delta

        fill = comp_data["fillClass"]
        if fill == "низкая":
            scores["одиночество"] += 15
            scores["грусть"]      += 10
        elif fill == "высокая":
            scores["энергия"] += 15
            scores["радость"] += 10

        if comp_data["complexity"] == "низкая":
            scores["тревога"] += 10
        elif comp_data["complexity"] == "высокая":
            scores["радость"] += 5

        if comp_data["location"] == "низ":
            scores["тревога"] += 10
            scores["страх"]   += 5
        elif comp_data["location"] == "верх":
            scores["радость"] += 10

        if age:
            if age < 5:
                scores["тревога"] = max(0, scores["тревога"] - 10)
            elif age > 10:
                scores["агрессия"] *= 0.85

        result = []
        for name, score in scores.items():
            clamped = max(0, min(100, round(score)))
            if clamped >= 10:
                result.append({
                    "name":      name,
                    "intensity": clamped,
                    "evidence":  self._emotion_evidence(name, color_data, comp_data),
                })

        result.sort(key=lambda x: -x["intensity"])
        return result[:5]

    def _emotion_evidence(self, emotion: str, color_data: dict, comp_data: dict) -> str:
        evidences = {
            "радость":     f"Тёплая/яркая палитра ({color_data['palette']}), активное заполнение листа",
            "грусть":      f"Холодные тона, низкая яркость ({color_data['brightnessValue']}%)",
            "тревога":     f"Расположение: {comp_data['location']}, насыщенность: {color_data['saturationClass']}",
            "страх":       f"Тёмные тона, слабое заполнение ({comp_data['fillRatio']}%)",
            "агрессия":    f"Красные/оранжевые тона, яркая насыщенность",
            "спокойствие": f"Зелёные/синие тона, сбалансированная композиция",
            "одиночество": f"Малое заполнение листа ({comp_data['fillRatio']}%), приглушённые тона",
            "любовь":      f"Розовые/тёплые тона, активная детализация",
            "энергия":     f"Яркие цвета, высокое заполнение листа ({comp_data['fillRatio']}%)",
        }
        return evidences.get(emotion, "Комплексный анализ цвета и композиции")

    # ── Психологический портрет ───────────────
    def _build_portrait(self, emotions: list, color_data: dict, comp_data: dict, age: int) -> str:
        if not emotions:
            return "Недостаточно данных для построения психологического портрета."

        dominant  = emotions[0]["name"]
        secondary = emotions[1]["name"] if len(emotions) > 1 else None
        age_str   = f"{age}-летнего ребёнка" if age else "ребёнка"

        intro = f"Рисунок {age_str} демонстрирует преобладание эмоции «{dominant}»"
        if secondary:
            intro += f" на фоне «{secondary}»"
        intro += "."

        palette_desc = f"Выбранная {color_data['palette']} палитра с {color_data['brightnessClass']} яркостью "
        if color_data["brightnessClass"] == "тёмный":
            palette_desc += "может свидетельствовать о внутреннем напряжении или сниженном настроении."
        elif color_data["brightnessClass"] == "светлый":
            palette_desc += "указывает на позитивный эмоциональный фон и открытость."
        else:
            palette_desc += "соответствует нормативному эмоциональному состоянию."

        comp_desc = f"Композиция ({comp_data['fillClass']} заполненность, {comp_data['complexity']} детализация) "
        if comp_data["fillClass"] == "высокая":
            comp_desc += "говорит о высокой энергетике и экстраверсии."
        elif comp_data["fillClass"] == "низкая":
            comp_desc += "может указывать на замкнутость или недостаток уверенности."
        else:
            comp_desc += "соответствует возрастной норме."

        return f"{intro} {palette_desc} {comp_desc}"

    # ── Рекомендации ──────────────────────────
    def _generate_recommendations(self, emotions: list, comp_data: dict, age: int) -> list:
        recs = []
        emotion_names = [e["name"] for e in emotions]

        if "тревога" in emotion_names or "страх" in emotion_names:
            recs.append("Провести беседу с ребёнком в спокойной обстановке, выяснить источник тревожности")
            recs.append("Рекомендовать упражнения на релаксацию и арт-терапию с яркими цветами")

        if "агрессия" in emotion_names:
            recs.append("Обратить внимание на социальное окружение ребёнка — возможны конфликты")
            recs.append("Предложить спортивные активности для выхода накопленной энергии")

        if "одиночество" in emotion_names or "грусть" in emotion_names:
            recs.append("Уделить повышенное внимание общению с ребёнком, расширить круг социальных контактов")

        if emotion_names and emotion_names[0] == "радость":
            recs.append("Эмоциональный фон благоприятный — поддерживать текущие условия воспитания")

        if comp_data["fillClass"] == "низкая":
            recs.append("Стимулировать самовыражение через творческие занятия, поощрять инициативу")

        if not recs:
            recs.append("Плановое наблюдение в стандартном режиме")
            recs.append("Повторный анализ рисунков через 2–3 недели для отслеживания динамики")

        recs.append("Результаты анализа носят вспомогательный характер и требуют очной консультации специалиста")
        return recs[:4]

    # ── Факторы риска ─────────────────────────
    def _detect_risk_factors(self, emotions: list, color_data: dict, comp_data: dict) -> list:
        risks = []
        emotion_names = {e["name"]: e["intensity"] for e in emotions}

        if emotion_names.get("страх", 0) > 50:
            risks.append("Высокий уровень страха (>50%)")
        if emotion_names.get("агрессия", 0) > 60:
            risks.append("Повышенная агрессивность (>60%)")
        if emotion_names.get("тревога", 0) > 55:
            risks.append("Выраженная тревожность (>55%)")
        if color_data["brightnessClass"] == "тёмный" and color_data["saturationClass"] == "серый":
            risks.append("Ахроматическая тёмная палитра — возможна депрессивность")
        if comp_data["fillRatio"] < 8:
            risks.append("Крайне низкое заполнение листа (<8%)")
        if emotion_names.get("одиночество", 0) > 50 and emotion_names.get("грусть", 0) > 40:
            risks.append("Сочетание одиночества и грусти")

        return risks

    # ── Общая оценка ──────────────────────────
    def _assess_overall_state(self, emotions: list, risk_factors: list) -> str:
        if len(risk_factors) >= 3:
            return "требует_консультации"
        if len(risk_factors) >= 1:
            return "требует_внимания"
        negative = {"страх", "агрессия", "тревога", "одиночество", "грусть"}
        for e in emotions:
            if e["name"] in negative and e["intensity"] > 65:
                return "требует_внимания"
        return "норма"

    # ── Уверенность модели ────────────────────
    def _estimate_confidence(self, color_data: dict, comp_data: dict) -> int:
        base = 70
        known_colors = len([v for v in color_data.get("colorRatios", {}).values() if v > 2])
        base += min(known_colors * 3, 15)
        if comp_data["fillRatio"] < 5:
            base -= 15
        return max(40, min(95, base))