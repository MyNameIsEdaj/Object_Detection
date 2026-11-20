# Real-Time Object Detection System

Detects 5 everyday objects from a webcam in real time: **can, glasses, marker, watch, water bottle**.

Built with **Python 3.11**, **YOLO (Ultralytics)**, **OpenCV** and **ONNX Runtime (DirectML GPU)**.
Images are labelled in **Roboflow** and the model is trained in **Google Colab**, then exported to ONNX and run locally.

---

## Workflow

1. **Collect photos** - `collect_data.py` saves webcam shots to `datasets/my_raw_photos/<class>/`
2. **Label** them in Roboflow and export as *YOLOv8* zip -> put the zip in `datasets/raw_zips/`
3. **Merge datasets** - `prepare_dataset.py` combines your zips + downloaded datasets + negatives
   into `datasets/combined_5_objects_dataset.zip`
4. **Train in Colab** - unzip to `/content/dataset`, train, export with `format="onnx"`
5. **Run** - copy the `.onnx` to `models/5_objects_detector.onnx`, then `main.py`

---

## Project Structure

```
Object_Detection/
├── core/                    # Shared code (used by the scripts and the future GUI)
│   ├── config.py            #   paths, camera indices
│   ├── camera.py            #   open / switch webcams
│   ├── detector.py          #   ONNX model: load, letterbox, decode, NMS
│   ├── tracker.py           #   box smoothing between frames
│   └── drawing.py           #   class colours, box + label drawing
├── main.py                  # Entry point (live detection; GUI later)
├── detect_live.py           # Live webcam detection
├── collect_data.py          # Webcam photo collector for training data
├── prepare_dataset.py       # Merge Roboflow zips into one training dataset
├── models/                  # .onnx models (not in git)
├── datasets/                # raw photos, raw zips, merged dataset (not in git)
├── start_detector.bat       # Double-click launcher: detection
├── start_collector.bat      # Double-click launcher: collector
└── pyproject.toml           # Dependencies (managed by uv)
```

---

## Getting Started

```powershell
uv sync
```

### Live detection
```powershell
uv run python main.py
uv run python detect_live.py --conf 0.4          # start with a higher threshold
uv run python detect_live.py --model models\backups\5_objects_detector_v1_backup.onnx
uv run python detect_live.py --cpu               # force CPU
```
*(or double-click `start_detector.bat`)*

| Key | Action |
|---|---|
| `C` | Switch camera |
| `+` / `=` | Raise confidence threshold |
| `-` | Lower confidence threshold |
| `Q` / `Esc` | Quit |

Class names are read from the model file, so a retrained model with different classes works without code changes.

### Collect photos
```powershell
uv run python collect_data.py
```
*(or double-click `start_collector.bat`)*

| Key | Action |
|---|---|
| `0` | Negative (no objects: empty hands, desk, wall) |
| `1`-`5` | Marker, Watch, Can, Water Bottle, Eye Glasses |
| `C` | Switch camera |
| `Space` | Take one photo |
| `A` | Toggle auto-capture (every 0.6 s) |
| `Q` / `Esc` | Finish |

## Improving accuracy (especially for moving objects)

Measured on 335 of our own webcam photos, the v2 model found: can 60%, water bottle 30%,
marker 23%, glasses 21%, watch 5%. When an object is detected while still, 6 px of motion
blur drops detection to 72%, and 10 px drops it to 28%. Two causes:

1. **The training data doesn't look like our webcam.** Only ~90 of 1,931 training images come
   from our camera. Downloaded glasses images are close-ups (median box = 93% of the image,
   while glasses on a face are a small part of the frame), and the can datasets are mostly
   shelf photos (median box = 0.3% of the image).
2. **No blurry training images**, so the model has never seen a moving object.

What to do, in order of impact:

1. **Label all of `my_raw_photos`** in Roboflow (most are not labelled yet). Roboflow's
   *Label Assist* can pre-draw boxes with the current model, so you only correct them.
2. **Collect more photos with `collect_data.py` in auto mode while moving the object**:
   slow and fast movement, near and far, different angles, both cameras, day and night
   lighting, held in hand and on the desk. Watch on the wrist and in the hand; glasses worn
   and held. Aim for 200+ per object, plus negatives of empty moving hands.
3. **Give our photos the most weight** in `prepare_dataset.py`: raise `max_train` for the
   custom zips, lower the close-up glasses / shelf can sources, and keep `blur_copies: 2`
   (adds motion-blurred copies of our train photos).
4. **Train a slightly bigger model** in Colab (below).

### Training in Colab
```python
!pip install -q ultralytics
!unzip -q -o combined_5_objects_dataset.zip -d /content/dataset

from ultralytics import YOLO
model = YOLO("yolo11s.pt")          # "s" is more accurate than "n"; fine on the RTX 4050
model.train(data="/content/dataset/data.yaml", imgsz=640, epochs=150, patience=30,
            batch=16, degrees=10, scale=0.5, hsv_v=0.5, close_mosaic=15)
model.export(format="onnx", imgsz=640, simplify=True, opset=12)
# download runs/detect/train/weights/best.onnx -> models/5_objects_detector.onnx
```
Stick to YOLOv8 / YOLO11. YOLO26 exports an NMS-free output format that `core/detector.py`
does not read yet.

### Build the training dataset
```powershell
uv run python prepare_dataset.py
```
Edit `DATASET_SOURCES` at the top of the script to add zips or change how many images are sampled.
For each zip the script prints the zip's own class names next to your `mapping`, so you can check the ids line up.
