"""
АртМинд — Психоэмоциональный анализ детских рисунков v5.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Модуль 1 : Тест Люшера          — цвет → эмоции (расширен)
Модуль 2 : Методика Маховер     — зональный анализ листа
Модуль 3 : Анализ линий         — нажим, характер, хаотичность
Модуль 4 : Сигнатуры радости    — детектор позитивных паттернов
Модуль 5 : Детектор объектов    — контурный анализ OpenCV
Модуль 6 : Haar-каскады         — детектор лиц и улыбок
Модуль 7 : LBP текстура         — анализ текстуры штриха
Модуль 8 : FFT частотный анализ — хаотичность через спектр

Новое в v5.0:
  + Модуль 6: Haar-каскады (лица, улыбки) встроены в OpenCV
  + Модуль 7: LBP-текстура штриха
  + Модуль 8: FFT-анализ пространственных частот
  + Расширенная психология цветов (чёрный, серый, коричневый)
  + Детектор пустого рисунка
  + Нормализация зон по заполненности
  + Возрастная калибровка + контекст-адаптация
"""

import cv2
import numpy as np
from PIL import Image
from sklearn.cluster import KMeans
import io
import math
from typing import Optional


# ── Утилита: numpy → JSON-safe ─────────────────────────────────────────────
def _to_json_safe(obj):
    """Рекурсивно конвертирует numpy-типы в стандартные Python-типы."""
    if isinstance(obj, dict):
        return {k: _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_json_safe(v) for v in obj]
    if isinstance(obj, np.integer):  return int(obj)
    if isinstance(obj, np.floating): return float(obj)
    if isinstance(obj, np.bool_):    return bool(obj)
    if isinstance(obj, np.ndarray):  return obj.tolist()
    return obj


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
    "коричневый":    [(10, 25)],   # hue 10-25 + низкая насыщенность — детектируется отдельно
}

COLOR_EMOTION_MAP = {
    "красный":       {"агрессия": 1.0, "радость": 0.4, "тревога": 0.2},
    "оранжевый":     {"радость": 1.0, "агрессия": 0.2},
    "жёлтый":        {"радость": 1.0, "спокойствие": 0.2},
    "жёлто-зелёный": {"тревога": 0.7, "спокойствие": 0.3},
    "зелёный":       {"спокойствие": 0.9, "радость": 0.4},
    "голубой":       {"спокойствие": 0.8, "радость": 0.2, "грусть": 0.1},
    "синий":         {"грусть": 0.6, "спокойствие": 0.4, "тревога": 0.1},
    "фиолетовый":    {"тревога": 0.9, "грусть": 0.5},
    "розовый":       {"радость": 1.0, "спокойствие": 0.4},
    "коричневый":    {"грусть": 0.5, "тревога": 0.3, "спокойствие": 0.2},
    "чёрный":        {"агрессия": 0.6, "грусть": 0.8, "тревога": 0.7},
    "серый":         {"грусть": 0.7, "тревога": 0.4, "спокойствие": 0.1},
}

WARM_JOY_COLORS   = {"красный", "оранжевый", "жёлтый", "розовый"}
COOL_SAD_COLORS   = {"синий", "фиолетовый", "серый"}
DARK_RISK_COLORS  = {"чёрный", "серый", "коричневый"}
NATURE_JOY_COLORS = {"жёлтый", "оранжевый", "зелёный", "голубой"}

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
    "верх":  {"высокая": {"радость": 20},        "низкая": {"грусть": 20}},
    "центр": {"высокая": {"агрессия": 10},        "низкая": {"грусть": 15, "тревога": 15}},
    "низ":   {"высокая": {"тревога": 25},          "низкая": {"спокойствие": 10}},
    "лево":  {"высокая": {"грусть": 15},           "низкая": {}},
    "право": {"высокая": {"радость": 15},          "низкая": {"тревога": 15}},
}

COMPOSITION_MAP = {
    "заполненность": {
        "высокая": "Высокое заполнение листа — энергия, активность.",
        "средняя": "Среднее заполнение листа — норма.",
        "низкая":  "Низкое заполнение листа — замкнутость или апатия.",
    },
    "расположение": {
        "верх":  "Смещение вверх — оптимизм, фантазии",
        "низ":   "Смещение вниз — тревожность, приземлённость",
        "лево":  "Смещение влево — ориентация на прошлое, интроверсия",
        "право": "Смещение вправо — устремлённость в будущее, экстраверсия",
        "центр": "Центральное расположение — потребность во внимании",
    },
    "сложность": {
        "высокая": "Богатая детализация — высокий интеллект, развитое воображение.",
        "средняя": "Умеренная детализация — нормативное развитие.",
        "низкая":  "Минимальная детализация — возможна тревога или усталость.",
    },
}

LINE_PRESSURE_MAP = {
    "сильный": {"агрессия": 25, "тревога": 15},
    "средний": {"спокойствие": 10},
    "слабый":  {"грусть": 20, "тревога": 10},
}

LINE_CHARACTER_MAP = {
    "прерывистые": {"тревога": 25, "грусть": 10},
    "плавные":     {"спокойствие": 15, "радость": 5},
    "угловатые":   {"агрессия": 20, "тревога": 10},
}

JOY_SIGNATURES = {
    "vivid_rich": {
        "condition": lambda f: f["n_vivid_colors"] >= 3 and f["vivid_coverage"] > 0.15 and f["brightness"] > 0.6,
        "bonus": {"радость": 35}, "aggression_cap": 50, "label": "Яркая насыщенная палитра",
    },
    "warm_dominant": {
        "condition": lambda f: f["warm_ratio"] > 0.35,
        "bonus": {"радость": 30}, "aggression_cap": 55, "label": "Тёплые тона доминируют",
    },
    "multicolor": {
        "condition": lambda f: f["n_vivid_colors"] >= 5,
        "bonus": {"радость": 25}, "aggression_cap": 45, "label": "Многоцветность",
    },
    "nature_palette": {
        "condition": lambda f: sum(f["color_ratios"].get(c, 0) for c in ["жёлтый", "зелёный", "голубой", "оранжевый"]) > 0.4,
        "bonus": {"радость": 20, "спокойствие": 15}, "aggression_cap": 60, "label": "Природная палитра",
    },
    "bright_light": {
        "condition": lambda f: f["brightness"] > 0.78 and f["vivid_coverage"] > 0.1,
        "bonus": {"радость": 20, "спокойствие": 10}, "aggression_cap": 60, "label": "Яркий светлый фон",
    },
}

AGE_NORMS = {
    (3, 5):  {"label": "Дошкольники (3–5 лет)", "тревога": -15, "агрессия": -10, "спокойствие": 5, "fill_low_ok": True, "chaos_ok": True},
    (6, 8):  {"label": "Младший школьный возраст (6–8 лет)", "тревога": -5, "агрессия": -5},
    (9, 12): {"label": "Средний школьный возраст (9–12 лет)"},
    (13, 18):{"label": "Подростки (13–18 лет)", "агрессия": -12, "грусть": -10, "тревога": -8, "dark_ok": True},
}

AGE_STATE_THRESHOLDS = {
    (3, 5):   {"консультация": 4, "внимание": 2},
    (6, 8):   {"консультация": 3, "внимание": 1},
    (9, 12):  {"консультация": 3, "внимание": 1},
    (13, 18): {"консультация": 4, "внимание": 2},
}

CONTEXT_STRESS_KEYWORDS = [
    "смерть", "умер", "похороны", "развод", "расстались", "разлука",
    "переезд", "новая школа", "буллинг", "бьют", "обижают", "конфликт",
    "болезнь", "больница", "операция", "страх", "кошмары", "не спит",
    "плачет", "замкнулся", "агрессивен", "дерётся", "тревожится",
    "потеря", "горе", "стресс", "травма", "насилие",
]
CONTEXT_POSITIVE_KEYWORDS = [
    "счастлив", "радуется", "активный", "весёлый", "дружит", "успевает",
    "хорошо", "отлично", "спокойный", "позитивный",
]

MODULE_WEIGHTS = {
    "module1_luscher":  0.25,
    "module2_makeover": 0.20,
    "module3_lines":    0.15,
    "module4_joy":      0.12,
    "module5_objects":  0.13,
    "module6_haar":     0.08,
    "module7_lbp":      0.04,
    "module8_fft":      0.03,
}

ALL_EMOTIONS = ["радость", "грусть", "тревога", "агрессия", "спокойствие"]


class DrawingAnalyzer:

    def analyze(self, image_bytes: bytes, child_age: Optional[int] = None, context: str = "") -> dict:
        img_bgr  = self._load_image(image_bytes)
        img_hsv  = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        is_empty = self._is_empty_drawing(img_gray)

        color_data = self._analyze_colors(img_bgr, img_hsv)
        comp_data  = self._analyze_composition(img_gray)
        zone_data  = self._analyze_zones(img_gray, comp_data)
        line_data  = self._analyze_lines(img_gray)
        joy_data   = self._analyze_joy_signatures(img_hsv, color_data)
        obj_data   = self._analyze_objects(img_bgr, img_gray)
        haar_data  = self._analyze_haar(img_gray)
        lbp_data   = self._analyze_lbp(img_gray)
        fft_data   = self._analyze_fft(img_gray)
        ctx_data   = self._parse_context(context)

        s1 = self._scores_luscher(color_data, comp_data, child_age)
        s2 = self._scores_makeover(zone_data, child_age)
        s3 = self._scores_lines(line_data)
        s4 = self._scores_joy(joy_data)
        s5 = self._scores_objects(obj_data)
        s6 = self._scores_haar(haar_data)
        s7 = self._scores_lbp(lbp_data)
        s8 = self._scores_fft(fft_data)

        raw    = self._aggregate(s1, s2, s3, s4, s5, s6, s7, s8)
        vetoed = self._apply_veto(raw, color_data, comp_data, zone_data, line_data, joy_data)
        aged   = self._apply_age_correction(vetoed, child_age, color_data, line_data, is_empty)
        final  = self._apply_context_correction(aged, ctx_data)

        emotions = self._to_emotions(final, color_data, comp_data, zone_data, line_data)
        portrait = self._build_portrait(emotions, color_data, comp_data, zone_data, line_data, child_age, haar_data)
        recs     = self._recommendations(emotions, comp_data, zone_data, line_data, child_age, ctx_data, haar_data)
        risks    = self._risk_factors(emotions, color_data, comp_data, zone_data, line_data, ctx_data, haar_data)
        state    = self._overall_state(emotions, risks, child_age)
        conf     = self._confidence(color_data, comp_data, zone_data, line_data, haar_data, fft_data)
        content  = self._build_content_analysis(obj_data, haar_data)
        age_norm = self._get_age_norms(child_age)

        result = {
            "colorAnalysis":         color_data,
            "composition":           comp_data,
            "zoneAnalysis":          zone_data,
            "lineAnalysis":          line_data,
            "contentAnalysis":       content,
            "emotions":              emotions,
            "psychologicalPortrait": portrait,
            "riskFactors":           risks,
            "recommendations":       recs,
            "overallState":          state,
            "confidence":            conf,
            "moduleWeights":         MODULE_WEIGHTS,
            "analysisMode":          "opencv",
            "ageNormLabel":          age_norm.get("label", "") if age_norm else "",
            "contextAnalysis":       ctx_data,
            "technicalData": {
                "lbp":     lbp_data,
                "fft":     fft_data,
                "haar":    haar_data,
                "isEmpty": is_empty,
            },
        }
        return _to_json_safe(result)

    def _load_image(self, image_bytes: bytes) -> np.ndarray:
        pil = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        pil = pil.resize((512, 512), Image.LANCZOS)
        return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)

    def _is_empty_drawing(self, gray: np.ndarray) -> bool:
        _, binary = cv2.threshold(gray, 230, 255, cv2.THRESH_BINARY_INV)
        return float(np.count_nonzero(binary)) / binary.size < 0.02

    # ── МОДУЛЬ 1 ЛЮШЕР ──────────────────────────────────

    def _analyze_colors(self, bgr: np.ndarray, hsv: np.ndarray) -> dict:
        h, s, v = hsv[:,:,0], hsv[:,:,1], hsv[:,:,2]
        bri_mean = float(v.mean())
        colored  = s > 30
        color_coverage = float(colored.sum()) / s.size
        sat_active = float(s[colored].mean()) if colored.sum() > 200 else float(s.mean())
        bri_cls = "тёмный" if bri_mean < 80 else ("средний" if bri_mean < 180 else "светлый")
        sat_cls = "серый" if sat_active < 60 else ("приглушён" if sat_active < 120 else "яркий")
        dark_ratio = float((v < 50).sum()) / v.size
        gray_ratio = float(((s < 40) & (v > 40) & (v < 200)).sum()) / s.size

        px = bgr.reshape(-1, 3).astype(np.float32)
        sample = px[np.random.choice(len(px), min(3000, len(px)), replace=False)]
        try:
            km = KMeans(n_clusters=5, n_init=5, max_iter=100, random_state=42)
            km.fit(sample)
            dominant = ["#{:02x}{:02x}{:02x}".format(int(c[2]), int(c[1]), int(c[0])) for c in km.cluster_centers_.astype(int)]
        except Exception:
            dominant = ["#808080"]

        ratios  = self._color_ratios(h, s, v)
        warm_r  = sum(ratios.get(c, 0) for c in WARM_JOY_COLORS)
        cool_r  = sum(ratios.get(c, 0) for c in COOL_SAD_COLORS)
        dark_r  = sum(ratios.get(c, 0) for c in DARK_RISK_COLORS) + dark_ratio * 100
        vivid_c = sum(1 for c, r in ratios.items() if r > 5)

        if bri_mean < 70 or dark_ratio > 0.3:
            palette = "ахроматическая (серые тона)"
        elif vivid_c >= 5:
            palette = "многоцветная"
        elif warm_r > 40:
            palette = "тёплая"
        elif cool_r > 40:
            palette = "холодная"
        elif sum(ratios.get(c, 0) for c in NATURE_JOY_COLORS) > 35:
            palette = "природная"
        else:
            palette = "смешанная"

        return {
            "dominant":        dominant,
            "palette":         palette,
            "brightnessClass": bri_cls,
            "saturationClass": sat_cls,
            "brightnessValue": round(bri_mean / 255 * 100, 1),
            "saturationValue": round(sat_active / 255 * 100, 1),
            "colorRatios":     {k: round(vv, 1) for k, vv in ratios.items() if vv > 1},
            "colorCoverage":   round(color_coverage * 100, 1),
            "nVividColors":    vivid_c,
            "warmRatio":       round(warm_r, 1),
            "coolRatio":       round(cool_r, 1),
            "darkRatio":       round(dark_r, 1),
            "grayRatio":       round(gray_ratio * 100, 1),
            "interpretation":  self._color_interp(palette, bri_cls, sat_cls, warm_r, dark_ratio),
        }

    def _color_ratios(self, h, s, v) -> dict:
        total  = h.size
        ratios = {}
        ratios["чёрный"] = float((v < 40).sum()) / total * 100
        ratios["серый"]  = float(((s < 40) & (v >= 40) & (v < 200)).sum()) / total * 100
        chromatic = s > 40
        for name, ranges in COLOR_RANGES.items():
            if not ranges:
                continue
            mask = np.zeros(h.shape, dtype=bool)
            for lo, hi in ranges:
                mask |= (h >= lo) & (h < hi)
            mask &= chromatic
            if name == "коричневый":
                mask &= (s > 20) & (s < 100) & (v < 150)
            ratios[name] = float(mask.sum()) / total * 100
        return ratios

    def _color_interp(self, palette, bri_cls, sat_cls, warm_r, dark_ratio) -> str:
        parts = []
        if dark_ratio > 0.3:
            parts.append("Преобладание тёмных тонов сигнализирует о подавленном или тревожном состоянии.")
        if palette == "тёплая":
            parts.append("Тёплая палитра (Люшер) — эмоциональная открытость, позитивный фон.")
        elif palette == "холодная":
            parts.append("Холодная палитра (Люшер) — замкнутость, возможная грусть.")
        elif palette == "многоцветная":
            parts.append("Многоцветность — богатство эмоций, высокая экспрессивность.")
        elif palette == "ахроматическая (серые тона)":
            parts.append("Ахроматическая гамма — эмоциональная подавленность, уход в себя.")
        if bri_cls == "светлый":
            parts.append("Высокая яркость — оптимизм и энергия.")
        elif bri_cls == "тёмный":
            parts.append("Тёмный фон — напряжение или тревога.")
        if sat_cls == "яркий":
            parts.append("Высокая насыщенность — эмоциональная интенсивность.")
        return " ".join(parts) if parts else "Стандартная цветовая гамма."

    def _scores_luscher(self, color: dict, comp: dict, age) -> dict:
        sc = {e: 0.0 for e in ALL_EMOTIONS}
        for cname, ratio in color.get("colorRatios", {}).items():
            em_map = COLOR_EMOTION_MAP.get(cname, {})
            w = ratio / 100.0
            for em, strength in em_map.items():
                sc[em] += strength * w * 100
        bri = color["brightnessValue"]
        if bri < 35:
            sc["грусть"] += 20; sc["тревога"] += 15
        elif bri > 75:
            sc["радость"] += 15
        sat = color["saturationValue"]
        if sat < 25:
            sc["грусть"] += 15
        elif sat > 65:
            sc["радость"] += 10
        fill = comp["fillClass"]
        if fill == "низкая":
            sc["грусть"] += 20
        elif fill == "высокая" and comp["numObjects"] > 3:
            sc["радость"] += 20
        loc = comp["location"]
        if loc == "низ":   sc["тревога"] += 12
        elif loc == "верх": sc["радость"] += 12
        if comp["complexity"] == "низкая":
            sc["тревога"] += 10
        elif comp["complexity"] == "высокая":
            sc["радость"] += 5
        if color.get("darkRatio", 0) > 50:
            sc["агрессия"] += 15; sc["грусть"] += 15
        return sc

    # ── МОДУЛЬ 2 МАХОВЕР ────────────────────────────────

    def _smart_binary(self, gray: np.ndarray) -> np.ndarray:
        """Адаптивная бинаризация: Otsu + морфология. Работает для фото и сканов."""
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        _, otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        # Для очень светлых рисунков (карандаш) Otsu может дать порог ~200-220
        # Дополнительно: адаптивный порог для локальных деталей
        adaptive = cv2.adaptiveThreshold(blur, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 8)
        # Объединяем: берём объединение обеих масок
        combined = cv2.bitwise_or(otsu, adaptive)
        # Убираем шум
        kernel = np.ones((2, 2), np.uint8)
        combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel)
        return combined

    def _analyze_composition(self, gray: np.ndarray) -> dict:
        binary = self._smart_binary(gray)
        fill = float(np.count_nonzero(binary)) / binary.size
        M  = cv2.moments(binary)
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

    def _analyze_zones(self, gray: np.ndarray, comp_data: dict) -> dict:
        binary = self._smart_binary(gray)
        H, W = binary.shape
        zones = {
            "верх":  binary[:H//3, :],
            "центр": binary[H//3:2*H//3, :],
            "низ":   binary[2*H//3:, :],
            "лево":  binary[:, :W//2],
            "право": binary[:, W//2:],
        }
        dens = {k: float(np.count_nonzero(vv)) / vv.size * 100 for k, vv in zones.items()}
        total_density = float(np.count_nonzero(binary)) / binary.size * 100
        if total_density > 0.5:
            norm = {k: d / total_density for k, d in dens.items()}
        else:
            norm = {k: 1.0 for k in dens}
        cls  = {k: ("высокая" if norm[k] > 1.3 else ("средняя" if norm[k] > 0.5 else "низкая")) for k in dens}
        int_ = {k: ZONE_INTERPRETATIONS[k][cls[k]] for k in cls}
        vb = dens["верх"] - dens["низ"]
        hb = dens["право"] - dens["лево"]
        bal = ("Рисунок смещён вверх — оптимизм" if vb > 5 else
               "Рисунок смещён вниз — тревожность" if vb < -5 else "Вертикальный баланс в норме")
        if hb > 5:    bal += ". Преобладает правая сторона — экстраверсия"
        elif hb < -5: bal += ". Преобладает левая сторона — интроверсия"
        return {
            "zoneDensities":         {k: round(d, 1) for k, d in dens.items()},
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
        if vb < -10: sc["тревога"] += 15
        elif vb > 10: sc["радость"] += 10
        if hb < -10: sc["грусть"] += 10
        elif hb > 10: sc["радость"] += 10
        if age and age < 5:
            sc["тревога"] = max(0, sc["тревога"] - 8)
        return sc

    # ── МОДУЛЬ 3 ЛИНИИ ──────────────────────────────────

    def _analyze_lines(self, gray: np.ndarray) -> dict:
        # ── Нажим: чем ТЕМНЕЕ пиксели штриха — тем СИЛЬНЕЕ нажим ──
        # Используем адаптивную маску: пиксели темнее среднего фона
        bg_level  = float(np.percentile(gray, 90))   # яркость фона (90й перцентиль)
        threshold = bg_level * 0.75                   # штрих темнее фона на 25%
        line_mask = gray < threshold
        if line_mask.sum() > 200:
            lbri     = float(gray[line_mask].mean())
            # Нормируем: 0 = абсолютно чёрный (сильный), bg_level = фон (слабый)
            darkness = 1.0 - (lbri / max(bg_level, 1))
            pressure = "сильный" if darkness > 0.65 else ("средний" if darkness > 0.35 else "слабый")
            pv       = round(darkness, 2)
        else:
            pv = 0.5; pressure = "средний"
        edges = cv2.Canny(gray, 30, 100)
        ker   = np.ones((3,3), np.uint8)
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
                        n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
                        if n1 > 0 and n2 > 0 and np.dot(v1,v2)/(n1*n2) < -0.5:
                            sharp += 1
            ar   = sharp / max(len(big), 1)
            char = "прерывистые" if frag > 2.0 else ("угловатые" if ar > 1.5 else "плавные")
        else:
            frag = 0; ar = 0; char = "плавные"

        # ── Хаотичность: разброс направлений градиентов (не количество контуров!) ──
        # Метод: std углов градиента Собеля. Хаотичный штрих = много разных направлений.
        gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        mag_s, ang = cv2.cartToPolar(gx, gy, angleInDegrees=True)
        strong = mag_s > (mag_s.max() * 0.15)      # только значимые края
        if strong.sum() > 100:
            angles    = ang[strong]
            # Нормализуем в [0,1] и считаем цикличное std
            ang_rad   = angles * np.pi / 180.0
            sin_std   = float(np.std(np.sin(ang_rad)))
            cos_std   = float(np.std(np.cos(ang_rad)))
            chaos_v   = round((sin_std + cos_std) / 2.0, 3)  # 0..~0.7
            chaos     = "высокая" if chaos_v > 0.42 else ("средняя" if chaos_v > 0.28 else "низкая")
        else:
            chaos_v = 0.3; chaos = "средняя"
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

    def _line_interp(self, pressure, thickness, char, chaos) -> str:
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
        if line["thickness"] == "толстые":   sc["агрессия"] += 10
        elif line["thickness"] == "тонкие":  sc["грусть"] += 10
        if line["chaos"] == "высокая":       sc["тревога"] += 25
        elif line["chaos"] == "низкая":      sc["спокойствие"] += 10
        return sc

    # ── МОДУЛЬ 4 СИГНАТУРЫ РАДОСТИ ──────────────────────

    def _analyze_joy_signatures(self, hsv: np.ndarray, color: dict) -> dict:
        features = {
            "n_vivid_colors": color.get("nVividColors", 0),
            "vivid_coverage": color.get("colorCoverage", 0) / 100,
            "brightness":     color.get("brightnessValue", 0) / 100,
            "warm_ratio":     color.get("warmRatio", 0) / 100,
            "color_ratios":   {k: vv/100 for k, vv in color.get("colorRatios", {}).items()},
        }
        triggered = []
        for name, sig in JOY_SIGNATURES.items():
            try:
                if sig["condition"](features):
                    triggered.append({"name": name, "label": sig["label"], "bonus": sig["bonus"],
                                      "aggression_cap": sig.get("aggression_cap", 100)})
            except Exception:
                pass
        return {"triggered": triggered, "joyScore": len(triggered),
                "features": {k: round(vv, 3) if isinstance(vv, float) else vv
                             for k, vv in features.items() if k != "color_ratios"}}

    def _scores_joy(self, joy: dict) -> dict:
        sc = {e: 0.0 for e in ALL_EMOTIONS}
        for sig in joy.get("triggered", []):
            for em, bonus in sig["bonus"].items():
                if em in sc: sc[em] += bonus
        return sc

    # ── МОДУЛЬ 5 ОБЪЕКТЫ ────────────────────────────────

    def _analyze_objects(self, bgr: np.ndarray, gray: np.ndarray) -> dict:
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        binary = self._smart_binary(gray)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        H, W = gray.shape
        has_sun = has_house = has_human = has_nature = has_dark = has_smile = False
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 100: continue
            peri = cv2.arcLength(cnt, True)
            if peri == 0: continue
            circ   = 4 * math.pi * area / (peri * peri)
            x, y, w, h = cv2.boundingRect(cnt)
            aspect   = w / max(h, 1)
            solidity = area / max(w * h, 1)
            cy_ratio = (y + h / 2) / H
            if circ > 0.55 and cy_ratio < 0.4 and area > 300:
                has_sun = True
            if solidity > 0.6 and 0.5 < aspect < 2.0 and area > 1000:
                has_house = True
            if aspect < 0.8 and h > W * 0.15 and area > 500:
                has_human = True
            if 0.3 < circ < 0.75 and area < 2000 and area > 50:
                hull = cv2.convexHull(cnt)
                hull_area = cv2.contourArea(hull)
                if hull_area > 0 and area / hull_area < 0.6:
                    has_smile = True
        green_mask = cv2.inRange(hsv, (40,40,40), (90,255,255))
        blue_mask  = cv2.inRange(hsv, (90,40,80), (130,255,255))
        if green_mask.sum()/(H*W) > 0.08 or blue_mask.sum()/(H*W) > 0.08:
            has_nature = True
        if (gray < 50).mean() > 0.12:
            has_dark = True
        detected = []
        if has_sun:    detected.append("солнце")
        if has_house:  detected.append("дом")
        if has_human:  detected.append("человек")
        if has_nature: detected.append("природа")
        if has_smile:  detected.append("улыбка")
        if has_dark:   detected.append("тёмные_элементы")
        return {"hasSun": has_sun, "hasHouse": has_house, "hasHuman": has_human,
                "hasNature": has_nature, "hasDarkElements": has_dark, "hasSmile": has_smile,
                "detectedObjects": detected}

    def _scores_objects(self, obj: dict) -> dict:
        sc = {e: 0.0 for e in ALL_EMOTIONS}
        if obj["hasSun"]:          sc["радость"] += 30; sc["спокойствие"] += 15
        if obj["hasHouse"]:        sc["спокойствие"] += 20; sc["радость"] += 10
        if obj["hasSmile"]:        sc["радость"] += 25
        if obj["hasNature"]:       sc["спокойствие"] += 15; sc["радость"] += 10
        if obj["hasDarkElements"]: sc["тревога"] += 20; sc["агрессия"] += 10; sc["грусть"] += 15
        if obj["hasHuman"]:        sc["радость"] += 5
        return sc

    # ── МОДУЛЬ 6 HAAR-КАСКАДЫ ───────────────────────────

    def _analyze_haar(self, gray: np.ndarray) -> dict:
        result = {"faces_found": 0, "smiles_found": 0, "has_face": False,
                  "has_smile": False, "interpretation": ""}
        try:
            face_cascade  = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
            smile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_smile.xml")
            eq     = cv2.equalizeHist(gray)
            faces  = face_cascade.detectMultiScale(eq, scaleFactor=1.05, minNeighbors=2, minSize=(20,20))
            n_faces = len(faces) if faces is not None and len(faces) > 0 else 0
            result["faces_found"] = n_faces
            result["has_face"]    = n_faces > 0
            n_smiles = 0
            if n_faces > 0:
                for (fx, fy, fw, fh) in faces:
                    roi = eq[fy:fy+fh, fx:fx+fw]
                    smiles = smile_cascade.detectMultiScale(roi, scaleFactor=1.1, minNeighbors=10, minSize=(10,10))
                    if smiles is not None and len(smiles) > 0:
                        n_smiles += len(smiles)
            result["smiles_found"] = n_smiles
            result["has_smile"]    = n_smiles > 0
            if n_faces > 0 and n_smiles > 0:
                result["interpretation"] = f"Обнаружено {n_faces} лицо(-а) с улыбкой — позитивный эмоциональный образ."
            elif n_faces > 0:
                result["interpretation"] = f"Обнаружено {n_faces} лицо(-а) без явной улыбки."
            else:
                result["interpretation"] = "Нарисованные лица не обнаружены."
        except Exception as e:
            result["interpretation"] = f"Haar-анализ: {e}"
        return result

    def _scores_haar(self, haar: dict) -> dict:
        sc = {e: 0.0 for e in ALL_EMOTIONS}
        if haar["has_face"] and haar["has_smile"]:
            sc["радость"] += 35; sc["спокойствие"] += 10
        elif haar["has_face"] and not haar["has_smile"]:
            sc["грусть"] += 10; sc["тревога"] += 5
        return sc

    # ── МОДУЛЬ 7 LBP ТЕКСТУРА ───────────────────────────

    def _analyze_lbp(self, gray: np.ndarray) -> dict:
        try:
            # ── LBP только на ШТРИХАХ (не на белом фоне!) ──
            bg_level  = float(np.percentile(gray, 90))
            threshold = bg_level * 0.80
            line_mask = gray < threshold          # только пиксели штриха
            if line_mask.sum() < 300:
                return {"energy": 0.5, "entropy": 0.5, "textureType": "неизвестно",
                        "interpretation": "Недостаточно данных для LBP"}

            # Вычисляем LBP на всём изображении
            h, w = gray.shape
            center = gray[1:-1, 1:-1].astype(np.int16)
            neighbors = [
                gray[0:-2,0:-2], gray[0:-2,1:-1], gray[0:-2,2:],
                gray[1:-1,2:],   gray[2:,  2:],   gray[2:,  1:-1],
                gray[2:,  0:-2], gray[1:-1,0:-2],
            ]
            lbp_map = np.zeros((h-2, w-2), dtype=np.uint8)
            for i, nb in enumerate(neighbors):
                lbp_map += ((nb.astype(np.int16) >= center) * (1 << i)).astype(np.uint8)

            # Гистограмма ТОЛЬКО по пикселям штриха (обрезаем маску под размер lbp_map)
            stroke_mask = line_mask[1:-1, 1:-1]
            if stroke_mask.sum() < 100:
                stroke_pixels = lbp_map.flatten()
            else:
                stroke_pixels = lbp_map[stroke_mask]

            hist, _ = np.histogram(stroke_pixels, bins=256, range=(0, 256))
            hist     = hist.astype(float) / (hist.sum() + 1e-6)
            energy   = float(np.sum(hist**2))
            entropy  = float(-np.sum(hist[hist > 0] * np.log2(hist[hist > 0] + 1e-6)))
            norm_e   = entropy / math.log2(256)

            if norm_e > 0.85:
                tt = "хаотичная"; interp = "Хаотичная текстура штриха (LBP) — импульсивность, тревожность."
            elif norm_e > 0.70:
                tt = "смешанная"; interp = "Смешанная текстура штриха — умеренная эмоциональная нестабильность."
            else:
                tt = "регулярная"; interp = "Регулярная текстура штриха (LBP) — уравновешенность, контроль."
            return {"energy": round(energy, 4), "entropy": round(norm_e, 3),
                    "textureType": tt, "interpretation": interp}
        except Exception as e:
            return {"energy": 0.5, "entropy": 0.5, "textureType": "неизвестно", "interpretation": f"LBP: {e}"}

    def _scores_lbp(self, lbp: dict) -> dict:
        sc = {e: 0.0 for e in ALL_EMOTIONS}
        tt = lbp.get("textureType", "смешанная")
        if tt == "хаотичная":    sc["тревога"] += 20; sc["агрессия"] += 10
        elif tt == "регулярная": sc["спокойствие"] += 20; sc["радость"] += 5
        return sc

    # ── МОДУЛЬ 8 FFT ────────────────────────────────────

    def _analyze_fft(self, gray: np.ndarray) -> dict:
        try:
            f      = np.fft.fft2(gray.astype(float))
            fshift = np.fft.fftshift(f)
            mag    = np.abs(fshift)
            H, W   = gray.shape
            cy, cx = H//2, W//2
            r_low  = min(H,W)//8
            r_high = min(H,W)//3
            Y, X   = np.ogrid[:H, :W]
            dist   = np.sqrt((X-cx)**2 + (Y-cy)**2)
            total  = mag.sum() + 1e-6
            low_e  = float(mag[dist < r_low].sum()) / total
            high_e = float(mag[dist > r_high].sum()) / total
            mid_e  = float(mag[(dist >= r_low) & (dist <= r_high)].sum()) / total
            hf     = high_e / (low_e + 1e-6)
            if hf > 2.0:
                ft = "высокочастотный"; interp = "Высокочастотный спектр (FFT) — детализированный штрих, возможна тревожность."
            elif hf < 0.5:
                ft = "низкочастотный"; interp = "Низкочастотный спектр (FFT) — крупные формы, плавность, спокойствие."
            else:
                ft = "сбалансированный"; interp = "Сбалансированный частотный спектр — нормативный характер рисунка."
            return {"lowEnergy": round(low_e,3), "midEnergy": round(mid_e,3), "highEnergy": round(high_e,3),
                    "hfRatio": round(hf,3), "freqType": ft, "interpretation": interp}
        except Exception as e:
            return {"lowEnergy":0.3,"midEnergy":0.4,"highEnergy":0.3,"hfRatio":1.0,
                    "freqType":"неизвестно","interpretation":f"FFT: {e}"}

    def _scores_fft(self, fft: dict) -> dict:
        sc = {e: 0.0 for e in ALL_EMOTIONS}
        ft = fft.get("freqType", "сбалансированный")
        if ft == "высокочастотный":  sc["тревога"] += 15; sc["агрессия"] += 5
        elif ft == "низкочастотный": sc["спокойствие"] += 15; sc["радость"] += 5
        return sc

    # ── АГРЕГАЦИЯ ────────────────────────────────────────

    def _aggregate(self, s1, s2, s3, s4, s5, s6, s7, s8) -> dict:
        w = MODULE_WEIGHTS
        return {
            e: max(0.0, min(150.0,
                s1.get(e,0)*w["module1_luscher"]  + s2.get(e,0)*w["module2_makeover"] +
                s3.get(e,0)*w["module3_lines"]    + s4.get(e,0)*w["module4_joy"]      +
                s5.get(e,0)*w["module5_objects"]  + s6.get(e,0)*w["module6_haar"]     +
                s7.get(e,0)*w["module7_lbp"]      + s8.get(e,0)*w["module8_fft"]
            )) for e in ALL_EMOTIONS
        }

    def _apply_veto(self, scores, color, comp, zone, line, joy) -> dict:
        result = dict(scores)
        for sig in joy.get("triggered", []):
            cap = sig.get("aggression_cap", 100)
            if result.get("агрессия", 0) > 50:
                excess = result["агрессия"] - 50
                reduction = excess / 50.0 * max(0, result.get("радость", 0) - cap)
                if reduction > 0:
                    result["радость"] = max(cap, result.get("радость", 0) - reduction * 0.5)
        if color.get("darkRatio", 0) > 60 and color["saturationClass"] == "серый":
            result["радость"]      = min(result.get("радость", 0), 30)
            result["спокойствие"]  = min(result.get("спокойствие", 0), 25)
        return {e: max(0.0, min(100.0, v)) for e, v in result.items()}

    def _get_age_norms(self, age: Optional[int]) -> Optional[dict]:
        if age is None: return None
        for (lo, hi), norms in AGE_NORMS.items():
            if lo <= age <= hi: return norms
        return None

    def _apply_age_correction(self, scores, age, color, line, is_empty) -> dict:
        result = dict(scores)
        norms  = self._get_age_norms(age)
        if not norms: return result
        for em in ALL_EMOTIONS:
            corr = norms.get(em, 0)
            if corr: result[em] = max(0, result[em] + corr)
        if norms.get("chaos_ok") and line.get("chaos") == "высокая":
            result["тревога"] = max(0, result["тревога"] - 15)
        if norms.get("fill_low_ok") and is_empty:
            result["грусть"] = max(0, result["грусть"] - 10)
        if norms.get("dark_ok") and color.get("darkRatio", 0) > 30:
            result["грусть"]  = max(0, result["грусть"]  - 10)
            result["тревога"] = max(0, result["тревога"] - 10)
        return {e: max(0.0, min(100.0, v)) for e, v in result.items()}

    def _parse_context(self, context: str) -> dict:
        if not context:
            return {"stress_level": 0, "positive_level": 0, "stress_keywords": [], "positive_keywords": []}
        ctx = context.lower()
        sk  = [k for k in CONTEXT_STRESS_KEYWORDS   if k in ctx]
        pk  = [k for k in CONTEXT_POSITIVE_KEYWORDS if k in ctx]
        return {"stress_level": min(3, len(sk)), "positive_level": min(2, len(pk)),
                "stress_keywords": sk, "positive_keywords": pk}

    def _apply_context_correction(self, scores: dict, ctx: dict) -> dict:
        result = dict(scores)
        sl = ctx.get("stress_level", 0)
        pl = ctx.get("positive_level", 0)
        if sl >= 1: result["тревога"] += 8;  result["грусть"] += 5
        if sl >= 2: result["тревога"] += 10; result["грусть"] += 8
        if sl >= 3: result["тревога"] += 15; result["грусть"] += 10; result["агрессия"] += 5
        if pl >= 1: result["радость"] += 5
        if pl >= 2: result["радость"] += 8; result["спокойствие"] += 5
        return {e: max(0.0, min(100.0, v)) for e, v in result.items()}

    def _to_emotions(self, scores, color, comp, zone, line) -> list:
        result = []
        for name, score in scores.items():
            v = max(0, min(100, round(score)))
            if v >= 10:
                result.append({"name": name, "intensity": v, "evidence": self._evidence(name, color, comp, zone, line)})
        result.sort(key=lambda x: -x["intensity"])
        return result[:5]

    def _evidence(self, em, color, comp, zone, line) -> str:
        zc = zone["zoneClasses"]
        ev = {
            "радость":     f"Палитра: {color['palette']}; покрытие: {color.get('colorCoverage',0)}%; нажим: {line['pressure']}",
            "грусть":      f"Яркость {color['brightnessValue']}%; нажим: {line['pressure']}; левая зона: {zc.get('лево','—')}",
            "тревога":     f"Линии: {line['character']}; хаос: {line['chaos']}; нижняя зона: {zc.get('низ','—')}",
            "агрессия":    f"Нажим: {line['pressure']}; толщина: {line['thickness']}; центр: {zc.get('центр','—')}",
            "спокойствие": f"Линии: {line['character']}; палитра: {color['palette']}; баланс: {zone['balanceInterpretation'][:40]}",
        }
        return ev.get(em, "Люшер + Маховер + линии + объекты + Haar + LBP + FFT")

    def _build_content_analysis(self, obj_data: dict, haar_data: dict) -> dict:
        detected = list(obj_data.get("detectedObjects", []))
        if haar_data.get("has_face") and "человек" not in detected:
            detected.append("нарисованное лицо")
        if haar_data.get("has_smile") and "улыбка" not in detected:
            detected.append("улыбающееся лицо")
        parts = []
        if obj_data.get("hasSun"):    parts.append("Солнце — символ безопасности и тепла")
        if obj_data.get("hasHouse"):  parts.append("Дом — потребность в защите и стабильности")
        if obj_data.get("hasHuman"):  parts.append("Человеческая фигура — социальная направленность")
        if obj_data.get("hasNature"): parts.append("Природа — связь с естественной средой")
        if obj_data.get("hasDarkElements"): parts.append("Тёмные элементы — тревога или подавленность")
        if haar_data.get("has_smile"): parts.append("Улыбающееся лицо (Haar) — позитивный образ")
        return {
            "detectedObjects": detected,
            "hasHuman":        obj_data.get("hasHuman") or haar_data.get("has_face", False),
            "hasSun":          obj_data.get("hasSun", False),
            "hasHouse":        obj_data.get("hasHouse", False),
            "hasNature":       obj_data.get("hasNature", False),
            "hasDarkElements": obj_data.get("hasDarkElements", False),
            "hasSmile":        obj_data.get("hasSmile") or haar_data.get("has_smile", False),
            "symbolism":       ". ".join(parts) if parts else "Символические объекты не обнаружены.",
        }

    def _build_portrait(self, emotions, color, comp, zone, line, age, haar) -> str:
        if not emotions:
            return "Недостаточно данных для построения психологического портрета."
        dom  = emotions[0]["name"]
        sec  = emotions[1]["name"] if len(emotions) > 1 else None
        astr = f"{age}-летнего ребёнка" if age else "ребёнка"
        intro = f"Рисунок {astr} демонстрирует преобладание «{dom}»"
        if sec: intro += f" на фоне «{sec}»"
        intro += "."
        pal = ("может свидетельствовать о внутреннем напряжении" if color["brightnessClass"] == "тёмный" else
               "указывает на позитивный эмоциональный фон"      if color["brightnessClass"] == "светлый" else
               "соответствует нормативному состоянию")
        haar_desc = ""
        if haar.get("has_face") and haar.get("has_smile"):
            haar_desc = "Наличие улыбающегося лица (Haar-анализ) подтверждает позитивный настрой."
        elif haar.get("has_face"):
            haar_desc = "Нарисованное лицо без улыбки может указывать на сдержанность эмоций."
        return " ".join(filter(None, [
            intro,
            f"Выбранная {color['palette']} палитра {pal}.",
            f"Анализ линий: {line['pressure']} нажим, {line['character']} штрих.",
            f"Зональный анализ (Маховер): {zone['balanceInterpretation']}.",
            ("Высокое заполнение листа говорит об энергетике." if comp["fillClass"] == "высокая" else
             "Низкое заполнение листа может указывать на замкнутость." if comp["fillClass"] == "низкая" else
             "Заполнение листа соответствует норме."),
            haar_desc,
        ]))

    def _recommendations(self, emotions, comp, zone, line, age, ctx, haar) -> list:
        recs  = []
        names = [e["name"] for e in emotions]
        zc    = zone["zoneClasses"]
        if ctx.get("stress_level", 0) >= 2:
            recs.append(f"Выявлены стрессовые факторы ({', '.join(ctx.get('stress_keywords',[])[:2])}): необходима поддерживающая беседа")
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
        if haar.get("has_face") and not haar.get("has_smile"):
            recs.append("Ребёнок рисует лица без улыбок — обратите внимание на эмоциональный климат")
        if names and names[0] == "радость":
            recs.append("Эмоциональный фон благоприятный — поддерживать текущие условия воспитания")
        if not recs:
            recs.append("Плановое наблюдение в стандартном режиме")
            recs.append("Повторный анализ через 2–3 недели для отслеживания динамики")
        recs.append("Результаты носят вспомогательный характер и требуют очной консультации специалиста")
        return recs[:4]

    def _risk_factors(self, emotions, color, comp, zone, line, ctx, haar) -> list:
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
        if ctx.get("stress_level", 0) >= 2:
            risks.append(f"Стресс-контекст: {', '.join(ctx.get('stress_keywords',[])[:3])}")
        if haar.get("has_face") and not haar.get("has_smile") and em.get("грусть", 0) > 30:
            risks.append("Haar: нарисованное лицо без улыбки + грусть — эмоциональная подавленность")
        return risks

    def _overall_state(self, emotions, risks, age) -> str:
        key = next((k for k in AGE_STATE_THRESHOLDS if k[0] <= (age or 8) <= k[1]), (6, 8))
        thr = AGE_STATE_THRESHOLDS.get(key, {"консультация": 3, "внимание": 1})
        if len(risks) >= thr["консультация"]: return "требует_консультации"
        if len(risks) >= thr["внимание"]:     return "требует_внимания"
        for e in emotions:
            if e["name"] in {"агрессия","тревога","грусть"} and e["intensity"] > 60:
                return "требует_внимания"
        return "норма"

    def _confidence(self, color, comp, zone, line, haar, fft) -> int:
        base = 65
        base += min(color.get("nVividColors", 0) * 3, 12)
        base += min(sum(1 for c in zone["zoneClasses"].values() if c != "низкая") * 2, 8)
        if line["pressure"] != "средний":        base += 4
        if line["character"] != "плавные":       base += 3
        if haar.get("has_face"):                  base += 5
        if fft.get("freqType") != "неизвестно":  base += 3
        if comp["fillRatio"] < 5:                 base -= 15
        return max(50, min(96, base))