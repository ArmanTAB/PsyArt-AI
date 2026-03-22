"""
АртМинд — CNN-классификатор эмоций v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EfficientNet-B0, дообученный на датасете детских рисунков.
Модель: models/emotion_classifier.pth
"""

import json, io
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
from torchvision import transforms, models
from PIL import Image

MODEL_DIR = Path(__file__).parent / "models"
MODEL_PATH = MODEL_DIR / "emotion_classifier.pth"
META_PATH = MODEL_DIR / "emotion_classifier_meta.json"

CATEGORIES = ["Angry", "Fear", "Happy", "Sad"]
CNN_TO_EMOTION = {0: "агрессия", 1: "тревога", 2: "радость", 3: "грусть"}
NUM_CLASSES = 4; IMAGE_SIZE = 224

_transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])
_model = None; _device = None


def _load_model():
    global _model, _device
    if _model is not None: return _model, _device
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Модель не найдена: {MODEL_PATH}\nЗапустите: py -3.11 train_cnn.py")
    _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = models.efficientnet_b0(weights=None)
    inf = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.3), nn.Linear(inf, 256), nn.ReLU(),
        nn.Dropout(p=0.2), nn.Linear(256, NUM_CLASSES),
    )
    model.load_state_dict(torch.load(MODEL_PATH, map_location=_device, weights_only=True))
    model.to(_device); model.eval(); _model = model
    return _model, _device


def _predict(image_bytes: bytes) -> dict:
    model, device = _load_model()
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    tensor = _transform(img).unsqueeze(0).to(device)
    with torch.no_grad():
        probs = torch.softmax(model(tensor), dim=1).cpu().numpy()[0]
    idx = int(np.argmax(probs))
    return {"class_idx": idx, "class_name": CATEGORIES[idx], "emotion": CNN_TO_EMOTION[idx],
            "confidence": float(probs[idx]),
            "probabilities": {CNN_TO_EMOTION[i]: float(probs[i]) for i in range(NUM_CLASSES)}}


def analyze_with_cnn(image_bytes: bytes, child_age: Optional[int] = None, context: str = "") -> dict:
    pred = _predict(image_bytes); probs = pred["probabilities"]
    neg = probs.get("тревога",0) + probs.get("агрессия",0) + probs.get("грусть",0)
    calm = max(0, (1-neg) * probs.get("радость",0))

    emotions = []
    for name, prob in probs.items():
        i = round(prob*100)
        if i >= 10: emotions.append({"name": name, "intensity": i, "evidence": f"CNN EfficientNet-B0: {prob:.1%}"})
    ci = round(calm*100)
    if ci >= 10: emotions.append({"name": "спокойствие", "intensity": ci, "evidence": "CNN: баланс эмоций"})
    emotions.sort(key=lambda x: -x["intensity"]); emotions = emotions[:5]

    dom = pred["emotion"]; dp = pred["confidence"]
    if dom in ("тревога","агрессия","грусть") and dp > 0.7: state = "требует_консультации"
    elif dom in ("тревога","агрессия","грусть") and dp > 0.4: state = "требует_внимания"
    else: state = "норма"

    risks = []
    if probs.get("агрессия",0)>0.5: risks.append(f"CNN: агрессия {probs['агрессия']:.0%}")
    if probs.get("тревога",0)>0.5: risks.append(f"CNN: тревога {probs['тревога']:.0%}")
    if probs.get("грусть",0)>0.5: risks.append(f"CNN: грусть {probs['грусть']:.0%}")

    recs = []
    if dom=="агрессия": recs.extend(["CNN: признаки агрессии — рекомендована беседа","Обратить внимание на окружение"])
    elif dom=="тревога": recs.extend(["CNN: тревожность — упражнения на релаксацию","Беседа в спокойной обстановке"])
    elif dom=="грусть": recs.extend(["CNN: грусть — эмоциональный контакт","Арт-терапия с яркими цветами"])
    else: recs.append("Эмоциональный фон благоприятный")
    recs.append("Результаты требуют очной консультации специалиста")

    age_s = f"{child_age}-летнего ребёнка" if child_age else "ребёнка"
    port = f"CNN-анализ рисунка {age_s}: «{dom}» с уверенностью {dp:.0%}. "
    port += {"радость":"Позитивное состояние.","грусть":"Возможна подавленность.",
             "тревога":"Признаки тревожности.","агрессия":"Признаки агрессии."}.get(dom,"")

    return {
        "emotions": emotions, "psychologicalPortrait": port,
        "riskFactors": risks, "recommendations": recs,
        "overallState": state, "confidence": max(50,min(96,round(dp*100))),
        "analysisMode": "cnn", "moduleWeights": {"cnn_efficientnet": 1.0},
        "cnnPrediction": {"class": pred["class_name"], "emotion": dom,
                          "probability": round(dp,3),
                          "allProbabilities": {k:round(v,3) for k,v in probs.items()}},
        "colorAnalysis": {"dominant":[],"palette":"","brightnessClass":"","saturationClass":"",
                          "brightnessValue":0,"saturationValue":0,"colorRatios":{},
                          "interpretation":"CNN не анализирует цвет отдельно"},
        "composition": {"fillRatio":0,"fillClass":"","location":"","numObjects":0,
                        "complexity":"","lineDensity":0,"style":"","spaceUsage":"",
                        "interpretation":"CNN не анализирует композицию отдельно"},
    }


async def check_cnn_available() -> dict:
    if not MODEL_PATH.exists():
        return {"available": False, "error": f"Модель не найдена: {MODEL_PATH}"}
    try:
        _load_model(); meta = {}
        if META_PATH.exists():
            with open(META_PATH,"r",encoding="utf-8") as f: meta = json.load(f)
        return {"available": True, "model": "EfficientNet-B0", "device": str(_device),
                "test_accuracy": meta.get("results",{}).get("test_acc",0),
                "macro_f1": meta.get("results",{}).get("macro_f1",0)}
    except Exception as e:
        return {"available": False, "error": str(e)}