"""Shared building blocks for the object detection project.

Everything that both the command-line tools and the future GUI need lives here,
so the GUI can import the same detector/camera/tracker instead of copying code.
"""
from .camera import CameraManager, open_camera
from .config import (
    DATASETS_DIR,
    DEFAULT_MODEL_PATH,
    MODELS_DIR,
    PROJECT_ROOT,
    RAW_PHOTOS_DIR,
    RAW_ZIPS_DIR,
)
from .detector import Detection, YoloOnnxDetector
from .drawing import color_for, draw_detections
from .tracker import ObjectTracker

__all__ = [
    "CameraManager",
    "open_camera",
    "Detection",
    "YoloOnnxDetector",
    "ObjectTracker",
    "draw_detections",
    "color_for",
    "PROJECT_ROOT",
    "MODELS_DIR",
    "DEFAULT_MODEL_PATH",
    "DATASETS_DIR",
    "RAW_PHOTOS_DIR",
    "RAW_ZIPS_DIR",
]
