"""
АртМинд — Психоэмоциональный анализ детских рисунков v3.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Модуль 1 : Тест Люшера        — цвет → эмоции
Модуль 2 : Методика Маховер   — зональный анализ листа
Модуль 3 : Анализ линий       — нажим, характер, хаотичность
Модуль 4 : Сигнатуры радости  — специальный детектор позитивных паттернов
Агрегация: взвешенное суммирование + вето-правила
"""

import cv2
import numpy as np
from PIL import Image
from sklearn.cluster import KMeans
import io
from typing import Optional

# ══════════════════════════════════════════════════════════
# КОНСТАНТЫ — ЦВЕТОВЫЕ ДИАПАЗОНЫ (HSV hue 0–180)
# ══════════════════════════════════════════════════════════

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

# Психологические значения цветов (Люшер)
COLOR_EMOTION_MAP = {
    "красный":       {"агрессия": 0.9, "радость": 0.3},
    "оранжевый":     {"радость": 1.0},
    "жёлтый":        {"радость": 1.0},
    "жёлто-зелёный": {"тревога": 0.8},
    "зелёный":       {"спокойствие": 0.9, "радость": 0.3},
    "голубой":       {"спокойствие": 0.7, "радость": 0.2, "грусть": 0.1},
    "синий":         {"грусть": 0.5, "спокойствие": 0.4, "тревога": 0.2},
    "фиолетовый":    {"тревога": 0.9, "грусть": 0.4},
    "розовый":       {"радость": 1.0, "спокойствие": 0.3},
}

# Психологически тёплые цвета — сигнал радости
WARM_JOY_COLORS  = {"красный", "оранжевый", "жёлтый", "розовый"}
# Психологически холодные цвета — сигнал грусти/покоя
COOL_SAD_COLORS  = {"синий", "фиолетовый"}
# Природные позитивные (небо, трава, солнце)
NATURE_JOY_COLORS = {"жёлтый", "оранжевый", "зелёный", "голубой"}

# ══════════════════════════════════════════════════════════
# КОНСТАНТЫ — ЗОНЫ МАХОВЕР
# ══════════════════════════════════════════════════════════

ZONE_INTERPRETATIONS = {
    "верх":  {"высокая": "Верхняя зона активна — фантазии, устремлённость, оптимизм",
               "средняя": "Умеренная активность верхней зоны — нормативный уровень фантазирования",
               "низкая":  "Верхняя зона пуста — снижение мотивации или депрессивность"},
    "центр": {"высокая": "Центральная зона насыщена — сильное эго, потребность во внимании",
               "средняя": "Центральная зона умеренно заполнена — сбалансированное самовосприятие",
               "низкая":  "Центральная зона пуста — неуверенность в себе, низкая самооценка"},
    "низ":   {"высокая": "Нижняя зона активна — приземлённость, инстинктивность, тревога",
               "средняя": "Нижняя зона умеренно заполнена — нормативный контакт с реальностью",
               "низкая":  "Нижняя зона пуста — оторванность от реальности, мечтательность"},
    "лево":  {"высокая": "Левая сторона активна — фиксация на прошлом, интроверсия",
               "средняя": "Умеренная активность левой стороны — норма",
               "низкая":  "Левая сторона пуста — отрыв от прошлого опыта"},
    "право": {"высокая": "Правая сторона активна — устремлённость в будущее, экстраверсия",
               "средняя": "Умеренная активность правой стороны — норма",
               "низкая":  "Правая сторона пуста — страх будущего, замкнутость"},
}

ZONE_EMOTION_MAP = {
    "верх":  {"высокая": {"радость": 20},          "низкая": {"грусть": 20}},
    "центр": {"высокая": {"агрессия": 10},          "низкая": {"грусть": 15, "тревога": 15}},
    "низ":   {"высокая": {"тревога": 25},            "низкая": {"спокойствие": 10}},
    "лево":  {"высокая": {"грусть": 15},             "низкая": {}},
    "право": {"высокая": {"радость": 15},            "низкая": {"тревога": 15}},
}

# ══════════════════════════════════════════════════════════
# КОНСТАНТЫ — АНАЛИЗ ЛИНИЙ
# ══════════════════════════════════════════════════════════

LINE_PRESSURE_MAP = {
    "сильный": {"агрессия": 25, "тревога": 15},
    "средний": {"спокойствие": 10},
    "слабый":  {"грусть": 20},
}

LINE_CHARACTER_MAP = {
    "прерывистые": {"тревога": 25},
    "плавные":     {"спокойствие": 15, "радость": 5},
    "угловатые":   {"агрессия": 20, "тревога": 10},
}

# ══════════════════════════════════════════════════════════
# КОНСТАНТЫ — СИГНАТУРЫ РАДОСТИ (Модуль 4)
# ══════════════════════════════════════════════════════════
# Паттерны которые однозначно означают радость в детских рисунках

JOY_SIGNATURES = {
    # Яркая насыщенная палитра (много цветных пикселей)
    "vivid_rich": {
        "condition": lambda f: (
            f["n_vivid_colors"] >= 3 and
            f["vivid_coverage"] > 0.15 and
            f["brightness"] > 0.6
        ),
        "bonus": {"радость": 35, },
        "label": "Яркая насыщенная палитра",
    },
    # Тёплые цвета доминируют (жёлтый+оранжевый > 30%)
    "warm_dominant": {
        "condition": lambda f: (
            f["warm_ratio"] > 0.30 and f["brightness"] > 0.55
        ),
        "bonus": {"радость": 30, },
        "label": "Доминирование тёплых цветов",
    },
    # Природная сцена: небо+солнце+трава (голубой+жёлтый+зелёный)
    "nature_scene": {
        "condition": lambda f: (
            f["color_ratios"].get("голубой", 0) > 0.10 and
            f["color_ratios"].get("зелёный", 0) > 0.10 and
            f["brightness"] > 0.65
        ),
        "bonus": {"радость": 25, "спокойствие": 15, },
        "label": "Природная сцена (небо+трава)",
    },
    # Солнечный рисунок: жёлтый + что-то ещё яркое
    "sunny": {
        "condition": lambda f: (
            f["color_ratios"].get("жёлтый", 0) > 0.05 and
            f["brightness"] > 0.75 and
            f["n_vivid_colors"] >= 2
        ),
        "bonus": {"радость": 20, },
        "label": "Солнечный рисунок",
    },
    # Многоцветный (≥4 разных насыщенных цветов) — праздник, радуга
    "multicolor": {
        "condition": lambda f: f["n_vivid_colors"] >= 4,
        "bonus": {"радость": 25, },
        "label": "Многоцветный рисунок",
    },
    # Розовый/тёплый + достаточно насыщенный → любовь/нежность
    "pink_warm": {
        "condition": lambda f: (
            f["color_ratios"].get("розовый", 0) > 0.08 and
            f["brightness"] > 0.6
        ),
        "bonus": {"радость": 35, "спокойствие": 10},
        "label": "Розово-тёплая гамма",
    },
}

# ══════════════════════════════════════════════════════════
# ВЕТО-ПРАВИЛА — блокируют неверные эмоции
# ══════════════════════════════════════════════════════════

VETO_RULES = [
    # Тёмная ахроматическая — радость и энергия заблокированы
    {
        "condition": lambda c, comp, z, l: (
            c["brightnessValue"] < 25 and c["saturationValue"] < 15
        ),
        "caps":   {"радость": 15, },
        "boosts": {"грусть": 40, "тревога": 20},
        "label":  "Тёмная ахроматическая палитра",
    },
    # Тёмная палитра (любая)
    {
        "condition": lambda c, comp, z, l: c["brightnessValue"] < 35,
        "caps":   {"радость": 25, },
        "boosts": {"грусть": 25, "тревога": 20},
        "label":  "Тёмная палитра",
    },
    # Закрашенный лист одним цветом (объектов ≤ 2)
    {
        "condition": lambda c, comp, z, l: (
            comp["fillRatio"] > 90 and comp["numObjects"] <= 2 and
            c["nVividColors"] <= 1
        ),
        "caps":   {"радость": 20},
        "boosts": {"тревога": 30},
        "label":  "Закрашенный лист (подавление)",
    },
    # Сильный нажим + тёмный → нет радости
    {
        "condition": lambda c, comp, z, l: (
            l.get("pressure") == "сильный" and c["brightnessValue"] < 50
        ),
        "caps":   {"радость": 20},
        "boosts": {"агрессия": 15, "тревога": 15},
        "label":  "Сильный нажим + тёмная палитра",
    },
    # Слабый нажим + тёмная холодная → подавленность
    {
        "condition": lambda c, comp, z, l: (
            l.get("pressure") == "слабый" and
            c["palette"] in ("холодная", "ахроматическая (серые тона)") and
            c["brightnessValue"] < 60
        ),
        "caps":   {"агрессия": 15, },
        "boosts": {"грусть": 25},
        "label":  "Слабый нажим + тёмная холодная",
    },
    # Ахроматическая штриховка (хаос без цвета)
    {
        "condition": lambda c, comp, z, l: (
            l.get("chaos") == "высокая" and
            c["palette"] == "ахроматическая (серые тона)"
        ),
        "caps":   {"радость": 20, },
        "boosts": {"тревога": 30},
        "label":  "Ахроматическая штриховка",
    },
    # Тёмная хаотичная штриховка
    {
        "condition": lambda c, comp, z, l: (
            l.get("chaos") == "высокая" and c["brightnessValue"] < 70
        ),
        "caps":   {"радость": 25, },
        "boosts": {"тревога": 30},
        "label":  "Тёмная хаотичная штриховка",
    },
    # Светлый холодный рисунок с малым покрытием → грусть
    {
        "condition": lambda c, comp, z, l: (
            c["palette"] == "холодная" and
            c["brightnessValue"] > 75 and
            c.get("colorCoverage", 100) < 15
        ),
        "caps":   {"тревога": 35, "агрессия": 10, "спокойствие": 35},
        "boosts": {"грусть": 35},
        "label":  "Холодный светлый рисунок с малым покрытием",
    },
]

COMPOSITION_MAP = {
    "заполненность": {
        "высокая": "Активное использование пространства — высокая энергетика, экстраверсия",
        "средняя": "Умеренное использование пространства — сбалансированное состояние",
        "низкая":  "Малое заполнение листа — возможна замкнутость, низкая энергетика",
    },
    "расположение": {
        "верх":  "Рисунок в верхней части — оптимизм, устремлённость к мечте",
        "низ":   "Рисунок в нижней части — тревожность, заземлённость",
        "лево":  "Смещение влево — ориентация на прошлое, интроверсия",
        "право": "Смещение вправо — устремлённость в будущее, экстраверсия",
        "центр": "Центральное расположение — потребность во внимании, эгоцентричность",
    },
    "сложность": {
        "высокая": "Богатая детализация — высокий интеллект, развитое воображение",
        "средняя": "Умеренная детализация — нормативное развитие",
        "низкая":  "Минимальная детализация — возможна тревога или усталость",
    },
}

MODULE_WEIGHTS = {
    "module1_luscher":  0.35,
    "module2_makeover": 0.25,
    "module3_lines":    0.20,
    "module4_joy":      0.20,
}

ALL_EMOTIONS = [
    "радость", "грусть", "тревога", "агрессия", "спокойствие",
]


# ══════════════════════════════════════════════════════════
# КЛАСС АНАЛИЗАТОРА
# ══════════════════════════════════════════════════════════

class DrawingAnalyzer:

    def analyze(self, image_bytes: bytes, child_age: int = None, context: str = "") -> dict:
        img_bgr  = self._load_image(image_bytes)
        img_hsv  = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

        # ── извлечение признаков ─────────────────
        color_data = self._analyze_colors(img_bgr, img_hsv)
        comp_data  = self._analyze_composition(img_gray)
        zone_data  = self._analyze_zones(img_gray)
        line_data  = self._analyze_lines(img_gray)
        joy_data   = self._analyze_joy_signatures(img_hsv, color_data)

        # ── вычисление баллов ────────────────────
        s1 = self._scores_luscher(color_data, comp_data, child_age)
        s2 = self._scores_makeover(zone_data, child_age)
        s3 = self._scores_lines(line_data)
        s4 = self._scores_joy(joy_data)

        # ── агрегация + вето ─────────────────────
        raw   = self._aggregate(s1, s2, s3, s4)
        final = self._apply_veto(raw, color_data, comp_data, zone_data, line_data)

        # ── отчёт ────────────────────────────────
        emotions   = self._to_emotions(final, color_data, comp_data, zone_data, line_data)
        portrait   = self._build_portrait(emotions, color_data, comp_data, zone_data, line_data, child_age)
        recs       = self._recommendations(emotions, comp_data, zone_data, line_data, child_age)
        risks      = self._risk_factors(emotions, color_data, comp_data, zone_data, line_data)
        state      = self._overall_state(emotions, risks)
        confidence = self._confidence(color_data, comp_data, zone_data, line_data)

        return {
            "colorAnalysis":         color_data,
            "composition":           comp_data,
            "zoneAnalysis":          zone_data,
            "lineAnalysis":          line_data,
            "joySignatures":         joy_data,
            "emotions":              emotions,
            "psychologicalPortrait": portrait,
            "riskFactors":           risks,
            "recommendations":       recs,
            "overallState":          state,
            "confidence":            confidence,
            "moduleWeights":         MODULE_WEIGHTS,
        }

    # ════════════════════════════════════════════
    # ЗАГРУЗКА
    # ════════════════════════════════════════════

    def _load_image(self, image_bytes: bytes) -> np.ndarray:
        pil = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        pil = pil.resize((512, 512), Image.LANCZOS)
        return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)

    # ════════════════════════════════════════════
    # МОДУЛЬ 1 — ЛЮШЕР: анализ цвета
    # ════════════════════════════════════════════

    def _analyze_colors(self, bgr: np.ndarray, hsv: np.ndarray) -> dict:
        h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]

        bri_mean = float(v.mean())
        sat_mean = float(s.mean())

        # Насыщенность считаем по цветным пикселям (s>30), чтобы белый фон не занижал
        colored = s > 30
        color_coverage = float(colored.sum()) / s.size
        sat_active = float(s[colored].mean()) if colored.sum() > 200 else sat_mean

        bri_cls = "тёмный" if bri_mean < 80 else ("средний" if bri_mean < 180 else "светлый")
        sat_cls = "серый" if sat_active < 60 else ("приглушён" if sat_active < 120 else "яркий")

        # K-Means доминирующие цвета
        px = bgr.reshape(-1, 3).astype(np.float32)
        sample = px[np.random.choice(len(px), min(3000, len(px)), replace=False)]
        try:
            km = KMeans(n_clusters=5, n_init=5, max_iter=100, random_state=42)
            km.fit(sample)
            dominant = [
                "#{:02x}{:02x}{:02x}".format(int(c[2]), int(c[1]), int(c[0]))
                for c in km.cluster_centers_.astype(int)
            ]
        except Exception:
            dominant = ["#808080"]

        # Доли цветов среди насыщенных пикселей (s>60) — реальный цвет рисунка
        ratios       = self._color_ratios(h, s, threshold=60)
        ratios_vivid = self._color_ratios(h, s, threshold=120)  # особо яркие

        n_vivid = sum(1 for v_ in ratios_vivid.values() if v_ > 0.03)
        n_rich  = sum(1 for v_ in ratios.values()       if v_ > 0.03)

        warm  = sum(ratios.get(c, 0) for c in ["красный", "оранжевый", "жёлтый", "розовый"])
        cool  = sum(ratios.get(c, 0) for c in ["синий", "фиолетовый"])
        nat   = sum(ratios.get(c, 0) for c in ["голубой", "зелёный"])  # природные

        # Тип палитры
        if sat_active < 55:
            palette = "ахроматическая (серые тона)"
        elif warm > 0.50:
            palette = "тёплая"
        elif cool > 0.40:
            palette = "холодная"
        elif n_rich >= 4:
            palette = "многоцветная"
        elif nat > 0.50 and warm > 0.10:
            palette = "природная"       # небо+трава+солнце
        elif warm > cool:
            palette = "тёплая"
        elif cool > warm:
            palette = "холодная"
        else:
            palette = "смешанная"

        return {
            "dominant":        dominant[:3],
            "palette":         palette,
            "brightnessClass": bri_cls,
            "saturationClass": sat_cls,
            "brightnessValue": round(bri_mean / 255 * 100, 1),
            "saturationValue": round(sat_mean / 255 * 100, 1),
            "satActive":       round(sat_active, 1),
            "colorRatios":     {k: round(v_ * 100, 1) for k, v_ in ratios.items() if v_ > 0.01},
            "colorCoverage":   round(color_coverage * 100, 1),
            "nVividColors":    n_vivid,
            "warmRatio":       round(warm * 100, 1),
            "coolRatio":       round(cool * 100, 1),
            "interpretation":  self._color_interp(bri_cls, sat_cls, ratios, palette),
        }

    def _color_ratios(self, h: np.ndarray, s: np.ndarray, threshold: int = 60) -> dict:
        mask_col = s > threshold
        total = mask_col.sum() + 1
        out = {}
        for name, ranges in COLOR_RANGES.items():
            mask = np.zeros_like(h, dtype=bool)
            for lo, hi in ranges:
                mask |= (h >= lo) & (h <= hi)
            out[name] = float((mask & mask_col).sum()) / total
        return out

    def _color_interp(self, bri: str, sat: str, ratios: dict, palette: str) -> str:
        parts = []
        if bri == "тёмный":
            parts.append("Преобладание тёмных тонов указывает на подавленное настроение.")
        elif bri == "светлый":
            parts.append("Светлая палитра свидетельствует об открытости и позитивном фоне.")
        if sat == "серый":
            parts.append("Ахроматическая гамма может говорить об эмоциональной закрытости.")
        elif sat == "яркий":
            parts.append("Насыщенные цвета отражают высокую эмоциональную активность.")
        top = sorted(ratios.items(), key=lambda x: -x[1])[:2]
        for name, ratio in top:
            if ratio > 0.08:
                parts.append(f"Значительная доля {name} ({ratio*100:.0f}%) несёт соответствующую символику.")
        return " ".join(parts) or f"Палитра {palette}, без явных аномалий."

    def _scores_luscher(self, color: dict, comp: dict, age) -> dict:
        sc = {e: 0.0 for e in ALL_EMOTIONS}

        for name, ratio in color.get("colorRatios", {}).items():
            for em, w in COLOR_EMOTION_MAP.get(name, {}).items():
                sc[em] += (ratio / 100) * w * 100

        # Яркость — усиленные дельты
        bri_delta = {
            "тёмный":  {"грусть": 35, "тревога": 30, "радость": -30},
            "средний": {},
            "светлый": {"радость": 25, "спокойствие": 15, "грусть": -15},
        }
        for em, d in bri_delta.get(color["brightnessClass"], {}).items():
            sc[em] += d

        # Насыщенность
        sat_delta = {
            "серый":     {"грусть": 40, "тревога": 15, "спокойствие": -15, "радость": -20},
            "приглушён": {"грусть": 10, "спокойствие": 5},
            "яркий":     {"радость": 25, "агрессия": 10, },
        }
        for em, d in sat_delta.get(color["saturationClass"], {}).items():
            sc[em] += d

        # Цветовое покрытие
        cov = color.get("colorCoverage", 0)
        if cov > 30:
            sc["радость"] += 25
        elif cov > 15:
            sc["радость"] += 8;  
        elif cov < 5:
            sc["грусть"] += 10;  

        # Природная палитра — бонус радости
        if color.get("palette") in ("природная", "многоцветная"):
            sc["радость"] += 25; sc["спокойствие"] += 15

        # Тёплая палитра — бонус радости
        if color.get("palette") == "тёплая":
            sc["радость"] += 10; 

        # Разнообразие цветов
        nv = color.get("nVividColors", 0)
        if nv >= 4:
            sc["радость"] += 15; 
        elif nv >= 2:
            sc["радость"] += 8

        # Композиция
        fill = comp["fillClass"]
        if fill == "низкая":
            sc["грусть"] += 20
        elif fill == "высокая" and comp["numObjects"] > 3:
            sc["радость"] += 20

        loc = comp["location"]
        if loc == "низ":   sc["тревога"] += 12; 
        elif loc == "верх": sc["радость"] += 12

        if comp["complexity"] == "низкая":
            sc["тревога"] += 10
        elif comp["complexity"] == "высокая":
            sc["радость"] += 5

        if age and age < 5:
            sc["тревога"] = max(0, sc["тревога"] - 10)
        if age and age > 10:
            sc["агрессия"] *= 0.85

        return sc

    # ════════════════════════════════════════════
    # МОДУЛЬ 2 — МАХОВЕР: зональный анализ
    # ════════════════════════════════════════════

    def _analyze_composition(self, gray: np.ndarray) -> dict:
        _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        fill = float(np.count_nonzero(binary)) / binary.size

        M = cv2.moments(binary)
        cx = (M["m10"] / M["m00"] / gray.shape[1]) if M["m00"] > 0 else 0.5
        cy = (M["m01"] / M["m00"] / gray.shape[0]) if M["m00"] > 0 else 0.5

        vert = "верх" if cy < 0.4 else ("низ" if cy > 0.6 else "cv")
        hori = "лево" if cx < 0.4 else ("право" if cx > 0.6 else "центр")
        loc  = "центр" if (vert == "cv" and hori == "центр") else (vert if vert != "cv" else hori)

        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        n_obj = len([c for c in contours if cv2.contourArea(c) > 50])
        cmpx  = "высокая" if n_obj > 15 else ("средняя" if n_obj > 5 else "низкая")
        fcls  = "высокая" if fill > 0.35 else ("средняя" if fill > 0.12 else "низкая")

        edges = cv2.Canny(gray, 50, 150)
        ld    = float(np.count_nonzero(edges)) / edges.size

        return {
            "fillRatio":   round(fill * 100, 1),
            "fillClass":   fcls,
            "centerX":     round(cx, 2),
            "centerY":     round(cy, 2),
            "location":    loc,
            "numObjects":  n_obj,
            "complexity":  cmpx,
            "lineDensity": round(ld * 100, 2),
            "style":       f"{fcls} заполненность, {cmpx} детализация",
            "spaceUsage":  fcls,
            "interpretation": (
                f"{COMPOSITION_MAP['заполненность'][fcls]} "
                f"{COMPOSITION_MAP['расположение'].get(loc, '')} "
                f"{COMPOSITION_MAP['сложность'][cmpx]}"
            ),
        }

    def _analyze_zones(self, gray: np.ndarray) -> dict:
        _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        H, W = binary.shape
        zones = {
            "верх":  binary[:H // 3, :],
            "центр": binary[H // 3: 2 * H // 3, :],
            "низ":   binary[2 * H // 3:, :],
            "лево":  binary[:, :W // 2],
            "право": binary[:, W // 2:],
        }
        dens = {k: round(float(np.count_nonzero(v)) / v.size * 100, 1) for k, v in zones.items()}
        cls  = {k: ("высокая" if d > 20 else ("средняя" if d > 7 else "низкая")) for k, d in dens.items()}
        int_ = {k: ZONE_INTERPRETATIONS[k][c] for k, c in cls.items()}

        vb = dens["верх"] - dens["низ"]
        hb = dens["право"] - dens["лево"]
        bal = ("Рисунок смещён вверх — оптимизм" if vb > 5 else
               "Рисунок смещён вниз — тревожность" if vb < -5 else
               "Вертикальный баланс в норме")
        if hb > 5:   bal += ". Преобладает правая сторона — экстраверсия"
        elif hb < -5: bal += ". Преобладает левая сторона — интроверсия"

        return {
            "zoneDensities":         dens,
            "zoneClasses":           cls,
            "zoneInterpretations":   int_,
            "verticalBalance":       round(vb, 1),
            "horizontalBalance":     round(hb, 1),
            "balanceInterpretation": bal,
        }

    def _scores_makeover(self, zone: dict, age) -> dict:
        sc = {e: 0.0 for e in ALL_EMOTIONS}
        for zn, zc in zone["zoneClasses"].items():
            for em, d in ZONE_EMOTION_MAP.get(zn, {}).get(zc, {}).items():
                sc[em] += d
        vb, hb = zone["verticalBalance"], zone["horizontalBalance"]
        if vb < -10: sc["тревога"] += 15; 
        elif vb > 10: sc["радость"] += 10; 
        if hb < -10: sc["грусть"] += 10; 
        elif hb > 10: sc["радость"] += 10
        if age and age < 5:
            sc["тревога"] = max(0, sc["тревога"] - 8)
        return sc

    # ════════════════════════════════════════════
    # МОДУЛЬ 3 — АНАЛИЗ ЛИНИЙ
    # ════════════════════════════════════════════

    def _analyze_lines(self, gray: np.ndarray) -> dict:
        line_mask = gray < 200
        if line_mask.sum() > 100:
            lbri = float(gray[line_mask].mean())
            pv = lbri / 200.0
            pressure = "сильный" if pv < 0.35 else ("средний" if pv < 0.65 else "слабый")
        else:
            pv = 0.5; pressure = "средний"

        edges = cv2.Canny(gray, 30, 100)
        ker   = np.ones((3, 3), np.uint8)
        dil   = cv2.dilate(edges, ker, iterations=2)
        es    = float(edges.sum())
        thr   = float(dil.sum()) / max(es, 1) if es > 0 else 2.0
        thickness = "толстые" if thr > 3.5 else ("средние" if thr > 2.0 else "тонкие")

        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        big = [c for c in contours if len(c) > 10]
        if big:
            tlen  = sum(cv2.arcLength(c, False) for c in big)
            frag  = len(big) / max(tlen / 50, 1)
            sharp = 0
            for c in big[:30]:
                ap = cv2.approxPolyDP(c, 0.04 * cv2.arcLength(c, False), False)
                if len(ap) > 2:
                    pts = ap.reshape(-1, 2).astype(float)
                    for i in range(1, len(pts) - 1):
                        v1 = pts[i-1]-pts[i]; v2 = pts[i+1]-pts[i]
                        n1,n2 = np.linalg.norm(v1), np.linalg.norm(v2)
                        if n1>0 and n2>0 and np.dot(v1,v2)/(n1*n2) < -0.5:
                            sharp += 1
            ar  = sharp / max(len(big), 1)
            char = "прерывистые" if frag > 2.0 else ("угловатые" if ar > 1.5 else "плавные")
        else:
            frag = ar = 0; char = "плавные"

        H, W  = gray.shape
        chaos_v = min(float(len(big)) / max((H * W / 10000), 1), 10.0)
        chaos = "высокая" if chaos_v > 2 else ("средняя" if chaos_v > 0.8 else "низкая")

        return {
            "pressure":       pressure,
            "pressureValue":  round(pv, 2),
            "thickness":      thickness,
            "thicknessRatio": round(thr, 2),
            "character":      char,
            "fragmentRatio":  round(frag, 2),
            "chaos":          chaos,
            "chaosValue":     round(chaos_v, 2),
            "interpretation": self._line_interp(pressure, thickness, char, chaos),
        }

    def _line_interp(self, pressure: str, thickness: str, char: str, chaos: str) -> str:
        pt = {"сильный": "Сильный нажим — высокая напряжённость или агрессия.",
              "средний": "Нажим умеренный — эмоциональное состояние стабильно.",
              "слабый":  "Слабый нажим — низкая энергетика, возможна подавленность."}
        ct = {"прерывистые": "Прерывистые линии — тревога, неуверенность.",
              "плавные":     "Плавные линии — внутреннее спокойствие.",
              "угловатые":   "Угловатые линии — агрессия или напряжение."}
        parts = [pt[pressure], ct[char]]
        if chaos == "высокая":
            parts.append("Высокая хаотичность штриха — возможна тревожность.")
        return " ".join(parts)

    def _scores_lines(self, line: dict) -> dict:
        sc = {e: 0.0 for e in ALL_EMOTIONS}
        for em, d in LINE_PRESSURE_MAP.get(line["pressure"], {}).items():
            sc[em] += d
        for em, d in LINE_CHARACTER_MAP.get(line["character"], {}).items():
            sc[em] += d
        if line["thickness"] == "толстые":
            sc["агрессия"] += 10; 
        elif line["thickness"] == "тонкие":
            sc["грусть"] += 10; 
        if line["chaos"] == "высокая":
            sc["тревога"] += 25; 
        elif line["chaos"] == "низкая":
            sc["спокойствие"] += 10
        return sc

    # ════════════════════════════════════════════
    # МОДУЛЬ 4 — СИГНАТУРЫ РАДОСТИ
    # ════════════════════════════════════════════

    def _analyze_joy_signatures(self, hsv: np.ndarray, color: dict) -> dict:
        h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]

        features = {
            "n_vivid_colors":  color.get("nVividColors", 0),
            "vivid_coverage":  color.get("colorCoverage", 0) / 100,
            "brightness":      color.get("brightnessValue", 0) / 100,
            "warm_ratio":      color.get("warmRatio", 0) / 100,
            "color_ratios":    {k: v_ / 100 for k, v_ in color.get("colorRatios", {}).items()},
        }

        triggered = []
        for name, sig in JOY_SIGNATURES.items():
            try:
                if sig["condition"](features):
                    triggered.append({
                        "name":  name,
                        "label": sig["label"],
                        "bonus": sig["bonus"],
                    })
            except Exception:
                pass

        return {
            "triggered":    triggered,
            "joyScore":     len(triggered),
            "features":     {k: round(v_, 3) if isinstance(v_, float) else v_
                             for k, v_ in features.items() if k != "color_ratios"},
        }

    def _scores_joy(self, joy: dict) -> dict:
        sc = {e: 0.0 for e in ALL_EMOTIONS}
        for sig in joy.get("triggered", []):
            for em, bonus in sig["bonus"].items():
                if em in sc:
                    sc[em] += bonus
        return sc

    # ════════════════════════════════════════════
    # АГРЕГАЦИЯ
    # ════════════════════════════════════════════

    def _aggregate(self, s1: dict, s2: dict, s3: dict, s4: dict) -> dict:
        w = MODULE_WEIGHTS
        return {
            e: max(0.0, min(150.0,
                s1.get(e, 0) * w["module1_luscher"]  +
                s2.get(e, 0) * w["module2_makeover"] +
                s3.get(e, 0) * w["module3_lines"]    +
                s4.get(e, 0) * w["module4_joy"]))
            for e in ALL_EMOTIONS
        }

    # ════════════════════════════════════════════
    # ВЕТО-ПРАВИЛА
    # ════════════════════════════════════════════

    def _apply_veto(self, scores: dict, color: dict, comp: dict, zone: dict, line: dict) -> dict:
        result = dict(scores)
        for rule in VETO_RULES:
            try:
                if rule["condition"](color, comp, zone, line):
                    for em, cap in rule.get("caps", {}).items():
                        if result.get(em, 0) > cap:
                            result[em] = float(cap)
                    for em, boost in rule.get("boosts", {}).items():
                        result[em] = result.get(em, 0) + boost
            except Exception:
                pass
        return {e: max(0.0, min(100.0, v)) for e, v in result.items()}

    # ════════════════════════════════════════════
    # ФИНАЛЬНЫЙ СПИСОК ЭМОЦИЙ
    # ════════════════════════════════════════════

    def _to_emotions(self, scores: dict, color: dict, comp: dict, zone: dict, line: dict) -> list:
        result = []
        for name, score in scores.items():
            v = max(0, min(100, round(score)))
            if v >= 10:
                result.append({
                    "name":      name,
                    "intensity": v,
                    "evidence":  self._evidence(name, color, comp, zone, line),
                })
        result.sort(key=lambda x: -x["intensity"])
        return result[:5]

    def _evidence(self, em: str, color: dict, comp: dict, zone: dict, line: dict) -> str:
        zc = zone["zoneClasses"]
        ev = {
            "радость":     f"Палитра: {color['palette']}; покрытие: {color.get('colorCoverage',0)}%; нажим: {line['pressure']}",
            "грусть":      f"Яркость {color['brightnessValue']}%; нажим: {line['pressure']}; левая зона: {zc.get('лево','—')}",
            "тревога":     f"Линии: {line['character']}; хаос: {line['chaos']}; нижняя зона: {zc.get('низ','—')}",
            "агрессия":    f"Нажим: {line['pressure']}; толщина: {line['thickness']}; центр: {zc.get('центр','—')}",
            "спокойствие": f"Линии: {line['character']}; палитра: {color['palette']}; баланс: {zone['balanceInterpretation'][:40]}",
        }
        return ev.get(em, "Комплексный анализ (Люшер + Маховер + линии + сигнатуры)")

    # ════════════════════════════════════════════
    # ОТЧЁТ
    # ════════════════════════════════════════════

    def _build_portrait(self, emotions, color, comp, zone, line, age) -> str:
        if not emotions:
            return "Недостаточно данных для построения психологического портрета."
        dom  = emotions[0]["name"]
        sec  = emotions[1]["name"] if len(emotions) > 1 else None
        astr = f"{age}-летнего ребёнка" if age else "ребёнка"

        intro = f"Рисунок {astr} демонстрирует преобладание «{dom}»"
        if sec: intro += f" на фоне «{sec}»"
        intro += "."

        pal = ("может свидетельствовать о внутреннем напряжении"
               if color["brightnessClass"] == "тёмный" else
               "указывает на позитивный эмоциональный фон"
               if color["brightnessClass"] == "светлый" else
               "соответствует нормативному состоянию")
        color_desc = f"Выбранная {color['palette']} палитра {pal}."
        line_desc  = f"Анализ линий: {line['pressure']} нажим, {line['character']} штрих."
        zone_desc  = f"Зональный анализ (Маховер): {zone['balanceInterpretation']}."
        comp_desc  = ("Высокое заполнение листа говорит об энергетике."
                      if comp["fillClass"] == "высокая" else
                      "Низкое заполнение листа может указывать на замкнутость."
                      if comp["fillClass"] == "низкая" else
                      "Заполнение листа соответствует норме.")

        return f"{intro} {color_desc} {line_desc} {zone_desc} {comp_desc}"

    def _recommendations(self, emotions, comp, zone, line, age) -> list:
        recs  = []
        names = [e["name"] for e in emotions]
        zc    = zone["zoneClasses"]

        if "тревога" in names:
            recs.append("Провести беседу в спокойной обстановке, выяснить источник тревожности")
            recs.append("Рекомендовать упражнения на релаксацию и арт-терапию с яркими цветами")
        if "агрессия" in names:
            recs.append("Обратить внимание на социальное окружение — возможны конфликты")
            recs.append("Предложить спортивные активности для выхода накопленной энергии")
        if "грусть" in names:
            recs.append("Уделить повышенное внимание общению, поддержать эмоциональный контакт с ребёнком")
        if line["pressure"] == "слабый":
            recs.append("Слабый нажим — поощрять уверенность, использовать яркие материалы")
        if line["character"] == "прерывистые":
            recs.append("Прерывистые линии — рекомендованы занятия по снижению стресса")
        if zc.get("центр") == "низкая":
            recs.append("Укреплять самооценку через похвалу и поддержку инициативы")
        if zc.get("верх") == "низкая":
            recs.append("Стимулировать фантазию через творческие игры и чтение")
        if names and names[0] == "радость":
            recs.append("Эмоциональный фон благоприятный — поддерживать текущие условия воспитания")
        if not recs:
            recs.append("Плановое наблюдение в стандартном режиме")
            recs.append("Повторный анализ через 2–3 недели для отслеживания динамики")
        recs.append("Результаты носят вспомогательный характер и требуют очной консультации специалиста")
        return recs[:4]

    def _risk_factors(self, emotions, color, comp, zone, line) -> list:
        risks = []
        em = {e["name"]: e["intensity"] for e in emotions}
        zc = zone["zoneClasses"]

        if em.get("агрессия", 0) > 60:
            risks.append("Повышенная агрессивность (>60%) — возможны конфликты в окружении")
        if em.get("тревога", 0) > 55:
            risks.append("Выраженная тревожность (>55%) — требует внимания педагога")
        if em.get("грусть", 0) > 55:
            risks.append("Выраженная грусть (>55%) — возможна эмоциональная подавленность")
        if color["brightnessClass"] == "тёмный" and color["saturationClass"] == "серый":
            risks.append("Ахроматическая тёмная палитра — сигнал депрессивного состояния")
        if comp["fillRatio"] < 8:
            risks.append("Крайне низкое заполнение листа (<8%) — замкнутость или апатия")
        if line["pressure"] == "слабый" and em.get("грусть", 0) > 30:
            risks.append("Слабый нажим + грусть — возможна подавленность")
        if line["character"] == "прерывистые" and em.get("тревога", 0) > 30:
            risks.append("Прерывистые линии + тревога — признаки эмоционального стресса")
        if zc.get("центр") == "низкая" and zc.get("низ") == "высокая":
            risks.append("Маховер: пустой центр + активный низ — нестабильность самооценки")
        if zone["verticalBalance"] < -15:
            risks.append("Маховер: сильный сдвиг вниз — выраженная тревожность")
        return risks

    def _overall_state(self, emotions, risks) -> str:
        if len(risks) >= 3: return "требует_консультации"
        if len(risks) >= 1: return "требует_внимания"
        negative = {"агрессия", "тревога", "грусть"}
        for e in emotions:
            if e["name"] in negative and e["intensity"] > 60:
                return "требует_внимания"
        return "норма"

    def _confidence(self, color, comp, zone, line) -> int:
        base = 70
        base += min(color.get("nVividColors", 0) * 3, 12)
        base += min(sum(1 for c in zone["zoneClasses"].values() if c != "низкая") * 2, 8)
        if line["pressure"] != "средний": base += 4
        if line["character"] != "плавные": base += 3
        if comp["fillRatio"] < 5: base -= 15
        return max(45, min(96, base))