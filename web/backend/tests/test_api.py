"""
Core API tests — run from web/backend/:
    pip install pytest httpx Pillow
    pytest tests/test_api.py -v
"""
import io
import os
import sys
import time

import pytest
from fastapi.testclient import TestClient

# Ensure backend package is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_history.db")
os.environ.setdefault("STORAGE_DIR", "/tmp/ps_test_storage")

from main import app  # noqa: E402 — must come after env vars are set

client = TestClient(app)


# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_jpeg_bytes(color: tuple = (34, 139, 34), size: tuple = (100, 100)) -> bytes:
    """Return minimal green JPEG bytes (no ML library needed)."""
    from PIL import Image

    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# ── Health check ───────────────────────────────────────────────────────────────


def test_health_check():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "models_loaded" in data


# ── Model info ─────────────────────────────────────────────────────────────────


def test_get_models():
    resp = client.get("/api/models")
    assert resp.status_code == 200
    data = resp.json()
    assert "pest_detect" in data
    assert "disease_cls" in data
    assert "settings" in data
    # Each model block must have these keys
    for key in ("name", "path", "loaded"):
        assert key in data["pest_detect"]
        assert key in data["disease_cls"]


# ── Settings ───────────────────────────────────────────────────────────────────


def test_update_settings_valid():
    resp = client.post(
        "/api/settings",
        json={"pest_conf_threshold": 0.6, "disease_conf_threshold": 0.55},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["settings"]["pest_conf_threshold"] == pytest.approx(0.6)
    assert data["settings"]["disease_conf_threshold"] == pytest.approx(0.55)


def test_update_settings_invalid_threshold():
    resp = client.post("/api/settings", json={"pest_conf_threshold": 1.5})
    assert resp.status_code == 422  # pydantic validation error


def test_update_settings_zero_threshold():
    resp = client.post("/api/settings", json={"pest_conf_threshold": 0.0})
    assert resp.status_code == 422


# ── Single inference ───────────────────────────────────────────────────────────


def test_infer_requires_file():
    resp = client.post("/api/infer")
    assert resp.status_code == 422


def test_infer_rejects_non_image():
    resp = client.post(
        "/api/infer",
        files={"file": ("malware.exe", b"MZ\x90\x00", "application/octet-stream")},
    )
    assert resp.status_code == 400


def test_infer_single_image():
    """Upload a real JPEG; response shape must be correct regardless of model."""
    resp = client.post(
        "/api/infer",
        files={"file": ("leaf.jpg", _make_jpeg_bytes(), "image/jpeg")},
    )
    assert resp.status_code == 200
    data = resp.json()

    # Required fields
    assert "result_type" in data
    assert "label" in data
    assert "label_zh" in data
    assert "confidence" in data
    assert "elapsed_ms" in data

    # result_type must be one of the known values
    assert data["result_type"] in {"pest", "disease", "healthy", "error"}
    assert isinstance(data["confidence"], float)
    assert data["elapsed_ms"] >= 0


def test_infer_result_saved_to_history():
    """After inference a history record should appear."""
    client.post(
        "/api/infer",
        files={"file": ("history_test.jpg", _make_jpeg_bytes(), "image/jpeg")},
    )
    resp = client.get("/api/history?page=1&page_size=1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


# ── Batch inference ────────────────────────────────────────────────────────────


def test_batch_infer_returns_task_id():
    img1 = _make_jpeg_bytes((0, 128, 0))
    img2 = _make_jpeg_bytes((128, 0, 0))
    resp = client.post(
        "/api/infer/batch",
        files=[
            ("files", ("img1.jpg", img1, "image/jpeg")),
            ("files", ("img2.jpg", img2, "image/jpeg")),
        ],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "task_id" in data
    assert data["total"] == 2


def _submit_batch_task() -> str:
    """Helper: submit a 2-image batch and return task_id."""
    img1 = _make_jpeg_bytes((0, 128, 0))
    img2 = _make_jpeg_bytes((128, 0, 0))
    resp = client.post(
        "/api/infer/batch",
        files=[
            ("files", ("img1.jpg", img1, "image/jpeg")),
            ("files", ("img2.jpg", img2, "image/jpeg")),
        ],
    )
    return resp.json()["task_id"]


def test_task_status_polling():
    task_id = _submit_batch_task()
    # Poll until done (max ~10 s)
    deadline = time.time() + 10
    status = None
    while time.time() < deadline:
        resp = client.get(f"/api/tasks/{task_id}")
        assert resp.status_code == 200
        data = resp.json()
        status = data["status"]
        if status in ("done", "failed"):
            break
        time.sleep(0.3)

    assert status in ("done", "failed", "running", "pending")  # task exists


def test_task_not_found():
    resp = client.get("/api/tasks/nonexistent-task-id-xyz")
    assert resp.status_code == 404


# ── History ────────────────────────────────────────────────────────────────────


def test_history_pagination():
    resp = client.get("/api/history?page=1&page_size=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "items" in data
    assert "page" in data
    assert "page_size" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) <= 5


def test_history_detail_not_found():
    resp = client.get("/api/history/999999")
    assert resp.status_code == 404


def test_history_detail_exists():
    # Infer first, then check history
    client.post(
        "/api/infer",
        files={"file": ("detail_test.jpg", _make_jpeg_bytes(), "image/jpeg")},
    )
    hist = client.get("/api/history?page=1&page_size=1").json()
    record_id = hist["items"][0]["id"]

    resp = client.get(f"/api/history/{record_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == record_id
    assert "boxes" in data
