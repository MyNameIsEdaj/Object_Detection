"""
Real-Time Multi-Object Detection with Smooth Temporal Tracking
Features:
- Dynamic 5 classes with custom color tags
- Exponential Moving Average (EMA) box smoothing to eliminate jitter & flicker
- Motion persistence (prevents boxes from disappearing during quick movements)
- Lower default threshold (0.25) for immediate responsiveness
- Live camera switcher [C]
"""
import cv2
import numpy as np
import onnxruntime as ort
import os
import time


class ObjectTracker:
    """Smooths bounding boxes over time to prevent jitter and flickering."""
    def __init__(self, alpha=0.55, max_missed_frames=6):
        self.alpha = alpha  # Smoothing factor (higher = faster response, lower = smoother)
        self.max_missed = max_missed_frames
        self.active_tracks = []  # list of dicts: {'box': [x,y,w,h], 'cls': int, 'conf': float, 'missed': 0}

    def update(self, new_boxes, new_confs, new_classes):
        updated_tracks = []
        used_new = set()

        # Match new detections with existing tracks based on IoU overlap
        for track in self.active_tracks:
            best_iou = 0.0
            best_idx = -1

            for i, (n_box, n_cls) in enumerate(zip(new_boxes, new_classes)):
                if i in used_new or n_cls != track['cls']:
                    continue
                iou = self._compute_iou(track['box'], n_box)
                if iou > best_iou:
                    best_iou = iou
                    best_idx = i

            if best_iou > 0.25 and best_idx != -1:
                # Smooth the box coordinates with EMA
                tb = track['box']
                nb = new_boxes[best_idx]
                smooth_box = [
                    int(self.alpha * nb[0] + (1 - self.alpha) * tb[0]),
                    int(self.alpha * nb[1] + (1 - self.alpha) * tb[1]),
                    int(self.alpha * nb[2] + (1 - self.alpha) * tb[2]),
                    int(self.alpha * nb[3] + (1 - self.alpha) * tb[3])
                ]
                updated_tracks.append({
                    'box': smooth_box,
                    'cls': track['cls'],
                    'conf': float(self.alpha * new_confs[best_idx] + (1 - self.alpha) * track['conf']),
                    'missed': 0
                })
                used_new.add(best_idx)
            else:
                # Persist track for a few frames if temporarily lost
                track['missed'] += 1
                if track['missed'] <= self.max_missed:
                    updated_tracks.append(track)

        # Add remaining new detections as new tracks
        for i, (n_box, n_conf, n_cls) in enumerate(zip(new_boxes, new_confs, new_classes)):
            if i not in used_new:
                updated_tracks.append({
                    'box': n_box,
                    'cls': n_cls,
                    'conf': n_conf,
                    'missed': 0
                })

        self.active_tracks = updated_tracks
        return [(t['box'], t['conf'], t['cls']) for t in self.active_tracks]

    @staticmethod
    def _compute_iou(boxA, boxB):
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[0] + boxA[2], boxB[0] + boxB[2])
        yB = min(boxA[1] + boxA[3], boxB[1] + boxB[3])
        interArea = max(0, xB - xA) * max(0, yB - yA)
        boxAArea = boxA[2] * boxA[3]
        boxBArea = boxB[2] * boxB[3]
        denom = float(boxAArea + boxBArea - interArea)
        return interArea / denom if denom > 0 else 0.0


def open_camera(cam_idx):
    cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(cam_idx)
    return cap


def main():
    base_dir = os.path.dirname(__file__)
    model_path = os.path.join(base_dir, "models", "5_objects_detector.onnx")
    if not os.path.exists(model_path):
        model_path = os.path.join(base_dir, "5_objects_detector.onnx")

    if not os.path.exists(model_path):
        print(f"Error: No ONNX model found in '{base_dir}'!")
        return

    print("Loading ONNX model...")
    session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
    input_name = session.get_inputs()[0].name
    out_shape = session.get_outputs()[0].shape
    num_classes = out_shape[1] - 4

    all_classes = [
        ("Can", (0, 140, 255)),          # Orange
        ("Glasses", (255, 0, 255)),      # Magenta
        ("Marker", (0, 255, 0)),         # Green
        ("Watch", (255, 255, 0)),        # Cyan
        ("Water Bottle", (255, 120, 0))  # Blue
    ]

    class_names = [c[0] for c in all_classes[:num_classes]]
    class_colors = [c[1] for c in all_classes[:num_classes]]

    # Camera cycling
    cam_indices = [1, 0, 2]
    current_cam_pos = 0
    cam_idx = cam_indices[current_cam_pos]

    cap = open_camera(cam_idx)
    if not cap.isOpened():
        current_cam_pos = 1
        cam_idx = cam_indices[current_cam_pos]
        cap = open_camera(cam_idx)

    if not cap.isOpened():
        print("Error: Could not open any camera. Please close Windows Camera app or Zoom.")
        return

    # Responsive threshold & Smoother initialization
    CONF_THRESHOLD = 0.25  # Lower threshold catches objects instantly
    IOU_THRESHOLD = 0.45
    tracker = ObjectTracker(alpha=0.6, max_missed_frames=5)
    WINDOW_NAME = "Multi-Object Detection (Smooth Tracker)"

    print("=" * 65)
    print("      LIVE MULTI-OBJECT DETECTION (SMOOTH TRACKING)")
    print("=" * 65)
    print(f"Model: {os.path.basename(model_path)}")
    print(f"Active Camera: Index {cam_idx}")
    print(f"Classes: {', '.join(class_names)}")
    print("\nControls:")
    print("  [C]          : Switch Camera")
    print("  [+] or [=]   : Increase confidence threshold")
    print("  [-]          : Decrease confidence threshold")
    print("  [Q] or [X]   : Exit")
    print("=" * 65)

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_AUTOSIZE)

    prev_time = time.time()
    fps = 0
    fail_count = 0

    while True:
        if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
            print("\nWindow closed by user.")
            break

        ret, frame = cap.read()
        if not ret or frame is None:
            fail_count += 1
            if fail_count > 20:
                print("Camera feed lost. Exiting.")
                break
            time.sleep(0.05)
            continue
        fail_count = 0

        orig_h, orig_w = frame.shape[:2]

        curr_time = time.time()
        fps = int(1.0 / (curr_time - prev_time)) if (curr_time - prev_time) > 0 else fps
        prev_time = curr_time

        # --- PREPROCESSING ---
        rgb_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb_img, (640, 640))
        input_data = (resized.astype(np.float32) / 255.0).transpose(2, 0, 1)
        input_tensor = np.expand_dims(input_data, axis=0)

        # --- INFERENCE ---
        outputs = session.run(None, {input_name: input_tensor})
        output = np.transpose(outputs[0][0])

        # --- DETECTION PARSING ---
        raw_boxes = []
        raw_confs = []
        raw_classes = []

        scale_x = orig_w / 640.0
        scale_y = orig_h / 640.0

        for row in output:
            class_scores = row[4:]
            best_id = int(np.argmax(class_scores))
            score = float(class_scores[best_id])

            if score > CONF_THRESHOLD:
                cx, cy, w, h = row[0], row[1], row[2], row[3]
                x = int((cx - (w / 2)) * scale_x)
                y = int((cy - (h / 2)) * scale_y)
                box_w = int(w * scale_x)
                box_h = int(h * scale_y)

                raw_boxes.append([x, y, box_w, box_h])
                raw_confs.append(score)
                raw_classes.append(best_id)

        # NMS filtering
        indices = cv2.dnn.NMSBoxes(raw_boxes, raw_confs, CONF_THRESHOLD, IOU_THRESHOLD)

        nms_boxes = []
        nms_confs = []
        nms_classes = []
        if len(indices) > 0:
            for i in indices.flatten():
                nms_boxes.append(raw_boxes[i])
                nms_confs.append(raw_confs[i])
                nms_classes.append(raw_classes[i])

        # --- TEMPORAL SMOOTHING & TRACKING ---
        smoothed_detections = tracker.update(nms_boxes, nms_confs, nms_classes)

        # --- DRAW SMOOTHED BOXES ---
        for (x, y, w, h), conf, cls_id in smoothed_detections:
            label_name = class_names[cls_id] if cls_id < len(class_names) else f"Class {cls_id}"
            color = class_colors[cls_id] if cls_id < len(class_colors) else (0, 255, 0)
            label = f"{label_name} {conf * 100:.0f}%"

            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(frame, (x, max(0, y - text_h - 10)), (x + text_w, y), color, -1)
            cv2.putText(frame, label, (x, max(text_h, y - 5)), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

        # Overlay HUD
        cv2.putText(frame, f"FPS: {fps} | Cam: {cam_idx} ('C' to switch)", (20, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(frame, f"Threshold: {CONF_THRESHOLD:.2f} ([+] / [-])", (20, 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

        cv2.imshow(WINDOW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            break
        elif key == ord('c') or key == ord('C'):
            current_cam_pos = (current_cam_pos + 1) % len(cam_indices)
            new_cam_idx = cam_indices[current_cam_pos]
            print(f"\nSwitching to Camera Index {new_cam_idx}...")
            cap.release()
            cap = open_camera(new_cam_idx)
            if cap.isOpened():
                cam_idx = new_cam_idx
                print(f"Now using Camera Index {cam_idx}!")
        elif key == ord('+') or key == ord('='):
            CONF_THRESHOLD = min(0.95, CONF_THRESHOLD + 0.05)
            print(f"Threshold: {CONF_THRESHOLD:.2f}")
        elif key == ord('-') or key == ord('_'):
            CONF_THRESHOLD = max(0.10, CONF_THRESHOLD - 0.05)
            print(f"Threshold: {CONF_THRESHOLD:.2f}")

    cap.release()
    cv2.destroyAllWindows()
    print("Camera released. Application finished.")


if __name__ == "__main__":
    main()
