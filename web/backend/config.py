import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", str(BASE_DIR / "storage")))
MODELS_DIR = Path(os.getenv("MODELS_DIR", str(BASE_DIR.parent.parent / "models")))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/history.db")
PORT = int(os.getenv("PORT", "8000"))
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
).split(",")

# Model paths
PEST_DETECT_MODEL = os.getenv("PEST_DETECT_MODEL", str(MODELS_DIR / "pest_detect.pt"))
DISEASE_CLS_MODEL = os.getenv("DISEASE_CLS_MODEL", str(MODELS_DIR / "disease_cls.pth"))
DISEASE_CLASSES_JSON = os.getenv(
    "DISEASE_CLASSES_JSON", str(MODELS_DIR / "disease_classes.json")
)

# Thresholds
PEST_CONF_THRESHOLD = float(os.getenv("PEST_CONF_THRESHOLD", "0.5"))
DISEASE_CONF_THRESHOLD = float(os.getenv("DISEASE_CONF_THRESHOLD", "0.5"))
HEALTHY_THRESHOLD = float(os.getenv("HEALTHY_THRESHOLD", "0.8"))

# Batch processing
MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", "50"))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "2"))
