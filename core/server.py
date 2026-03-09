"""
АртМинд — FastAPI Backend v2.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Запуск: uvicorn server:app --reload --port 8000

Режимы анализа:
  /analyze        — автовыбор (LLaVA если доступна, иначе OpenCV)
  /analyze/opencv — принудительно OpenCV (быстро, без LLaVA)
  /analyze/llava  — принудительно LLaVA (требует Ollama)
  /llava/status   — проверка доступности Ollama
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional
import traceback

from analyzer import DrawingAnalyzer
from llava_analyzer import analyze_with_llava, check_ollama_available
import httpx

app = FastAPI(
    title="АртМинд API",
    description="Психоэмоциональный анализ детских рисунков (LLaVA + OpenCV)",
    version="2.0.0",
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


@app.get("/")
def root():
    return {
        "status":  "ok",
        "service": "АртМинд API v2.0",
        "modes":   ["auto", "opencv", "llava"],
    }


@app.get("/health")
async def health():
    ollama = await check_ollama_available()
    return {
        "status":       "healthy",
        "opencv_ready": True,
        "llava_ready":  ollama["available"] and ollama.get("has_llava", False),
        "ollama":       ollama,
    }


@app.get("/llava/status")
async def llava_status():
    """Проверить доступность Ollama и модели LLaVA."""
    return await check_ollama_available()


@app.post("/analyze")
async def analyze_auto(
    file:    UploadFile    = File(...),
    age:     Optional[int] = Form(None),
    context: Optional[str] = Form(""),
    mode:    Optional[str] = Form("auto"),
):
    """
    Анализ рисунка.
    - **mode**: auto (по умолчанию) | opencv | llava
    """
    _validate_image(file)
    image_bytes = await _read_image(file)
    ctx = context or ""

    # Определяем режим
    if mode == "llava":
        use_llava = True
    elif mode == "opencv":
        use_llava = False
    else:
        ollama = await check_ollama_available()
        use_llava = ollama["available"] and ollama.get("has_llava", False)

    if use_llava:
        try:
            result = await analyze_with_llava(image_bytes, child_age=age, context=ctx)
            result["analysisMode"] = "llava"
            return JSONResponse(content=result)
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            if mode == "llava":
                raise HTTPException(status_code=503,
                    detail=f"Ollama недоступна: {e}. Запустите: ollama serve")
            # auto-режим: тихий fallback на OpenCV
            result = opencv_analyzer.analyze(image_bytes, child_age=age, context=ctx)
            result["analysisMode"]   = "opencv_fallback"
            result["fallbackReason"] = f"LLaVA недоступна: {e}"
            return JSONResponse(content=result)
        except ValueError as e:
            if mode == "llava":
                raise HTTPException(status_code=422, detail=f"Ошибка парсинга LLaVA: {e}")
            result = opencv_analyzer.analyze(image_bytes, child_age=age, context=ctx)
            result["analysisMode"]   = "opencv_fallback"
            result["fallbackReason"] = f"LLaVA вернула некорректный ответ"
            return JSONResponse(content=result)
        except Exception as e:
            traceback.print_exc()
            if mode == "llava":
                raise HTTPException(status_code=500, detail=f"Ошибка LLaVA: {e}")
            result = opencv_analyzer.analyze(image_bytes, child_age=age, context=ctx)
            result["analysisMode"]   = "opencv_fallback"
            result["fallbackReason"] = str(e)
            return JSONResponse(content=result)
    else:
        try:
            result = opencv_analyzer.analyze(image_bytes, child_age=age, context=ctx)
            result["analysisMode"] = "opencv"
            return JSONResponse(content=result)
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Ошибка анализа: {e}")


@app.post("/analyze/opencv")
async def analyze_opencv(
    file:    UploadFile    = File(...),
    age:     Optional[int] = Form(None),
    context: Optional[str] = Form(""),
):
    """Принудительно OpenCV — быстро, без Ollama."""
    _validate_image(file)
    image_bytes = await _read_image(file)
    try:
        result = opencv_analyzer.analyze(image_bytes, child_age=age, context=context or "")
        result["analysisMode"] = "opencv"
        return JSONResponse(content=result)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ошибка анализа: {e}")


@app.post("/analyze/llava")
async def analyze_llava_endpoint(
    file:    UploadFile    = File(...),
    age:     Optional[int] = Form(None),
    context: Optional[str] = Form(""),
):
    """Принудительно LLaVA — требует запущенной Ollama с llava:7b."""
    _validate_image(file)
    image_bytes = await _read_image(file)
    try:
        result = await analyze_with_llava(image_bytes, child_age=age, context=context or "")
        result["analysisMode"] = "llava"
        return JSONResponse(content=result)
    except httpx.ConnectError:
        raise HTTPException(status_code=503,
            detail="Ollama не запущена. Выполните в терминале: ollama serve")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504,
            detail="LLaVA не ответила за 120 секунд. Попробуйте ещё раз.")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ошибка LLaVA: {e}")