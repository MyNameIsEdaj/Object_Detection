"""
Real-Time Multi-Object Detection using ONNX Runtime & OpenCV
Supports dynamic classes (marker, watch, can, water bottle, eye glasses)
"""
import cv2
import numpy as np
import onnxruntime as ort
import os
import time


def main():
    base_dir = os.path.dirname(__file__)
    # Prefer 5-object model if available, fallback to marker detector
    model_path = os.path.join(base_dir, "5_objects_detector.onnx")
    if not os.path.exists(model_path):
        model_path = os.path.join(base_dir, "marker_detector.onnx")

    if not os.path.exists(model_path):
        print(f"Error: No ONNX model found in '{base_dir}'!")
        return

    print("Loading ONNX model...")
    session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
    input_name = session.get_inputs()[0].name
    out_shape = session.get_outputs()[0].shape  # e.g., [1, 9, 8400] or [1, 5, 8400]
    num_classes = out_shape[1] - 4

    # Class definitions with distinctive colors (BGR)
    all_classes = [
        ("Marker", (0, 255, 0)),       # Green
        ("Watch", (255, 255, 0)),       # Cyan
        ("Can", (0, 140, 255)),         # Orange
        ("Water Bottle", (255, 120, 0)),# Blue
        ("Eye Glasses", (255, 0, 255))  # Magenta
    ]

    class_names = [c[0] for c in all_classes[:num_classes]]
    class_colors = [c[1] for c in all_classes[:num_classes]]

    # Open webcam with DirectShow for native Windows compatibility
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not access the webcam.")
        return

    CONF_THRESHOLD = 0.40  # Minimum detection confidence
    IOU_THRESHOLD = 0.45   # Non-Maximum Suppression overlap threshold

    print("=" * 65)
    print("      LIVE MULTI-OBJECT DETECTION RUNNING")
    print("=" * 65)
    print(f"Model: {os.path.basename(model_path)}")
    print(f"Detected Classes ({num_classes}): {', '.join(class_names)}")
    print("\nControls:")
    print("  [+] or [=] : Increase confidence threshold")
    print("  [-]        : Decrease confidence threshold")
    print("  [Q] or ESC : Exit")
    print("=" * 65)

    prev_time = time.time()
    fps = 0
    fail_count = 0

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            fail_count += 1
            if fail_count > 10:
                print("Camera feed lost. Exiting.")
                break
            time.sleep(0.05)
            continue
        fail_count = 0

        orig_h, orig_w = frame.shape[:2]

        curr_time = time.time()
        fps = int(1.0 / (curr_time - prev_time)) if (curr_time - prev_time) > 0 else fps
        prev_time = curr_time

        # --- STEP 1: PREPROCESSING ---
        rgb_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb_img, (640, 640))
        input_data = resized.astype(np.float32) / 255.0
        input_data = np.transpose(input_data, (2, 0, 1))
        input_tensor = np.expand_dims(input_data, axis=0)

        # --- STEP 2: INFERENCE ---
        outputs = session.run(None, {input_name: input_tensor})
        output = outputs[0][0]         # Shape: [num_channels, 8400]
        output = np.transpose(output)  # Shape: [8400, num_channels]

        # --- STEP 3: PARSE DETECTIONS ---
        boxes = []
        confidences = []
        class_ids = []

        scale_x = orig_w / 640.0
        scale_y = orig_h / 640.0

        for row in output:
            cx, cy, w, h = row[0], row[1], row[2], row[3]
            class_scores = row[4:]
            best_class_id = int(np.argmax(class_scores))
            score = float(class_scores[best_class_id])

            if score > CONF_THRESHOLD:
                x = int((cx - (w / 2)) * scale_x)
                y = int((cy - (h / 2)) * scale_y)
                box_w = int(w * scale_x)
                box_h = int(h * scale_y)

                boxes.append([x, y, box_w, box_h])
                confidences.append(score)
                class_ids.append(best_class_id)

        # --- STEP 4: NON-MAXIMUM SUPPRESSION ---
        indices = cv2.dnn.NMSBoxes(boxes, confidences, CONF_THRESHOLD, IOU_THRESHOLD)

        # --- STEP 5: DRAW BOUNDING BOXES ---
        if len(indices) > 0:
            for i in indices.flatten():
                x, y, w, h = boxes[i]
                conf = confidences[i]
                cls_id = class_ids[i]
                label_name = class_names[cls_id] if cls_id < len(class_names) else f"Class {cls_id}"
                color = class_colors[cls_id] if cls_id < len(class_colors) else (0, 255, 0)
                label = f"{label_name} {conf * 100:.1f}%"

                # Draw bounding box
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)

                # Draw label background tag
                (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                cv2.rectangle(frame, (x, max(0, y - text_h - 10)), (x + text_w, y), color, -1)
                cv2.putText(frame, label, (x, max(text_h, y - 5)), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

        # Overlay HUD
        cv2.putText(frame, f"FPS: {fps}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(frame, f"Threshold: {CONF_THRESHOLD:.2f} ([+] / [-])", (20, 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

        cv2.imshow("Multi-Object Detection", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            break
        elif key == ord('+') or key == ord('='):
            CONF_THRESHOLD = min(0.95, CONF_THRESHOLD + 0.05)
            print(f"Confidence threshold: {CONF_THRESHOLD:.2f}")
        elif key == ord('-') or key == ord('_'):
            CONF_THRESHOLD = max(0.10, CONF_THRESHOLD - 0.05)
            print(f"Confidence threshold: {CONF_THRESHOLD:.2f}")

    cap.release()
    cv2.destroyAllWindows()
    print("Webcam closed.")


if __name__ == "__main__":
    main()
