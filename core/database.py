"""
АртМинд — База данных (PostgreSQL + SQLAlchemy) v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Хранение истории анализов в PostgreSQL.

Подключение через DATABASE_URL в core/.env:
  DATABASE_URL=postgresql://user:password@localhost:5432/artmind
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, LargeBinary
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# ── Подключение ────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/artmind")

engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


# ══════════════════════════════════════════════════════════
# МОДЕЛИ
# ══════════════════════════════════════════════════════════

class AnalysisRecord(Base):
    __tablename__ = "analyses"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    created_at    = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Входные данные
    child_age     = Column(Integer, nullable=True)
    context       = Column(Text, default="")
    image_name    = Column(String(255), default="")
    image_data    = Column(LargeBinary, nullable=True)  # сам рисунок (JPEG/PNG bytes)

    # Результат анализа
    analysis_mode = Column(String(50), default="opencv")
    overall_state = Column(String(50), default="норма")
    confidence    = Column(Float, default=0.0)
    result_json   = Column(Text, default="{}")  # полный JSON-результат

    def to_dict(self) -> dict:
        """Конвертирует запись в словарь для API-ответа."""
        return {
            "id":           self.id,
            "createdAt":    self.created_at.isoformat() if self.created_at else None,
            "childAge":     self.child_age,
            "context":      self.context,
            "imageName":    self.image_name,
            "analysisMode": self.analysis_mode,
            "overallState": self.overall_state,
            "confidence":   self.confidence,
            "result":       json.loads(self.result_json) if self.result_json else {},
        }

    def to_summary(self) -> dict:
        """Краткая информация для списка истории (без полного JSON и изображения)."""
        result = json.loads(self.result_json) if self.result_json else {}
        emotions = result.get("emotions", [])
        return {
            "id":           self.id,
            "createdAt":    self.created_at.isoformat() if self.created_at else None,
            "childAge":     self.child_age,
            "context":      self.context[:100] if self.context else "",
            "imageName":    self.image_name,
            "analysisMode": self.analysis_mode,
            "overallState": self.overall_state,
            "confidence":   self.confidence,
            "topEmotions":  [{"name": e["name"], "intensity": e["intensity"]} for e in emotions[:3]],
        }


# ══════════════════════════════════════════════════════════
# ИНИЦИАЛИЗАЦИЯ ТАБЛИЦ
# ══════════════════════════════════════════════════════════

def init_db():
    """Создаёт таблицы если их нет."""
    Base.metadata.create_all(bind=engine)


# ══════════════════════════════════════════════════════════
# CRUD-ОПЕРАЦИИ
# ══════════════════════════════════════════════════════════

def get_db() -> Session:
    """Генератор сессии для FastAPI Depends."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_analysis(
    db: Session,
    child_age: Optional[int],
    context: str,
    image_name: str,
    image_data: Optional[bytes],
    analysis_mode: str,
    result: dict,
) -> AnalysisRecord:
    """Сохраняет результат анализа в БД."""
    record = AnalysisRecord(
        child_age     = child_age,
        context       = context or "",
        image_name    = image_name or "upload.jpg",
        image_data    = image_data,
        analysis_mode = analysis_mode,
        overall_state = result.get("overallState", "норма"),
        confidence    = result.get("confidence", 0),
        result_json   = json.dumps(result, ensure_ascii=False),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_history(db: Session, limit: int = 50, offset: int = 0) -> list[AnalysisRecord]:
    """Возвращает историю анализов (новые первыми)."""
    return (
        db.query(AnalysisRecord)
        .order_by(AnalysisRecord.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_analysis_by_id(db: Session, analysis_id: int) -> Optional[AnalysisRecord]:
    """Возвращает конкретный анализ по ID."""
    return db.query(AnalysisRecord).filter(AnalysisRecord.id == analysis_id).first()


def delete_analysis(db: Session, analysis_id: int) -> bool:
    """Удаляет анализ по ID. Возвращает True если удалено."""
    record = get_analysis_by_id(db, analysis_id)
    if record:
        db.delete(record)
        db.commit()
        return True
    return False


def get_history_count(db: Session) -> int:
    """Возвращает общее количество анализов."""
    return db.query(AnalysisRecord).count()