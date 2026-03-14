from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List, Any
from datetime import datetime


class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    label: str


class InferResult(BaseModel):
    result_type: str  # "pest" | "disease" | "healthy" | "error"
    label: str
    label_zh: str
    confidence: float
    elapsed_ms: float
    boxes: Optional[List[BoundingBox]] = None
    annotated_image_url: Optional[str] = None
    input_image_url: Optional[str] = None
    message: Optional[str] = None


class HistoryItem(BaseModel):
    id: int
    created_at: Optional[str]
    filename: str
    result_type: str
    label: str
    label_zh: str
    confidence: float
    elapsed_ms: float
    input_path: Optional[str] = None
    output_path: Optional[str] = None
    input_image_url: Optional[str] = None
    annotated_image_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class HistoryResponse(BaseModel):
    total: int
    items: List[HistoryItem]
    page: int
    page_size: int


class TaskStatus(BaseModel):
    task_id: str
    status: str  # "pending" | "running" | "done" | "failed"
    total: int
    completed: int
    results: Optional[List[Any]] = None
    error: Optional[str] = None


class ModelInfo(BaseModel):
    name: str
    path: str
    loaded: bool
    modified_at: Optional[str] = None
    classes: Optional[List[str]] = None


class ModelsResponse(BaseModel):
    pest_detect: ModelInfo
    disease_cls: ModelInfo
    settings: dict


class SettingsUpdate(BaseModel):
    pest_conf_threshold: Optional[float] = None
    disease_conf_threshold: Optional[float] = None
    healthy_threshold: Optional[float] = None

    @field_validator("pest_conf_threshold", "disease_conf_threshold", "healthy_threshold")
    @classmethod
    def validate_threshold(cls, v):
        if v is not None and not (0 < v <= 1):
            raise ValueError("阈值必须在 (0, 1] 范围内")
        return v
