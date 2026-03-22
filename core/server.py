"""
АртМинд — FastAPI Backend v7.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Запуск: py -3.11 -m uvicorn server:app --reload --port 8000

Режимы анализа:
  /analyze              — авто (лучший доступный)
  /analyze/opencv       — только OpenCV
  /analyze/groq         — Groq Vision (LLaMA-4)
  /analyze/hybrid       — Groq + OpenCV (65/35)

Служебные:
  /health               — статус системы
  /groq/status          — статус Groq API

История (PostgreSQL):
  GET  /history              — список анализов
  GET  /history/{id}         — конкретный анализ
  GET  /history/{id}/image   — изображение рисунка
  DELETE /history/{id}       — удалить анализ
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from typing import Optional
from sqlalchemy.orm import Session
import traceback
import asyncio

from analyzer      import DrawingAnalyzer
from groq_analyzer import analyze_with_groq, check_groq_available, _hybrid_merge
from database      import init_db, get_db, save_analysis, get_history, get_analysis_by_id, delete_analysis, get_history_count
from logger        import log_analysis_start, log_analysis_result, log_db_save, log_timing, logger

# ── Инициализация ──────────────────────────────────────────
app = FastAPI(
    title="АртМинд API",
    description="Психоэмоциональный анализ детских рисунков",
    version="7.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

opencv_analyzer = DrawingAnalyzer()


@app.on_event("startup")
def on_startup():
    logger.info("🚀 АртМинд API v7.0 — запуск")
    init_db()
    logger.info("💾 База данных инициализирована")


# ── Валидация ──────────────────────────────────────────────
def _validate_image(file: UploadFile):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Файл должен быть изображением")


async def _read_image(file: UploadFile) -> bytes:
    data = await file.read()
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Файл слишком большой (макс. 15 МБ)")
    return data


async def _run_opencv(image_bytes: bytes, age: Optional[int], ctx: str) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, opencv_analyzer.analyze, image_bytes, age, ctx
    )


# ═══════════════════════════════════════
# СЛУЖЕБНЫЕ ЭНДПОИНТЫ
# ═══════════════════════════════════════

@app.get("/")
def root():
    return {
        "status":  "ok",
        "service": "АртМинд API v7.0",
        "modes":   ["auto", "opencv", "groq", "hybrid"],
    }


@app.get("/health")
async def health(db: Session = Depends(get_db)):
    groq_s = await check_groq_available()
    db_count = get_history_count(db)
    return {
        "status":        "healthy",
        "opencv_ready":  True,
        "groq_ready":    groq_s["available"],
        "groq":          groq_s,
        "db_connected":  True,
        "db_analyses":   db_count,
    }


@app.get("/groq/status")
async def groq_status():
    return await check_groq_available()


# ═══════════════════════════════════════
# ГИБРИДНЫЙ ЗАПУСК
# ═══════════════════════════════════════

async def _do_groq_hybrid(image_bytes: bytes, age: Optional[int], ctx: str):
    try:
        with log_timing("Groq + OpenCV параллельный анализ"):
            opencv_result, groq_result = await asyncio.gather(
                _run_opencv(image_bytes, age, ctx),
                analyze_with_groq(image_bytes, child_age=age, context=ctx),
            )
        result = _hybrid_merge(groq_result, opencv_result)
        result["analysisMode"] = "hybrid"
        return result
    except Exception as e:
        traceback.print_exc()
        logger.warning(f"Groq fallback: {e}")
        with log_timing("OpenCV fallback"):
            result = opencv_analyzer.analyze(image_bytes, child_age=age, context=ctx)
        result["analysisMode"]   = "opencv_fallback"
        result["fallbackReason"] = f"Groq недоступен: {e}"
        return result


# ═══════════════════════════════════════
# АНАЛИЗ (единый эндпоинт)
# ═══════════════════════════════════════

@app.post("/analyze")
async def analyze_auto(
    file:    UploadFile    = File(...),
    age:     Optional[int] = Form(None),
    context: Optional[str] = Form(""),
    mode:    Optional[str] = Form("auto"),
    save:    Optional[str] = Form("true"),
    db:      Session       = Depends(get_db),
):
    _validate_image(file)
    image_bytes = await _read_image(file)
    ctx = context or ""

    # ── Валидация возраста ──
    if age is not None and (age < 2 or age > 17):
        raise HTTPException(status_code=400, detail="Возраст должен быть от 2 до 17 лет")

    log_analysis_start(mode, age, bool(ctx))

    # ── Выбор режима ──
    if mode == "hybrid":
        result = await _do_groq_hybrid(image_bytes, age, ctx)

    elif mode == "opencv":
        try:
            with log_timing("OpenCV анализ"):
                result = opencv_analyzer.analyze(image_bytes, child_age=age, context=ctx)
            result["analysisMode"] = "opencv"
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))

    elif mode == "groq":
        try:
            with log_timing("Groq анализ"):
                result = await analyze_with_groq(image_bytes, child_age=age, context=ctx)
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))

    else:
        # auto: Groq hybrid > OpenCV
        groq_s = await check_groq_available()
        if groq_s["available"]:
            result = await _do_groq_hybrid(image_bytes, age, ctx)
        else:
            try:
                with log_timing("OpenCV анализ (auto fallback)"):
                    result = opencv_analyzer.analyze(image_bytes, child_age=age, context=ctx)
                result["analysisMode"]   = "opencv"
                result["fallbackReason"] = "Groq недоступен"
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

    # ── Логирование результата ──
    log_analysis_result(
        result.get("analysisMode", mode),
        result.get("overallState", "—"),
        result.get("confidence", 0),
        result.get("emotions", []),
    )

    # ── Сохранение в БД (пропуск при save=false, например для сравнения) ──
    should_save = save != "false"
    if should_save:
        try:
            record = save_analysis(
                db=db,
                child_age=age,
                context=ctx,
                image_name=file.filename or "upload.jpg",
                image_data=image_bytes,
                analysis_mode=result.get("analysisMode", mode),
                result=result,
            )
            result["dbId"] = record.id
            log_db_save(record.id)
        except Exception as e:
            logger.error(f"Ошибка сохранения в БД: {e}")
        # Не ломаем ответ — анализ уже готов

    return JSONResponse(content=result)


# ═══════════════════════════════════════
# ОТДЕЛЬНЫЕ ЭНДПОИНТЫ (обратная совместимость)
# ═══════════════════════════════════════

@app.post("/analyze/opencv")
async def analyze_opencv(
    file:    UploadFile    = File(...),
    age:     Optional[int] = Form(None),
    context: Optional[str] = Form(""),
    db:      Session       = Depends(get_db),
):
    _validate_image(file)
    image_bytes = await _read_image(file)
    try:
        with log_timing("OpenCV анализ"):
            result = opencv_analyzer.analyze(image_bytes, child_age=age, context=context or "")
        result["analysisMode"] = "opencv"
        record = save_analysis(db, age, context or "", file.filename or "", image_bytes, "opencv", result)
        result["dbId"] = record.id
        return JSONResponse(content=result)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/groq")
async def analyze_groq_endpoint(
    file:    UploadFile    = File(...),
    age:     Optional[int] = Form(None),
    context: Optional[str] = Form(""),
    db:      Session       = Depends(get_db),
):
    _validate_image(file)
    image_bytes = await _read_image(file)
    try:
        with log_timing("Groq анализ"):
            result = await analyze_with_groq(image_bytes, child_age=age, context=context or "")
        record = save_analysis(db, age, context or "", file.filename or "", image_bytes, "groq", result)
        result["dbId"] = record.id
        return JSONResponse(content=result)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/hybrid")
async def analyze_groq_hybrid(
    file:    UploadFile    = File(...),
    age:     Optional[int] = Form(None),
    context: Optional[str] = Form(""),
    db:      Session       = Depends(get_db),
):
    _validate_image(file)
    image_bytes = await _read_image(file)
    result = await _do_groq_hybrid(image_bytes, age, context or "")
    record = save_analysis(db, age, context or "", file.filename or "", image_bytes, "hybrid", result)
    result["dbId"] = record.id
    return JSONResponse(content=result)


# ═══════════════════════════════════════
# ИСТОРИЯ АНАЛИЗОВ
# ═══════════════════════════════════════

@app.get("/history")
def history_list(
    limit:  int     = Query(50, ge=1, le=200),
    offset: int     = Query(0, ge=0),
    db:     Session = Depends(get_db),
):
    records = get_history(db, limit=limit, offset=offset)
    total   = get_history_count(db)
    return {
        "total":   total,
        "limit":   limit,
        "offset":  offset,
        "items":   [r.to_summary() for r in records],
    }


@app.get("/history/{analysis_id}")
def history_detail(analysis_id: int, db: Session = Depends(get_db)):
    record = get_analysis_by_id(db, analysis_id)
    if not record:
        raise HTTPException(status_code=404, detail="Анализ не найден")
    return record.to_dict()


@app.get("/history/{analysis_id}/image")
def history_image(analysis_id: int, db: Session = Depends(get_db)):
    record = get_analysis_by_id(db, analysis_id)
    if not record or not record.image_data:
        raise HTTPException(status_code=404, detail="Изображение не найдено")
    # Определяем тип по первым байтам
    media_type = "image/png" if record.image_data[:4] == b"\x89PNG" else "image/jpeg"
    return Response(content=record.image_data, media_type=media_type)


@app.delete("/history/{analysis_id}")
def history_delete(analysis_id: int, db: Session = Depends(get_db)):
    deleted = delete_analysis(db, analysis_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Анализ не найден")
    return {"status": "deleted", "id": analysis_id}