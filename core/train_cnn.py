"""
АртМинд — Обучение CNN (EfficientNet-B0) v3.0 FINAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Запуск: cd core && py -3.11 train_cnn.py

Лучшая версия: 76.6% accuracy, Macro F1 = 0.764
Сохраняет модель в models/emotion_classifier.pth
"""

import os, sys, json, time, random
from pathlib import Path
from collections import defaultdict, Counter

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset, random_split
from torchvision import transforms, models
from PIL import Image

DRAWINGS_DIR = Path(__file__).parent / "drawings"
MODEL_DIR = Path(__file__).parent / "models"
MODEL_PATH = MODEL_DIR / "emotion_classifier.pth"
META_PATH = MODEL_DIR / "emotion_classifier_meta.json"

CATEGORIES = ["Angry", "Fear", "Happy", "Sad"]
EMOTION_MAP = {"Angry": "агрессия", "Fear": "тревога", "Happy": "радость", "Sad": "грусть"}
NUM_CLASSES = 4; IMAGE_SIZE = 224; BATCH_SIZE = 16; NUM_EPOCHS = 40
LEARNING_RATE = 1e-4; WEIGHT_DECAY = 1e-4; LABEL_SMOOTHING = 0.05
EARLY_STOP_PATIENCE = 12; UNFREEZE_BLOCKS = 2; SEED = 42
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
if torch.cuda.is_available(): torch.cuda.manual_seed_all(SEED)


class DrawingsDataset(Dataset):
    def __init__(self, root_dir, sets=("set1", "set2")):
        self.samples = []; self.class_to_idx = {cat: i for i, cat in enumerate(CATEGORIES)}
        for sn in sets:
            sd = root_dir / sn
            if not sd.exists(): continue
            for cat in CATEGORIES:
                cd = sd / cat
                if not cd.exists(): continue
                for f in cd.iterdir():
                    if f.suffix.lower() in IMAGE_EXTENSIONS:
                        self.samples.append((f, self.class_to_idx[cat]))
        random.shuffle(self.samples)
        counts = defaultdict(int)
        for _, l in self.samples: counts[CATEGORIES[l]] += 1
        print(f"  Загружено {len(self.samples)} изображений")
        for cat in CATEGORIES: print(f"    {cat}: {counts[cat]}")

    def __len__(self): return len(self.samples)
    def __getitem__(self, idx):
        path, label = self.samples[idx]
        try: img = Image.open(path).convert("RGB")
        except: img = Image.new("RGB", (IMAGE_SIZE, IMAGE_SIZE), (0,0,0))
        return img, label

    def get_class_weights(self):
        counts = Counter(l for _, l in self.samples); total = len(self.samples)
        return torch.FloatTensor([total / (NUM_CLASSES * counts.get(i, 1)) for i in range(NUM_CLASSES)])


train_transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE + 32, IMAGE_SIZE + 32)),
    transforms.RandomCrop(IMAGE_SIZE),
    transforms.RandomHorizontalFlip(p=0.5),
    transforms.RandomRotation(15),
    transforms.RandomPerspective(distortion_scale=0.1, p=0.2),
    transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1),
    transforms.GaussianBlur(kernel_size=3, sigma=(0.1, 0.5)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    transforms.RandomErasing(p=0.1, scale=(0.02, 0.08)),
])

val_transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])


def create_model():
    model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.IMAGENET1K_V1)
    for p in model.parameters(): p.requires_grad = False
    for p in model.features[-UNFREEZE_BLOCKS:].parameters(): p.requires_grad = True
    inf = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.3), nn.Linear(inf, 256), nn.ReLU(),
        nn.Dropout(p=0.2), nn.Linear(256, NUM_CLASSES),
    )
    return model


class TrSubset(Dataset):
    def __init__(self, subset, transform):
        self.subset = subset; self.transform = transform
    def __len__(self): return len(self.subset)
    def __getitem__(self, idx):
        path, label = self.subset.dataset.samples[self.subset.indices[idx]]
        try: img = Image.open(path).convert("RGB")
        except: img = Image.new("RGB", (IMAGE_SIZE, IMAGE_SIZE), (0,0,0))
        if self.transform: img = self.transform(img)
        return img, label


def train_epoch(model, loader, criterion, optimizer, device):
    model.train(); tl = c = t = 0
    for imgs, labs in loader:
        imgs, labs = imgs.to(device), labs.to(device)
        optimizer.zero_grad(); out = model(imgs); loss = criterion(out, labs)
        loss.backward(); optimizer.step()
        tl += loss.item()*imgs.size(0); _, pred = out.max(1); c += pred.eq(labs).sum().item(); t += labs.size(0)
    return tl/t, c/t


def evaluate(model, loader, criterion, device):
    model.eval(); tl = c = t = 0; ap, al = [], []
    with torch.no_grad():
        for imgs, labs in loader:
            imgs, labs = imgs.to(device), labs.to(device)
            out = model(imgs); loss = criterion(out, labs)
            tl += loss.item()*imgs.size(0); _, pred = out.max(1); c += pred.eq(labs).sum().item(); t += labs.size(0)
            ap.extend(pred.cpu().numpy()); al.extend(labs.cpu().numpy())
    return tl/t, c/t, ap, al


def print_metrics(labels, preds, classes):
    n = len(classes); cm = np.zeros((n,n), dtype=int)
    for t,p in zip(labels, preds): cm[t][p] += 1
    print(f"\n{'Confusion Matrix':^50}")
    print(f"{'Предск. →':>12}", end="")
    for c in classes: print(f"{c:>10}", end="")
    print()
    for i,c in enumerate(classes):
        print(f"{'Факт: '+c:>12}", end="")
        for j in range(n): print(f"{cm[i][j]:>10}", end="")
        print()
    print(f"\n{'Класс':>10} {'Prec':>8} {'Rec':>8} {'F1':>8} {'Supp':>8}")
    mf = 0
    for i,c in enumerate(classes):
        tp=cm[i][i]; fp=cm[:,i].sum()-tp; fn=cm[i,:].sum()-tp
        p=tp/(tp+fp) if tp+fp else 0; r=tp/(tp+fn) if tp+fn else 0
        f1=2*p*r/(p+r) if p+r else 0; mf+=f1
        print(f"{c:>10} {p:>8.3f} {r:>8.3f} {f1:>8.3f} {cm[i,:].sum():>8}")
    mf/=n; print(f"{'macro':>10} {'':>8} {'':>8} {mf:>8.3f} {sum(cm.sum(1)):>8}")
    return mf, cm


def main():
    print("="*60); print("АртМинд — EfficientNet-B0 v3 FINAL"); print("="*60)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}" + (f" ({torch.cuda.get_device_name(0)})" if device.type=="cuda" else ""))

    ds = DrawingsDataset(DRAWINGS_DIR)
    total = len(ds); cw = ds.get_class_weights().to(device)
    tr = int(0.70*total); va = int(0.15*total); te = total-tr-va
    tr_ds, va_ds, te_ds = random_split(ds, [tr,va,te], generator=torch.Generator().manual_seed(SEED))
    print(f"  Split: {tr}/{va}/{te}")

    trl = DataLoader(TrSubset(tr_ds,train_transform), batch_size=BATCH_SIZE, shuffle=True, num_workers=0, pin_memory=True)
    val = DataLoader(TrSubset(va_ds,val_transform), batch_size=BATCH_SIZE, shuffle=False, num_workers=0, pin_memory=True)
    tel = DataLoader(TrSubset(te_ds,val_transform), batch_size=BATCH_SIZE, shuffle=False, num_workers=0, pin_memory=True)

    model = create_model().to(device)
    print(f"  Параметры: {sum(p.numel() for p in model.parameters() if p.requires_grad):,} обучаемых")

    crit = nn.CrossEntropyLoss(weight=cw, label_smoothing=LABEL_SMOOTHING)
    opt = optim.AdamW(filter(lambda p: p.requires_grad, model.parameters()), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    sched = optim.lr_scheduler.ReduceLROnPlateau(opt, mode="min", patience=4, factor=0.5)

    print(f"\n{'Ep':>4} {'TrLoss':>8} {'TrAcc':>8} {'VLoss':>8} {'VAcc':>8} {'LR':>10}")
    print("─"*50)
    bva=0; bep=0; ni=0; hist={"tl":[],"ta":[],"vl":[],"va":[]}
    t0=time.time()
    for ep in range(1, NUM_EPOCHS+1):
        tl,ta = train_epoch(model,trl,crit,opt,device)
        vl,va_,_,_ = evaluate(model,val,crit,device); sched.step(vl)
        lr=opt.param_groups[0]["lr"]
        print(f"{ep:>4} {tl:>8.4f} {ta:>7.1%} {vl:>8.4f} {va_:>7.1%} {lr:>10.6f}")
        hist["tl"].append(tl); hist["ta"].append(ta); hist["vl"].append(vl); hist["va"].append(va_)
        if va_>bva: bva=va_; bep=ep; ni=0; MODEL_DIR.mkdir(exist_ok=True); torch.save(model.state_dict(), MODEL_PATH)
        else: ni+=1
        if ni>=EARLY_STOP_PATIENCE: print(f"\n⏹ Early stopping (ep {ep})"); break

    elapsed=time.time()-t0
    print(f"\nОбучение: {elapsed:.0f}с, лучшая val: {bva:.1%} (ep {bep})")
    print(f"\n{'='*60}\nТЕСТИРОВАНИЕ\n{'='*60}")
    model.load_state_dict(torch.load(MODEL_PATH, map_location=device, weights_only=True))
    _,tacc,preds,labels = evaluate(model,tel,crit,device)
    print(f"Test Accuracy: {tacc:.1%}")
    el = [EMOTION_MAP[c] for c in CATEGORIES]; mf1,cm = print_metrics(labels,preds,el)

    meta = {"model":"EfficientNet-B0 v3 FINAL","num_classes":NUM_CLASSES,"categories":CATEGORIES,
            "emotion_map":EMOTION_MAP,"image_size":IMAGE_SIZE,
            "dataset":{"total":total,"train":tr,"val":va,"test":te,"sets":["set1","set2"]},
            "training":{"version":"v3","epochs_actual":ep,"best_epoch":bep,"lr":LEARNING_RATE,
                        "batch_size":BATCH_SIZE,"unfreeze_blocks":UNFREEZE_BLOCKS,
                        "label_smoothing":LABEL_SMOOTHING,"early_stop":EARLY_STOP_PATIENCE,
                        "class_weights":cw.cpu().tolist()},
            "results":{"best_val_acc":round(bva,4),"test_acc":round(tacc,4),"macro_f1":round(mf1,4),
                        "confusion_matrix":cm.tolist()},
            "history":{k:[round(v,4) for v in vals] for k,vals in hist.items()}}
    with open(META_PATH,"w",encoding="utf-8") as f: json.dump(meta,f,ensure_ascii=False,indent=2)
    print(f"\n{'='*60}\nСВОДКА\n{'='*60}")
    print(f"EfficientNet-B0 v3 FINAL | {total} рис | Test: {tacc:.1%} | F1: {mf1:.3f} | {elapsed:.0f}с")


if __name__=="__main__": main()