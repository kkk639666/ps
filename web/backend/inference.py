"""
Cascade inference module:
  1. Pest detection (YOLO) — if pests found → return pest result with boxes
  2. Disease classification (ResNet/custom) — if no pest → classify disease or healthy
Falls back gracefully when models are not available.
"""
import time
import json
import os
import uuid
import logging
from pathlib import Path
from typing import Optional, Dict, Any
logger = logging.getLogger(__name__)

# Global model instances
_pest_detector = None
_disease_classifier = None
_disease_classes = None
_models_loaded = False

# Disease label → Chinese name mapping
_ZH_LABEL_MAP = {
    "tomato_healthy": "健康",
    "tomato_early_blight": "早疫病",
    "tomato_late_blight": "晚疫病",
    "tomato_leaf_mold": "叶霉病",
    "tomato_septoria_leaf_spot": "叶斑病",
    "tomato_spider_mites": "红蜘蛛",
    "tomato_target_spot": "靶斑病",
    "tomato_yellow_leaf_curl_virus": "黄化曲叶病毒",
    "tomato_mosaic_virus": "花叶病毒",
    "tomato_bacterial_spot": "细菌性斑点病",
    "healthy": "健康",
    "pest": "虫害",
}


def _get_zh_label(label: str) -> str:
    """Map English label to Chinese display name."""
    key = label.lower().replace(" ", "_")
    for k, v in _ZH_LABEL_MAP.items():
        if k in key:
            return v
    return label


def load_models() -> bool:
    """
    Attempt to load YOLO pest detector and disease classifier.
    Returns True if at least one model loaded successfully.
    """
    global _pest_detector, _disease_classifier, _disease_classes, _models_loaded

    from config import (
        PEST_DETECT_MODEL,
        DISEASE_CLS_MODEL,
        DISEASE_CLASSES_JSON,
    )

    # --- Disease class names ---
    if os.path.exists(DISEASE_CLASSES_JSON):
        try:
            with open(DISEASE_CLASSES_JSON, "r", encoding="utf-8") as f:
                _disease_classes = json.load(f)
            logger.info("Loaded disease classes: %d classes", len(_disease_classes))
        except Exception as exc:
            logger.warning("Failed to load disease_classes.json: %s", exc)

    # --- Pest detection model (YOLO via ultralytics) ---
    if os.path.exists(PEST_DETECT_MODEL):
        try:
            from ultralytics import YOLO

            _pest_detector = YOLO(PEST_DETECT_MODEL)
            logger.info("Loaded pest detection model: %s", PEST_DETECT_MODEL)
        except Exception as exc:
            logger.warning("Failed to load pest model: %s", exc)
    else:
        logger.warning("Pest model not found: %s", PEST_DETECT_MODEL)

    # --- Disease classification model (PyTorch state-dict) ---
    if os.path.exists(DISEASE_CLS_MODEL):
        try:
            import torch
            import torchvision.models as tv_models

            num_classes = (
                len(_disease_classes)
                if isinstance(_disease_classes, list)
                else 10
            )
            model = tv_models.resnet50(weights=None)
            model.fc = torch.nn.Linear(model.fc.in_features, num_classes)

            # weights_only=True prevents arbitrary code execution from pickle files
            checkpoint = torch.load(DISEASE_CLS_MODEL, map_location="cpu", weights_only=True)
            if isinstance(checkpoint, dict):
                state = (
                    checkpoint.get("state_dict")
                    or checkpoint.get("model_state_dict")
                    or checkpoint
                )
            else:
                state = checkpoint
            model.load_state_dict(state)
            model.eval()
            _disease_classifier = model
            logger.info("Loaded disease classification model: %s", DISEASE_CLS_MODEL)
        except Exception as exc:
            logger.warning("Failed to load disease model: %s", exc)
    else:
        logger.warning("Disease model not found: %s", DISEASE_CLS_MODEL)

    _models_loaded = _pest_detector is not None or _disease_classifier is not None
    return _models_loaded


def _bgr_to_rgb(img):
    """Convert a numpy BGR array (from OpenCV/YOLO plot()) to RGB."""
    return img[..., ::-1]


def _save_annotated_image(result_obj, storage_dir: Path) -> Optional[str]:
    """Save YOLO-annotated image and return its path string."""
    try:
        from PIL import Image as PILImage

        annotated = result_obj.plot()  # numpy array BGR
        out_dir = storage_dir / "outputs"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"annotated_{uuid.uuid4().hex[:10]}.jpg"
        PILImage.fromarray(_bgr_to_rgb(annotated)).save(str(out_path))
        return str(out_path)
    except Exception as exc:
        logger.error("Failed to save annotated image: %s", exc)
        return None


def run_inference(image_path: str, storage_dir: Path, settings: dict) -> Dict[str, Any]:
    """
    Run cascade inference on a single image.

    Returns a dict with keys:
        result_type, label, label_zh, confidence, elapsed_ms,
        boxes, annotated_image_path, message
    """
    t0 = time.time()
    pest_thr = settings.get("pest_conf_threshold", 0.5)
    disease_thr = settings.get("disease_conf_threshold", 0.5)
    healthy_thr = settings.get("healthy_threshold", 0.8)

    def _elapsed():
        return (time.time() - t0) * 1000

    try:
        from PIL import Image as PILImage

        img = PILImage.open(image_path).convert("RGB")

        # ── Step 1: pest detection ──────────────────────────────────────────
        if _pest_detector is not None:
            results = _pest_detector(image_path, conf=pest_thr, verbose=False)
            yolo_result = results[0]
            boxes_data = []
            for box in yolo_result.boxes:
                conf = float(box.conf[0])
                if conf >= pest_thr:
                    x1, y1, x2, y2 = (float(v) for v in box.xyxy[0])
                    boxes_data.append(
                        {
                            "x1": x1,
                            "y1": y1,
                            "x2": x2,
                            "y2": y2,
                            "confidence": conf,
                            "label": "pest",
                        }
                    )

            if boxes_data:
                annotated_path = _save_annotated_image(yolo_result, storage_dir)
                max_conf = max(b["confidence"] for b in boxes_data)
                return {
                    "result_type": "pest",
                    "label": "pest",
                    "label_zh": "检测到害虫",
                    "confidence": max_conf,
                    "elapsed_ms": _elapsed(),
                    "boxes": boxes_data,
                    "annotated_image_path": annotated_path,
                    "message": f"检测到 {len(boxes_data)} 个害虫目标",
                }

        # ── Step 2: disease classification ─────────────────────────────────
        if _disease_classifier is not None and _disease_classes is not None:
            import torch
            from torchvision import transforms

            tfm = transforms.Compose(
                [
                    transforms.Resize(256),
                    transforms.CenterCrop(224),
                    transforms.ToTensor(),
                    transforms.Normalize(
                        [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]
                    ),
                ]
            )
            tensor = tfm(img).unsqueeze(0)
            with torch.no_grad():
                logits = _disease_classifier(tensor)
                probs = torch.softmax(logits, dim=1)
                top_prob, top_idx = probs.topk(1)

            confidence = float(top_prob[0][0])
            class_idx = int(top_idx[0][0])

            if isinstance(_disease_classes, list):
                label = (
                    _disease_classes[class_idx]
                    if class_idx < len(_disease_classes)
                    else f"class_{class_idx}"
                )
            elif isinstance(_disease_classes, dict):
                label = _disease_classes.get(str(class_idx), f"class_{class_idx}")
            else:
                label = f"class_{class_idx}"

            is_healthy = "healthy" in label.lower()
            if is_healthy and confidence >= healthy_thr:
                result_type = "healthy"
                label_zh = "健康"
            elif confidence < disease_thr:
                result_type = "healthy"
                label_zh = "健康（置信度低）"
            else:
                result_type = "disease"
                label_zh = _get_zh_label(label)

            return {
                "result_type": result_type,
                "label": label,
                "label_zh": label_zh,
                "confidence": confidence,
                "elapsed_ms": _elapsed(),
                "boxes": None,
                "annotated_image_path": None,
                "message": None,
            }

        # ── No models available ─────────────────────────────────────────────
        return {
            "result_type": "error",
            "label": "model_not_loaded",
            "label_zh": "模型未加载",
            "confidence": 0.0,
            "elapsed_ms": _elapsed(),
            "boxes": None,
            "annotated_image_path": None,
            "message": "模型文件未找到，请将模型放入 models/ 目录后重启服务",
        }

    except Exception as exc:
        logger.error("Inference error on %s: %s", image_path, exc, exc_info=True)
        return {
            "result_type": "error",
            "label": "error",
            "label_zh": "识别失败",
            "confidence": 0.0,
            "elapsed_ms": _elapsed(),
            "boxes": None,
            "annotated_image_path": None,
            "message": str(exc),
        }


def get_models_info(settings: dict) -> dict:
    """Return metadata about loaded/available models."""
    import datetime as dt
    from config import PEST_DETECT_MODEL, DISEASE_CLS_MODEL

    def _file_info(path: str, loaded: bool, default_name: str, classes) -> dict:
        info: Dict[str, Any] = {
            "name": default_name,
            "path": path,
            "loaded": loaded,
            "modified_at": None,
            "classes": classes,
        }
        if os.path.exists(path):
            mtime = os.path.getmtime(path)
            info["modified_at"] = dt.datetime.fromtimestamp(mtime).isoformat()
        return info

    disease_classes = None
    if isinstance(_disease_classes, list):
        disease_classes = _disease_classes
    elif isinstance(_disease_classes, dict):
        disease_classes = list(_disease_classes.values())

    return {
        "pest_detect": _file_info(
            PEST_DETECT_MODEL, _pest_detector is not None, "pest_detect.pt", ["pest"]
        ),
        "disease_cls": _file_info(
            DISEASE_CLS_MODEL,
            _disease_classifier is not None,
            "disease_cls.pth",
            disease_classes,
        ),
        "settings": settings,
    }
