"""
Background batch-task management using a thread-pool executor.
Tasks are kept in-process memory (suitable for MVP single-server deployments).
"""
import uuid
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Optional, Callable, Tuple

from config import MAX_WORKERS

logger = logging.getLogger(__name__)

_tasks: Dict[str, Dict[str, Any]] = {}
_executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)


def create_task(files: List) -> str:
    """Register a new batch task and return its ID."""
    task_id = str(uuid.uuid4())
    _tasks[task_id] = {
        "status": "pending",
        "total": len(files),
        "completed": 0,
        "results": [],
        "error": None,
    }
    return task_id


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    return _tasks.get(task_id)


def _run_batch(
    task_id: str,
    file_paths: List[Tuple[Path, str]],
    storage_dir: Path,
    settings: dict,
    db_callback: Optional[Callable],
) -> None:
    """Worker function executed in the thread-pool."""
    from inference import run_inference

    _tasks[task_id]["status"] = "running"
    try:
        for i, (file_path, filename) in enumerate(file_paths):
            try:
                result = run_inference(str(file_path), storage_dir, settings)
                result["filename"] = filename
            except Exception as exc:
                logger.error("Error processing %s: %s", filename, exc)
                result = {
                    "filename": filename,
                    "result_type": "error",
                    "label": "error",
                    "label_zh": "识别失败",
                    "confidence": 0.0,
                    "elapsed_ms": 0.0,
                    "boxes": None,
                    "annotated_image_path": None,
                    "message": str(exc),
                }

            _tasks[task_id]["results"].append(result)
            _tasks[task_id]["completed"] = i + 1

            if db_callback:
                try:
                    db_callback(filename, result, str(file_path))
                except Exception as exc:
                    logger.error("DB callback failed for %s: %s", filename, exc)

        _tasks[task_id]["status"] = "done"
    except Exception as exc:
        logger.error("Batch task %s failed: %s", task_id, exc, exc_info=True)
        _tasks[task_id]["status"] = "failed"
        _tasks[task_id]["error"] = str(exc)


def submit_batch_task(
    task_id: str,
    file_paths: List[Tuple[Path, str]],
    storage_dir: Path,
    settings: dict,
    db_callback: Optional[Callable] = None,
) -> None:
    """Submit a batch task to the thread-pool executor."""
    _executor.submit(_run_batch, task_id, file_paths, storage_dir, settings, db_callback)
