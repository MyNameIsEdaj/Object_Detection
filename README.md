# Real-Time Object Detection System

A lightweight, real-time computer vision system built with **Python 3.11**, **YOLO (Ultralytics)**, **OpenCV**, and **ONNX Runtime**. 

This project trains custom object detection models and runs high-speed live inference through a webcam feed.

---

## Project Structure

```
Object_Detection/
├── collect_data.py       # Tool to capture training images via webcam
├── prepare_dataset.py    # Script to organize, merge, and format datasets for YOLO
├── detect_live.py        # Real-time webcam inference using ONNX Runtime
├── main.py               # Main application entry point
├── start_collector.bat   # Windows one-click launcher for data collection
├── start_detector.bat    # Windows one-click launcher for live detection
├── pyproject.toml        # Project dependencies and configuration (managed by uv)
├── .python-version       # Pinned Python version (3.11)
└── .gitignore            # Git exclusions for datasets, weights, and environments
```

---

## Tech Stack & Libraries

* **Language:** Python 3.11
* **Inference Engine:** `onnxruntime` (Microsoft ONNX Runtime for CPU/DirectML acceleration)
* **Computer Vision:** `opencv-python` (Webcam capture, bounding box rendering, Non-Maximum Suppression)
* **Model Framework:** `ultralytics` (YOLOv8 / YOLO11)
* **Package Manager:** `uv`

---

## Getting Started

### 1. Install Dependencies
Using `uv`:
```powershell
uv sync
```

### 2. Live Object Detection
To start real-time detection on your webcam:
```powershell
uv run python main.py
```
*(or double-click `start_detector.bat`)*

**Controls during detection:**
* `+` or `=`: Increase confidence threshold
* `-`: Decrease confidence threshold
* `Q` or `ESC`: Exit detection

### 3. Collecting Custom Dataset Photos
To capture photos of new objects using your webcam:
```powershell
uv run python collect_data.py
```
*(or double-click `start_collector.bat`)*

**Controls during capture:**
* `SPACEBAR`: Take a single photo
* `A`: Toggle auto-capture mode (takes a photo every 0.8s)
* `Q` or `ESC`: Save and exit
