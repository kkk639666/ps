"""
番茄病虫害智能识别系统 — Web 后端 (FastAPI)
"""
import json
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

import aiofiles
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

import inference
import tasks as task_manager
from config import (
    CORS_ORIGINS,
    DISEASE_CONF_THRESHOLD,
    HEALTHY_THRESHOLD,
    MAX_BATCH_SIZE,
    PEST_CONF_THRESHOLD,
    PORT,
    STORAGE_DIR,
)
from database import HistoryRecord, SessionLocal, create_tables, get_db
from schemas import SettingsUpdate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── Storage directories ───────────────────────────────────────────────────────
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
(STORAGE_DIR / "uploads").mkdir(exist_ok=True)
(STORAGE_DIR / "outputs").mkdir(exist_ok=True)

# ── Database ──────────────────────────────────────────────────────────────────
create_tables()

# ── Load models (best-effort) ─────────────────────────────────────────────────
inference.load_models()

# ── In-memory settings (persisted per process) ───────────────────────────────
current_settings: dict = {
    "pest_conf_threshold": PEST_CONF_THRESHOLD,
    "disease_conf_threshold": DISEASE_CONF_THRESHOLD,
    "healthy_threshold": HEALTHY_THRESHOLD,
}

@asynccontextmanager
async def lifespan(application: FastAPI):
    # Startup: models are already loaded at module level
    logger.info("Application starting up")
    yield
    # Shutdown: gracefully stop the thread-pool executor
    logger.info("Application shutting down — stopping batch executor")
    task_manager._executor.shutdown(wait=False)


# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="番茄病虫害智能识别系统 API",
    description="提供番茄叶片病虫害识别的 REST API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/storage", StaticFiles(directory=str(STORAGE_DIR)), name="storage")

# ── Allowed image extensions ──────────────────────────────────────────────────
_ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def _safe_ext(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return ext if ext in _ALLOWED_EXTS else ".jpg"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _path_to_url(path: str) -> Optional[str]:
    """Convert an absolute storage path to a /storage/… URL."""
    if not path:
        return None
    try:
        rel = Path(path).relative_to(STORAGE_DIR)
        return f"/storage/{rel.as_posix()}"
    except ValueError:
        return None


def _enrich_result(result: dict, upload_path: Path) -> dict:
    """Add *_url fields to an inference result dict (in-place)."""
    result["annotated_image_url"] = _path_to_url(
        result.get("annotated_image_path", "")
    )
    result["input_image_url"] = _path_to_url(str(upload_path))
    return result


def _save_to_history(db: Session, filename: str, result: dict, input_path: str) -> None:
    """Persist one inference result to SQLite history."""
    try:
        record = HistoryRecord(
            filename=filename,
            result_type=result.get("result_type", ""),
            label=result.get("label", ""),
            label_zh=result.get("label_zh", ""),
            confidence=result.get("confidence", 0.0),
            elapsed_ms=result.get("elapsed_ms", 0.0),
            input_path=input_path,
            output_path=result.get("annotated_image_path") or "",
            extra=json.dumps(result.get("boxes") or [], ensure_ascii=False),
        )
        db.add(record)
        db.commit()
    except Exception as exc:
        logger.error("Failed to save history record: %s", exc)
        db.rollback()


def _record_to_dict(record: HistoryRecord) -> dict:
    d = {
        "id": record.id,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "filename": record.filename,
        "result_type": record.result_type,
        "label": record.label,
        "label_zh": record.label_zh,
        "confidence": record.confidence,
        "elapsed_ms": record.elapsed_ms,
        "input_path": record.input_path,
        "output_path": record.output_path,
        "input_image_url": _path_to_url(record.input_path or ""),
        "annotated_image_url": _path_to_url(record.output_path or ""),
    }
    return d


# ── Endpoints ─────────────────────────────────────────────────────────────────


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "models_loaded": inference._models_loaded}


@app.post("/api/infer")
async def infer_single(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Single image inference (multipart/form-data)."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="只支持图片文件（image/*）")

    ext = _safe_ext(file.filename or "")
    upload_path = STORAGE_DIR / "uploads" / f"{uuid.uuid4().hex}{ext}"

    async with aiofiles.open(str(upload_path), "wb") as f:
        await f.write(await file.read())

    result = inference.run_inference(str(upload_path), STORAGE_DIR, current_settings)
    _enrich_result(result, upload_path)

    _save_to_history(db, file.filename or upload_path.name, result, str(upload_path))
    return result


@app.post("/api/infer/batch")
async def infer_batch(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """Batch inference — saves files and returns a task_id for polling."""
    if not files:
        raise HTTPException(status_code=400, detail="请上传至少一张图片")

    if len(files) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400, detail=f"批量识别最多支持 {MAX_BATCH_SIZE} 张图片"
        )

    file_paths = []
    for file in files:
        if not file.content_type or not file.content_type.startswith("image/"):
            continue
        ext = _safe_ext(file.filename or "")
        upload_path = STORAGE_DIR / "uploads" / f"{uuid.uuid4().hex}{ext}"
        async with aiofiles.open(str(upload_path), "wb") as f:
            await f.write(await file.read())
        file_paths.append((upload_path, file.filename or upload_path.name))

    if not file_paths:
        raise HTTPException(status_code=400, detail="没有有效的图片文件")

    task_id = task_manager.create_task(file_paths)

    def _db_callback(filename: str, result: dict, input_path: str) -> None:
        with SessionLocal() as session:
            _save_to_history(session, filename, result, input_path)

    task_manager.submit_batch_task(
        task_id, file_paths, STORAGE_DIR, current_settings, _db_callback
    )
    return {"task_id": task_id, "total": len(file_paths)}


@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Poll batch task status and partial/complete results."""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    enriched_results = []
    for r in task.get("results", []):
        r_copy = dict(r)
        r_copy["annotated_image_url"] = _path_to_url(
            r_copy.get("annotated_image_path", "")
        )
        enriched_results.append(r_copy)

    return {
        "task_id": task_id,
        "status": task["status"],
        "total": task["total"],
        "completed": task["completed"],
        "results": enriched_results,
        "error": task.get("error"),
    }


@app.get("/api/history")
async def get_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Paginated history records (newest first)."""
    total = db.query(HistoryRecord).count()
    records = (
        db.query(HistoryRecord)
        .order_by(HistoryRecord.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "total": total,
        "items": [_record_to_dict(r) for r in records],
        "page": page,
        "page_size": page_size,
    }


@app.get("/api/history/{record_id}")
async def get_history_detail(record_id: int, db: Session = Depends(get_db)):
    """Get full detail of a single history record."""
    record = db.query(HistoryRecord).filter(HistoryRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    d = _record_to_dict(record)
    d["boxes"] = json.loads(record.extra) if record.extra else []
    return d


@app.get("/api/models")
async def get_models():
    """Return metadata about loaded models and current thresholds."""
    return inference.get_models_info(current_settings)


@app.post("/api/settings")
async def update_settings(body: SettingsUpdate):
    """Update inference thresholds (persisted in-process)."""
    if body.pest_conf_threshold is not None:
        current_settings["pest_conf_threshold"] = body.pest_conf_threshold
    if body.disease_conf_threshold is not None:
        current_settings["disease_conf_threshold"] = body.disease_conf_threshold
    if body.healthy_threshold is not None:
        current_settings["healthy_threshold"] = body.healthy_threshold
    return {"message": "设置已更新", "settings": current_settings}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
