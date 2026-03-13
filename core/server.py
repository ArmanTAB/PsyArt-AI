"""
АртМинд — FastAPI Backend v6.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Запуск: py -3.11 -m uvicorn server:app --reload --port 8000

Режимы анализа:
  /analyze              — авто (лучший доступный)
  /analyze/opencv       — только OpenCV
  /analyze/groq         — Groq Vision (LLaMA-4)
  /analyze/claude       — Claude Vision (лучшее качество)
  /analyze/hybrid       — Groq + OpenCV (65/35)
  /analyze/claude_hybrid— Claude + OpenCV (70/30)
  /groq/status          — статус Groq API
  /claude/status        — статус Claude API
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional
import traceback
import asyncio

from analyzer       import DrawingAnalyzer
from groq_analyzer  import analyze_with_groq,   check_groq_available,   _hybrid_merge
from claude_analyzer import analyze_with_claude, check_claude_available, _hybrid_merge_claude

app = FastAPI(
    title="АртМинд API",
    description="Психоэмоциональный анализ детских рисунков",
    version="6.0.0",
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
        "service": "АртМинд API v6.0",
        "modes":   ["auto", "opencv", "groq", "claude", "hybrid", "claude_hybrid"],
    }


@app.get("/health")
async def health():
    groq_s, claude_s = await asyncio.gather(
        check_groq_available(),
        check_claude_available(),
    )
    return {
        "status":        "healthy",
        "opencv_ready":  True,
        "groq_ready":    groq_s["available"],
        "claude_ready":  claude_s["available"],
        "groq":          groq_s,
        "claude":        claude_s,
    }


@app.get("/groq/status")
async def groq_status():
    return await check_groq_available()


@app.get("/claude/status")
async def claude_status():
    return await check_claude_available()


# ═══════════════════════════════════════
# ГИБРИДНЫЕ ЗАПУСКИ
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


async def _do_claude_hybrid(image_bytes: bytes, age: Optional[int], ctx: str):
    try:
        opencv_result, claude_result = await asyncio.gather(
            _run_opencv(image_bytes, age, ctx),
            analyze_with_claude(image_bytes, child_age=age, context=ctx),
        )
        result = _hybrid_merge_claude(claude_result, opencv_result)
        result["analysisMode"] = "claude_hybrid"
        return JSONResponse(content=result)
    except Exception as e:
        traceback.print_exc()
        try:
            result = opencv_analyzer.analyze(image_bytes, child_age=age, context=ctx)
            result["analysisMode"]   = "opencv_fallback"
            result["fallbackReason"] = f"Claude недоступен: {e}"
            return JSONResponse(content=result)
        except Exception as e2:
            raise HTTPException(status_code=500, detail=str(e2))


# ═══════════════════════════════════════
# АВТО-РЕЖИМ: Claude > Groq > OpenCV
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

    if mode == "claude_hybrid":
        return await _do_claude_hybrid(image_bytes, age, ctx)
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

    if mode == "claude":
        try:
            result = await analyze_with_claude(image_bytes, child_age=age, context=ctx)
            return JSONResponse(content=result)
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))

    # auto: Claude hybrid > Groq hybrid > OpenCV
    claude_s, groq_s = await asyncio.gather(
        check_claude_available(),
        check_groq_available(),
    )
    if claude_s["available"]:
        return await _do_claude_hybrid(image_bytes, age, ctx)
    elif groq_s["available"]:
        return await _do_groq_hybrid(image_bytes, age, ctx)
    else:
        try:
            result = opencv_analyzer.analyze(image_bytes, child_age=age, context=ctx)
            result["analysisMode"]   = "opencv"
            result["fallbackReason"] = "Claude и Groq недоступны"
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


@app.post("/analyze/claude")
async def analyze_claude_endpoint(
    file:    UploadFile    = File(...),
    age:     Optional[int] = Form(None),
    context: Optional[str] = Form(""),
):
    _validate_image(file)
    image_bytes = await _read_image(file)
    try:
        result = await analyze_with_claude(image_bytes, child_age=age, context=context or "")
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


@app.post("/analyze/claude_hybrid")
async def analyze_claude_hybrid(
    file:    UploadFile    = File(...),
    age:     Optional[int] = Form(None),
    context: Optional[str] = Form(""),
):
    _validate_image(file)
    image_bytes = await _read_image(file)
    return await _do_claude_hybrid(image_bytes, age, context or "")