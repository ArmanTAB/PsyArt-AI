"""
АртМинд — FastAPI Backend v6.1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Запуск: py -3.11 -m uvicorn server:app --reload --port 8000

Режимы анализа:
  /analyze              — авто (лучший доступный)
  /analyze/opencv       — только OpenCV
  /analyze/groq         — Groq Vision (LLaMA-4)
  /analyze/hybrid       — Groq + OpenCV (65/35)
  /groq/status          — статус Groq API
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional
import traceback
import asyncio

from analyzer      import DrawingAnalyzer
from groq_analyzer import analyze_with_groq, check_groq_available, _hybrid_merge

app = FastAPI(
    title="АртМинд API",
    description="Психоэмоциональный анализ детских рисунков",
    version="6.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

opencv_analyzer = DrawingAnalyzer()


def _validate_image(file: UploadFile):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Файл должен быть изображением")


async def _read_image(file: UploadFile) -> bytes:
    data = await file.read()
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Файл слишком большой (макс. 15 МБ)")
    return data


# ── Вспомогательная функция запуска OpenCV в executor ──────────────────────
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
        "service": "АртМинд API v6.1",
        "modes":   ["auto", "opencv", "groq", "hybrid"],
    }


@app.get("/health")
async def health():
    groq_s = await check_groq_available()
    return {
        "status":       "healthy",
        "opencv_ready": True,
        "groq_ready":   groq_s["available"],
        "groq":         groq_s,
    }


@app.get("/groq/status")
async def groq_status():
    return await check_groq_available()


# ═══════════════════════════════════════
# ГИБРИДНЫЙ ЗАПУСК
# ═══════════════════════════════════════

async def _do_groq_hybrid(image_bytes: bytes, age: Optional[int], ctx: str):
    try:
        opencv_result, groq_result = await asyncio.gather(
            _run_opencv(image_bytes, age, ctx),
            analyze_with_groq(image_bytes, child_age=age, context=ctx),
        )
        result = _hybrid_merge(groq_result, opencv_result)
        result["analysisMode"] = "hybrid"
        return JSONResponse(content=result)
    except Exception as e:
        traceback.print_exc()
        try:
            result = opencv_analyzer.analyze(image_bytes, child_age=age, context=ctx)
            result["analysisMode"]   = "opencv_fallback"
            result["fallbackReason"] = f"Groq недоступен: {e}"
            return JSONResponse(content=result)
        except Exception as e2:
            raise HTTPException(status_code=500, detail=str(e2))


# ═══════════════════════════════════════
# АВТО-РЕЖИМ: Groq hybrid > OpenCV
# ═══════════════════════════════════════

@app.post("/analyze")
async def analyze_auto(
    file:    UploadFile    = File(...),
    age:     Optional[int] = Form(None),
    context: Optional[str] = Form(""),
    mode:    Optional[str] = Form("auto"),
):
    _validate_image(file)
    image_bytes = await _read_image(file)
    ctx = context or ""

    if mode == "hybrid":
        return await _do_groq_hybrid(image_bytes, age, ctx)

    if mode == "opencv":
        try:
            result = opencv_analyzer.analyze(image_bytes, child_age=age, context=ctx)
            result["analysisMode"] = "opencv"
            return JSONResponse(content=result)
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))

    if mode == "groq":
        try:
            result = await analyze_with_groq(image_bytes, child_age=age, context=ctx)
            return JSONResponse(content=result)
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))

    # auto: Groq hybrid > OpenCV
    groq_s = await check_groq_available()
    if groq_s["available"]:
        return await _do_groq_hybrid(image_bytes, age, ctx)
    else:
        try:
            result = opencv_analyzer.analyze(image_bytes, child_age=age, context=ctx)
            result["analysisMode"]   = "opencv"
            result["fallbackReason"] = "Groq недоступен"
            return JSONResponse(content=result)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════
# ОТДЕЛЬНЫЕ ЭНДПОИНТЫ
# ═══════════════════════════════════════

@app.post("/analyze/opencv")
async def analyze_opencv(
    file:    UploadFile    = File(...),
    age:     Optional[int] = Form(None),
    context: Optional[str] = Form(""),
):
    _validate_image(file)
    image_bytes = await _read_image(file)
    try:
        result = opencv_analyzer.analyze(image_bytes, child_age=age, context=context or "")
        result["analysisMode"] = "opencv"
        return JSONResponse(content=result)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/groq")
async def analyze_groq_endpoint(
    file:    UploadFile    = File(...),
    age:     Optional[int] = Form(None),
    context: Optional[str] = Form(""),
):
    _validate_image(file)
    image_bytes = await _read_image(file)
    try:
        result = await analyze_with_groq(image_bytes, child_age=age, context=context or "")
        return JSONResponse(content=result)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/hybrid")
async def analyze_groq_hybrid(
    file:    UploadFile    = File(...),
    age:     Optional[int] = Form(None),
    context: Optional[str] = Form(""),
):
    _validate_image(file)
    image_bytes = await _read_image(file)
    return await _do_groq_hybrid(image_bytes, age, context or "")