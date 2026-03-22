"""
АртМинд — Structured Logging v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Логирование каждого этапа анализа с временами выполнения.
Используется loguru для структурированного вывода.
"""

import sys
import time
from contextlib import contextmanager
from loguru import logger

# ── Конфигурация логгера ───────────────────────────────────
# Убираем дефолтный handler и добавляем свой
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> | {message}",
    level="INFO",
    colorize=True,
)
logger.add(
    "logs/artmind.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} | {message}",
    level="DEBUG",
    rotation="10 MB",
    retention="30 days",
    encoding="utf-8",
)


@contextmanager
def log_timing(operation: str):
    """
    Контекстный менеджер для замера времени операции.

    Использование:
        with log_timing("OpenCV анализ"):
            result = analyzer.analyze(...)
    """
    start = time.perf_counter()
    logger.info(f"⏳ {operation} — старт")
    try:
        yield
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        logger.error(f"❌ {operation} — ошибка за {elapsed:.0f}мс: {e}")
        raise
    else:
        elapsed = (time.perf_counter() - start) * 1000
        logger.info(f"✅ {operation} — завершён за {elapsed:.0f}мс")


def log_analysis_start(mode: str, age: int | None, has_context: bool):
    """Логирует начало анализа."""
    logger.info(
        f"🎨 Новый анализ | режим={mode} | возраст={age or '—'} | контекст={'да' if has_context else 'нет'}"
    )


def log_analysis_result(mode: str, state: str, confidence: float, emotions: list):
    """Логирует результат анализа."""
    top = ", ".join(f"{e['name']}={e['intensity']}%" for e in emotions[:3])
    logger.info(
        f"📊 Результат | режим={mode} | состояние={state} | уверенность={confidence}% | топ: {top}"
    )


def log_db_save(analysis_id: int):
    """Логирует сохранение в БД."""
    logger.info(f"💾 Сохранено в БД | id={analysis_id}")