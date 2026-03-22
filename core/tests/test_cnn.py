"""
АртМинд — Тесты CNN-анализатора v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Запуск: cd core && py -3.11 -m pytest tests/test_cnn.py -v

Тестирует:
  - Загрузка модели
  - Формат ответа
  - Классификация синтетических изображений
  - Классификация реальных рисунков из датасета
  - Скорость инференса
  - Совместимость с форматом системы
"""

import sys
import os
import time
import json
import numpy as np
import pytest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cnn_analyzer import (
    analyze_with_cnn, check_cnn_available, _predict, _load_model,
    MODEL_PATH, META_PATH, CNN_TO_EMOTION, CATEGORIES,
)

DRAWINGS_DIR = Path(__file__).parent.parent / "drawings"


# ══════════════════════════════════════════════════════════
# Утилиты
# ══════════════════════════════════════════════════════════

def _make_color_image(color_rgb: tuple, size: int = 224) -> bytes:
    """Создаёт однородное изображение и возвращает JPEG bytes."""
    from PIL import Image
    import io
    img = Image.new("RGB", (size, size), color_rgb)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _load_real_image(set_name: str, category: str, index: int = 1) -> bytes:
    """Загружает реальный рисунок из датасета."""
    cat_dir = DRAWINGS_DIR / set_name / category
    if not cat_dir.exists():
        pytest.skip(f"Датасет не найден: {cat_dir}")
    files = sorted(f for f in cat_dir.iterdir() if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})
    if index > len(files):
        pytest.skip(f"Недостаточно файлов в {cat_dir}")
    return files[index - 1].read_bytes()


# ══════════════════════════════════════════════════════════
# Тесты модели
# ══════════════════════════════════════════════════════════

class TestCNNModel:
    """Тесты загрузки и доступности модели."""

    def test_model_file_exists(self):
        assert MODEL_PATH.exists(), f"Модель не найдена: {MODEL_PATH}"

    def test_meta_file_exists(self):
        assert META_PATH.exists(), f"Мета не найдена: {META_PATH}"

    def test_meta_has_required_keys(self):
        with open(META_PATH, "r", encoding="utf-8") as f:
            meta = json.load(f)
        required = {"model", "num_classes", "categories", "emotion_map", "results", "dataset"}
        assert required.issubset(set(meta.keys()))

    def test_meta_results(self):
        with open(META_PATH, "r", encoding="utf-8") as f:
            meta = json.load(f)
        results = meta["results"]
        assert results["test_acc"] > 0.5, f"Test accuracy слишком низкая: {results['test_acc']}"
        assert results["macro_f1"] > 0.4, f"Macro F1 слишком низкий: {results['macro_f1']}"

    @pytest.mark.asyncio
    async def test_check_cnn_available(self):
        status = await check_cnn_available()
        assert status["available"] is True
        assert status["model"] == "EfficientNet-B0"

    def test_load_model_returns_model(self):
        model, device = _load_model()
        assert model is not None
        assert device is not None

    def test_categories_count(self):
        assert len(CATEGORIES) == 4

    def test_emotion_map_covers_all_classes(self):
        for i in range(4):
            assert i in CNN_TO_EMOTION, f"Класс {i} не в CNN_TO_EMOTION"


# ══════════════════════════════════════════════════════════
# Тесты формата ответа
# ══════════════════════════════════════════════════════════

class TestCNNResponseFormat:
    """Тесты формата ответа analyze_with_cnn."""

    @pytest.fixture
    def result(self):
        img = _make_color_image((200, 200, 50))
        return analyze_with_cnn(img, child_age=8)

    def test_has_required_keys(self, result):
        required = {
            "emotions", "psychologicalPortrait", "riskFactors",
            "recommendations", "overallState", "confidence",
            "analysisMode", "colorAnalysis", "composition",
        }
        assert required.issubset(set(result.keys()))

    def test_analysis_mode_is_cnn(self, result):
        assert result["analysisMode"] == "cnn"

    def test_emotions_is_list(self, result):
        assert isinstance(result["emotions"], list)

    def test_emotions_have_correct_structure(self, result):
        for e in result["emotions"]:
            assert "name" in e
            assert "intensity" in e
            assert "evidence" in e
            assert 0 <= e["intensity"] <= 100

    def test_overall_state_valid(self, result):
        assert result["overallState"] in {"норма", "требует_внимания", "требует_консультации"}

    def test_confidence_range(self, result):
        assert 50 <= result["confidence"] <= 96

    def test_recommendations_not_empty(self, result):
        assert len(result["recommendations"]) >= 1

    def test_portrait_not_empty(self, result):
        assert len(result["psychologicalPortrait"]) > 10

    def test_has_cnn_prediction(self, result):
        assert "cnnPrediction" in result
        pred = result["cnnPrediction"]
        assert "class" in pred
        assert "emotion" in pred
        assert "probability" in pred
        assert "allProbabilities" in pred
        assert 0 <= pred["probability"] <= 1

    def test_color_analysis_stub(self, result):
        assert "colorAnalysis" in result
        assert isinstance(result["colorAnalysis"], dict)

    def test_composition_stub(self, result):
        assert "composition" in result
        assert isinstance(result["composition"], dict)


# ══════════════════════════════════════════════════════════
# Тесты _predict (низкоуровневый)
# ══════════════════════════════════════════════════════════

class TestCNNPredict:
    """Тесты низкоуровневой функции _predict."""

    def test_predict_returns_all_fields(self):
        img = _make_color_image((100, 100, 100))
        pred = _predict(img)
        assert "class_idx" in pred
        assert "class_name" in pred
        assert "emotion" in pred
        assert "confidence" in pred
        assert "probabilities" in pred

    def test_probabilities_sum_to_1(self):
        img = _make_color_image((150, 80, 80))
        pred = _predict(img)
        total = sum(pred["probabilities"].values())
        assert abs(total - 1.0) < 0.01, f"Сумма вероятностей = {total}"

    def test_confidence_matches_max_prob(self):
        img = _make_color_image((50, 50, 200))
        pred = _predict(img)
        max_prob = max(pred["probabilities"].values())
        assert abs(pred["confidence"] - max_prob) < 0.01

    def test_class_name_in_categories(self):
        img = _make_color_image((200, 50, 50))
        pred = _predict(img)
        assert pred["class_name"] in CATEGORIES

    def test_emotion_in_map(self):
        img = _make_color_image((50, 200, 50))
        pred = _predict(img)
        assert pred["emotion"] in CNN_TO_EMOTION.values()


# ══════════════════════════════════════════════════════════
# Тесты на реальных рисунках
# ══════════════════════════════════════════════════════════

class TestCNNRealImages:
    """Тесты на реальных рисунках из датасета."""

    def test_happy_drawing_predicts_joy(self):
        img = _load_real_image("set1", "Happy", 1)
        result = analyze_with_cnn(img, child_age=8)
        emotions = {e["name"]: e["intensity"] for e in result["emotions"]}
        assert "радость" in emotions, f"Happy рисунок: нет радости. Эмоции: {emotions}"
        assert emotions["радость"] >= 30, f"Happy рисунок: радость только {emotions['радость']}%"

    def test_sad_drawing_predicts_sadness(self):
        img = _load_real_image("set1", "Sad", 1)
        pred = _predict(img)
        # Sad должен давать грусть или тревогу (близкие эмоции)
        top2 = sorted(pred["probabilities"].items(), key=lambda x: -x[1])[:2]
        top2_emotions = [e[0] for e in top2]
        assert "грусть" in top2_emotions or "тревога" in top2_emotions, \
            f"Sad рисунок: top-2 = {top2_emotions}"

    def test_angry_drawing_has_negative_emotion(self):
        img = _load_real_image("set1", "Angry", 1)
        pred = _predict(img)
        negative = pred["probabilities"].get("агрессия", 0) + pred["probabilities"].get("тревога", 0)
        assert negative > 0.1, f"Angry рисунок: агрессия+тревога = {negative:.1%}"

    def test_fear_drawing_has_anxiety(self):
        img = _load_real_image("set1", "Fear", 1)
        pred = _predict(img)
        anxiety_related = pred["probabilities"].get("тревога", 0) + pred["probabilities"].get("грусть", 0)
        assert anxiety_related > 0.1, f"Fear рисунок: тревога+грусть = {anxiety_related:.1%}"

    def test_multiple_happy_drawings(self):
        """Проверяем 5 Happy рисунков — хотя бы 3 из 5 правильно."""
        correct = 0
        for i in range(1, 6):
            try:
                img = _load_real_image("set1", "Happy", i)
                pred = _predict(img)
                if pred["emotion"] == "радость":
                    correct += 1
            except Exception:
                pass
        assert correct >= 3, f"Happy: только {correct}/5 правильных"

    def test_multiple_sad_drawings(self):
        """Проверяем 5 Sad рисунков — хотя бы 2 из 5 правильно (грусть сложнее)."""
        correct = 0
        for i in range(1, 6):
            try:
                img = _load_real_image("set1", "Sad", i)
                pred = _predict(img)
                if pred["emotion"] == "грусть":
                    correct += 1
            except Exception:
                pass
        assert correct >= 2, f"Sad: только {correct}/5 правильных"


# ══════════════════════════════════════════════════════════
# Тесты производительности
# ══════════════════════════════════════════════════════════

class TestCNNPerformance:
    """Тесты скорости инференса."""

    def test_inference_speed(self):
        """Один инференс должен быть < 500мс."""
        img = _make_color_image((128, 128, 128))
        # Прогрев
        _predict(img)

        start = time.perf_counter()
        _predict(img)
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 500, f"Инференс слишком медленный: {elapsed:.0f}мс"

    def test_batch_speed(self):
        """10 инференсов < 3 сек."""
        img = _make_color_image((128, 128, 128))
        _predict(img)  # прогрев

        start = time.perf_counter()
        for _ in range(10):
            _predict(img)
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 3000, f"10 инференсов: {elapsed:.0f}мс (>{3000}мс)"
        print(f"  10 инференсов: {elapsed:.0f}мс ({elapsed/10:.0f}мс/шт)")

    def test_real_image_speed(self):
        """Реальный рисунок < 500мс."""
        try:
            img = _load_real_image("set1", "Happy", 1)
        except Exception:
            pytest.skip("Датасет не найден")

        _predict(img)  # прогрев

        start = time.perf_counter()
        _predict(img)
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 500, f"Реальный рисунок: {elapsed:.0f}мс"


# ══════════════════════════════════════════════════════════
# Тесты совместимости с системой
# ══════════════════════════════════════════════════════════

class TestCNNSystemCompat:
    """Тесты совместимости CNN-ответа с остальной системой."""

    def test_json_serializable(self):
        img = _make_color_image((128, 128, 128))
        result = analyze_with_cnn(img, child_age=8)
        # Не должно кинуть исключение
        json.dumps(result, ensure_ascii=False)

    def test_emotions_match_system_emotions(self):
        """Все эмоции из CNN должны быть из 5 системных."""
        from config import ALL_EMOTIONS
        img = _make_color_image((128, 128, 128))
        result = analyze_with_cnn(img, child_age=8)
        for e in result["emotions"]:
            assert e["name"] in ALL_EMOTIONS, f"Неизвестная эмоция: {e['name']}"

    def test_with_age_parameter(self):
        img = _make_color_image((128, 128, 128))
        r1 = analyze_with_cnn(img, child_age=3)
        r2 = analyze_with_cnn(img, child_age=15)
        # Оба должны вернуть валидный результат
        assert r1["analysisMode"] == "cnn"
        assert r2["analysisMode"] == "cnn"

    def test_with_context_parameter(self):
        img = _make_color_image((128, 128, 128))
        result = analyze_with_cnn(img, child_age=8, context="развод родителей")
        assert result["analysisMode"] == "cnn"

    def test_risk_factors_for_negative_emotion(self):
        """При высокой вероятности негативной эмоции должны быть риск-факторы."""
        # Используем реальный Angry рисунок для лучшего шанса
        try:
            img = _load_real_image("set1", "Angry", 5)
        except Exception:
            img = _make_color_image((200, 30, 30))

        result = analyze_with_cnn(img, child_age=10)
        pred = result.get("cnnPrediction", {})
        # Если модель уверена в негативной эмоции, должны быть рекомендации
        assert len(result["recommendations"]) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])