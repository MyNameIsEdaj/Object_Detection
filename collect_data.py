"""
Interactive Webcam Dataset Collector
Captures training photos for 5 custom objects:
  [1] Marker
  [2] Watch
  [3] Can
  [4] Water Bottle
  [5] Eye Glasses
Includes camera switcher key [C] to cycle between laptop & A4Tech webcams.
"""
import cv2
import numpy as np
import os
import time


def open_camera(cam_idx):
    """Tries to open a camera index using DirectShow first, then default."""
    cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(cam_idx)
    return cap


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_root = os.path.join(base_dir, "datasets", "my_raw_photos")

    classes = [
        "marker",
        "watch",
        "can",
        "water_bottle",
        "eye_glasses"
    ]

    for cls in classes:
        os.makedirs(os.path.join(output_root, cls), exist_ok=True)

    # Available camera indices to cycle through
    cam_indices = [1, 0, 2]  # Try external camera (1) first, then laptop (0)
    current_cam_pos = 0
    cam_idx = cam_indices[current_cam_pos]

    cap = open_camera(cam_idx)
    if not cap.isOpened():
        # Fallback to index 0
        current_cam_pos = 1
        cam_idx = cam_indices[current_cam_pos]
        cap = open_camera(cam_idx)

    if not cap.isOpened():
        print("=" * 65)
        print("ERROR: Could not open camera.")
        print("1. If Windows Camera app or Zoom is open, please CLOSE it.")
        print("2. Unplug and re-plug your A4Tech USB cable.")
        print("=" * 65)
        return

    current_idx = 0
    auto_capture = False
    last_auto_time = 0
    auto_interval = 0.6
    WINDOW_NAME = "Webcam Dataset Collector - 5 Objects"

    print("=" * 65)
    print("      INTERACTIVE WEBCAM DATASET COLLECTOR")
    print("=" * 65)
    print(f"Current Camera: Index {cam_idx}")
    print("\nControls:")
    print("  [C]          : Switch Camera (Cycles through Camera 0, 1, 2)")
    print("  [1] to [5]   : Switch object category")
    print("  [SPACEBAR]   : Capture 1 photo")
    print("  [A]          : Toggle Auto-Capture mode")
    print("  [Q] or [X]   : Save & Finish")
    print("=" * 65)

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_AUTOSIZE)

    while True:
        if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
            print("\nCollector closed by user.")
            break

        ret, frame = cap.read()
        if not ret or frame is None:
            time.sleep(0.05)
            continue

        display = frame.copy()
        current_class = classes[current_idx]
        current_folder = os.path.join(output_root, current_class)
        existing_count = len([f for f in os.listdir(current_folder) if f.endswith('.jpg')])

        now = time.time()
        if auto_capture and (now - last_auto_time >= auto_interval):
            existing_count += 1
            filename = f"{current_class}_{existing_count:04d}.jpg"
            filepath = os.path.join(current_folder, filename)
            cv2.imwrite(filepath, frame)
            last_auto_time = now
            print(f"Captured [{current_class}]: {filename} (Total: {existing_count})")

        h, w = display.shape[:2]

        # Top banner
        cv2.rectangle(display, (0, 0), (w, 85), (20, 20, 20), -1)
        cls_text = f"[{current_idx + 1}] {current_class.upper()} ({existing_count} photos) | Camera: {cam_idx} (Press 'C' to switch)"
        cv2.putText(display, cls_text, (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)

        status_text = "AUTO: ON (Rotate item)" if auto_capture else "AUTO: OFF (Press 'A' to start)"
        status_color = (0, 255, 0) if auto_capture else (180, 180, 180)
        cv2.putText(display, status_text, (15, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.65, status_color, 2)

        # Bottom instructions
        cv2.rectangle(display, (0, h - 35), (w, h), (20, 20, 20), -1)
        help_text = "Press 1-5: object | C: switch camera | SPACE: photo | A: auto | Q: exit"
        cv2.putText(display, help_text, (15, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (220, 220, 220), 1)

        cv2.imshow(WINDOW_NAME, display)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            break
        elif key == ord('c') or key == ord('C'):
            # Cycle to next camera index
            current_cam_pos = (current_cam_pos + 1) % len(cam_indices)
            new_cam_idx = cam_indices[current_cam_pos]
            print(f"\nSwitching to Camera Index {new_cam_idx}...")
            cap.release()
            cap = open_camera(new_cam_idx)
            if cap.isOpened():
                cam_idx = new_cam_idx
                print(f"Now using Camera Index {cam_idx}!")
            else:
                print(f"Could not open Camera Index {new_cam_idx}. Trying next...")
        elif key in [ord('1'), ord('2'), ord('3'), ord('4'), ord('5')]:
            current_idx = int(chr(key)) - 1
            auto_capture = False
            print(f"\nSwitched to: [{classes[current_idx].upper()}]")
        elif key == 32:  # SPACEBAR
            existing_count += 1
            filename = f"{current_class}_{existing_count:04d}.jpg"
            filepath = os.path.join(current_folder, filename)
            cv2.imwrite(filepath, frame)
            print(f"Captured [{current_class}]: {filename} (Total: {existing_count})")
        elif key == ord('a') or key == ord('A'):
            auto_capture = not auto_capture
            last_auto_time = now
            print(f"Auto-capture is now {'ENABLED' if auto_capture else 'DISABLED'} for {current_class}")

    cap.release()
    cv2.destroyAllWindows()
    print("\n" + "=" * 65)
    print("DATA COLLECTION SUMMARY:")
    for c in classes:
        folder = os.path.join(output_root, c)
        cnt = len([f for f in os.listdir(folder) if f.endswith('.jpg')])
        print(f"  {c.upper():<15}: {cnt:>3} photos saved in {folder}")
    print("=" * 65)


if __name__ == "__main__":
    main()
