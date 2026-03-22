"""
АртМинд — FastAPI Backend v8.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Запуск: py -3.11 -m uvicorn server:app --reload --port 8000

Режимы анализа:
  /analyze?mode=auto     — лучший доступный
  /analyze?mode=opencv   — только OpenCV (8 модулей)
  /analyze?mode=groq     — Groq Vision (LLaMA-4)
  /analyze?mode=hybrid   — Groq 65% + OpenCV 35%
  /analyze?mode=cnn      — CNN EfficientNet-B0

v8.0: + CNN EfficientNet-B0 режим
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from typing import Optional
from sqlalchemy.orm import Session
import traceback
import asyncio

from analyzer       import DrawingAnalyzer
from groq_analyzer  import analyze_with_groq, check_groq_available, _hybrid_merge
from cnn_analyzer   import analyze_with_cnn, check_cnn_available
from database       import init_db, get_db, save_analysis, get_history, get_analysis_by_id, delete_analysis, get_history_count
from logger         import log_analysis_start, log_analysis_result, log_db_save, log_timing, logger

# ── Инициализация ──────────────────────────────────────────

opencv_analyzer = DrawingAnalyzer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 АртМинд API v8.0 — запуск")
    init_db()
    logger.info("💾 База данных инициализирована")
    yield
    logger.info("👋 АртМинд API — остановка")


app = FastAPI(
    title="АртМинд API",
    description="Психоэмоциональный анализ детских рисунков",
    version="8.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Валидация ──────────────────────────────────────────────
def _validate_image(file: UploadFile):
    if not file.content_type or not file.content_type.startswith("image/"):
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


async def _run_cnn(image_bytes: bytes, age: Optional[int], ctx: str) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, analyze_with_cnn, image_bytes, age, ctx
    )


# ═══════════════════════════════════════
# СЛУЖЕБНЫЕ ЭНДПОИНТЫ
# ═══════════════════════════════════════

@app.get("/")
def root():
    return {
        "status":  "ok",
        "service": "АртМинд API v8.0",
        "modes":   ["auto", "opencv", "groq", "hybrid", "cnn"],
    }


@app.get("/health")
async def health(db: Session = Depends(get_db)):
    groq_s = await check_groq_available()
    cnn_s  = await check_cnn_available()

    db_connected = False
    db_count = 0
    try:
        db_count = get_history_count(db)
        db_connected = True
    except Exception as e:
        logger.error(f"Ошибка подключения к БД: {e}")

    return {
        "status":        "healthy" if db_connected else "degraded",
        "opencv_ready":  True,
        "groq_ready":    groq_s["available"],
        "cnn_ready":     cnn_s["available"],
        "groq":          groq_s,
        "cnn":           cnn_s,
        "db_connected":  db_connected,
        "db_analyses":   db_count,
    }


@app.get("/groq/status")
async def groq_status():
    return await check_groq_available()


@app.get("/cnn/status")
async def cnn_status():
    return await check_cnn_available()


# ═══════════════════════════════════════
# ГИБРИДНЫЙ ЗАПУСК (Groq + OpenCV)
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
    if mode == "cnn":
        try:
            with log_timing("CNN анализ"):
                result = await _run_cnn(image_bytes, age, ctx)
            result["analysisMode"] = "cnn"
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))

    elif mode == "hybrid":
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
        # auto: CNN > Groq hybrid > OpenCV
        cnn_s = await check_cnn_available()
        if cnn_s["available"]:
            try:
                with log_timing("CNN анализ (auto)"):
                    result = await _run_cnn(image_bytes, age, ctx)
                result["analysisMode"] = "cnn"
            except Exception:
                groq_s = await check_groq_available()
                if groq_s["available"]:
                    result = await _do_groq_hybrid(image_bytes, age, ctx)
                else:
                    result = opencv_analyzer.analyze(image_bytes, child_age=age, context=ctx)
                    result["analysisMode"] = "opencv"
        else:
            groq_s = await check_groq_available()
            if groq_s["available"]:
                result = await _do_groq_hybrid(image_bytes, age, ctx)
            else:
                result = opencv_analyzer.analyze(image_bytes, child_age=age, context=ctx)
                result["analysisMode"] = "opencv"
                result["fallbackReason"] = "CNN и Groq недоступны"

    # ── Логирование результата ──
    log_analysis_result(
        result.get("analysisMode", mode),
        result.get("overallState", "—"),
        result.get("confidence", 0),
        result.get("emotions", []),
    )

    # ── Сохранение в БД ──
    should_save = save != "false"
    if should_save:
        try:
            record = save_analysis(
                db=db, child_age=age, context=ctx,
                image_name=file.filename or "upload.jpg",
                image_data=image_bytes,
                analysis_mode=result.get("analysisMode", mode),
                result=result,
            )
            result["dbId"] = record.id
            log_db_save(record.id)
        except Exception as e:
            logger.error(f"Ошибка сохранения в БД: {e}")

    return JSONResponse(content=result)


# ═══════════════════════════════════════
# ОТДЕЛЬНЫЕ ЭНДПОИНТЫ (обратная совместимость)
# ═══════════════════════════════════════

@app.post("/analyze/opencv")
async def analyze_opencv(
    file: UploadFile = File(...), age: Optional[int] = Form(None),
    context: Optional[str] = Form(""), db: Session = Depends(get_db),
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
    file: UploadFile = File(...), age: Optional[int] = Form(None),
    context: Optional[str] = Form(""), db: Session = Depends(get_db),
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
    file: UploadFile = File(...), age: Optional[int] = Form(None),
    context: Optional[str] = Form(""), db: Session = Depends(get_db),
):
    _validate_image(file)
    image_bytes = await _read_image(file)
    result = await _do_groq_hybrid(image_bytes, age, context or "")
    record = save_analysis(db, age, context or "", file.filename or "", image_bytes, "hybrid", result)
    result["dbId"] = record.id
    return JSONResponse(content=result)


@app.post("/analyze/cnn")
async def analyze_cnn_endpoint(
    file: UploadFile = File(...), age: Optional[int] = Form(None),
    context: Optional[str] = Form(""), db: Session = Depends(get_db),
):
    _validate_image(file)
    image_bytes = await _read_image(file)
    try:
        with log_timing("CNN анализ"):
            result = await _run_cnn(image_bytes, age, context or "")
        result["analysisMode"] = "cnn"
        record = save_analysis(db, age, context or "", file.filename or "", image_bytes, "cnn", result)
        result["dbId"] = record.id
        return JSONResponse(content=result)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════
# ИСТОРИЯ АНАЛИЗОВ
# ═══════════════════════════════════════

@app.get("/history")
def history_list(
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    records = get_history(db, limit=limit, offset=offset)
    total = get_history_count(db)
    return {"total": total, "limit": limit, "offset": offset,
            "items": [r.to_summary() for r in records]}


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
    media_type = "image/png" if record.image_data[:4] == b"\x89PNG" else "image/jpeg"
    return Response(content=record.image_data, media_type=media_type)


@app.delete("/history/{analysis_id}")
def history_delete(analysis_id: int, db: Session = Depends(get_db)):
    deleted = delete_analysis(db, analysis_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Анализ не найден")
    return {"status": "deleted", "id": analysis_id}