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

# Size to ask the webcam for in the GUI. None = the camera's own default (640x480 on
# most webcams). Measured with check_speed.py: our USB webcam gives 20 fps at its
# default but only ~10 fps at 1280x720 (it ignores the MJPG request and sends YUY2).
CAMERA_RESOLUTION = None
