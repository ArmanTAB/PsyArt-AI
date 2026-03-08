"""
АртМинд — FastAPI Backend
Запуск: py -3.11 -m uvicorn server:app --reload --port 8000
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional
import traceback

from analyzer import DrawingAnalyzer

app = FastAPI(
    title="АртМинд API",
    description="Психоэмоциональный анализ детских рисунков",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

analyzer = DrawingAnalyzer()


@app.get("/")
def root():
    return {"status": "ok", "service": "АртМинд API v1.0"}


@app.get("/health")
def health():
    return {"status": "healthy", "model": "rule-based + OpenCV + sklearn"}


@app.post("/analyze")
async def analyze_drawing(
    file: UploadFile = File(...),
    age: Optional[int] = Form(None),
    context: Optional[str] = Form(""),
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Файл должен быть изображением")

    try:
        image_bytes = await file.read()
        if len(image_bytes) > 15 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Файл слишком большой (макс. 15 МБ)")

        result = analyzer.analyze(image_bytes, child_age=age, context=context or "")
        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ошибка анализа: {str(e)}")