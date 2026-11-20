"""Project-wide paths and defaults (one place to change them)."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

MODELS_DIR = PROJECT_ROOT / "models"
DEFAULT_MODEL_PATH = MODELS_DIR / "5_objects_detector.onnx"

DATASETS_DIR = PROJECT_ROOT / "datasets"
RAW_PHOTOS_DIR = DATASETS_DIR / "my_raw_photos"
RAW_ZIPS_DIR = DATASETS_DIR / "raw_zips"

# Camera indices to cycle through with the [C] key.
# 1 = external USB webcam (A4Tech), 0 = laptop webcam, 2 = any extra camera.
CAMERA_INDICES = (1, 0, 2)
