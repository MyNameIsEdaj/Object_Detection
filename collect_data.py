"""
Webcam photo collector for building the training set.

Photos are saved to datasets/my_raw_photos/<class>/<class>_0001.jpg, ready to
upload to Roboflow for labelling.

Controls:
  [0]        NEGATIVE (empty hands, desk, wall - no target objects)
  [1]-[5]    Marker, Watch, Can, Water Bottle, Eye Glasses
  [C]        switch camera
  [SPACE]    take one photo
  [A]        toggle auto-capture (one photo every AUTO_INTERVAL seconds)
  [Q] / ESC  finish (closing the window also finishes)
"""
import re
import time

import cv2

from core import CameraManager, RAW_PHOTOS_DIR

CLASSES = ["negative", "marker", "watch", "can", "water_bottle", "eye_glasses"]
AUTO_INTERVAL = 0.6  # seconds between auto-captured photos
WINDOW_NAME = "Webcam Dataset Collector"


def next_photo_number(folder, class_name):
    """Highest existing number + 1.

    The old code used "number of files + 1", which overwrote an existing photo
    whenever you had deleted a bad shot from the middle of the sequence.
    """
    pattern = re.compile(rf"^{re.escape(class_name)}_(\d+)\.jpg$", re.IGNORECASE)
    numbers = [int(m.group(1)) for f in folder.iterdir() if (m := pattern.match(f.name))]
    return max(numbers, default=0) + 1


def count_photos(folder):
    return sum(1 for f in folder.iterdir() if f.suffix.lower() == ".jpg")


def save_photo(frame, folder, class_name, number):
    path = folder / f"{class_name}_{number:04d}.jpg"
    # imencode + write_bytes also works for folder paths with non-ASCII characters
    ok, buf = cv2.imencode(".jpg", frame)
    if ok:
        path.write_bytes(buf.tobytes())
    return path if ok else None


def draw_overlay(frame, class_idx, count, cam_idx, auto_on):
    h, w = frame.shape[:2]
    name = CLASSES[class_idx]
    tag = "0 (NEGATIVE)" if class_idx == 0 else str(class_idx)

    cv2.rectangle(frame, (0, 0), (w, 85), (20, 20, 20), -1)
    cv2.putText(frame, f"[{tag}] {name.upper()} ({count} photos) | Camera: {cam_idx}",
                (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
    status = "AUTO: ON (move / rotate the object)" if auto_on else "AUTO: OFF (press 'A')"
    cv2.putText(frame, status, (15, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                (0, 255, 0) if auto_on else (180, 180, 180), 2)

    cv2.rectangle(frame, (0, h - 35), (w, h), (20, 20, 20), -1)
    cv2.putText(frame, "0: Negative | 1-5: Object | C: Camera | SPACE: Photo | A: Auto | Q: Exit",
                (15, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 220, 220), 1)


def main():
    folders = {c: RAW_PHOTOS_DIR / c for c in CLASSES}
    for folder in folders.values():
        folder.mkdir(parents=True, exist_ok=True)

    camera = CameraManager()
    if not camera.open_first_available():
        print("=" * 65)
        print("ERROR: Could not open a camera.")
        print("1. Close the Windows Camera app / Zoom if they are open.")
        print("2. Unplug and re-plug the USB webcam.")
        print("=" * 65)
        return

    class_idx = 1  # start on Marker
    auto_on = False
    last_auto = 0.0
    counts = {c: count_photos(folders[c]) for c in CLASSES}
    next_num = {c: next_photo_number(folders[c], c) for c in CLASSES}

    print(__doc__)
    print(f"Saving to: {RAW_PHOTOS_DIR}")
    print(f"Camera   : index {camera.index}")
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_AUTOSIZE)

    def capture(frame):
        name = CLASSES[class_idx]
        path = save_photo(frame, folders[name], name, next_num[name])
        if path:
            next_num[name] += 1
            counts[name] += 1
            print(f"Captured [{name}]: {path.name} (total {counts[name]})")
        else:
            print("Warning: failed to save photo.")

    try:
        while True:
            ok, frame = camera.read()
            if not ok or frame is None:
                time.sleep(0.05)
                continue

            now = time.time()
            if auto_on and now - last_auto >= AUTO_INTERVAL:
                capture(frame)
                last_auto = now

            display = frame.copy()
            draw_overlay(display, class_idx, counts[CLASSES[class_idx]], camera.index, auto_on)
            cv2.imshow(WINDOW_NAME, display)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):
                break
            if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                break
            if key in (ord("c"), ord("C")):
                auto_on = False
                print("Switching camera...")
                if camera.switch_next():
                    print(f"Now using camera index {camera.index}")
                else:
                    print("No other camera found; staying on the current one.")
            elif ord("0") <= key <= ord("5"):
                class_idx = key - ord("0")
                auto_on = False
                print(f"\nSwitched to: [{CLASSES[class_idx].upper()}]")
            elif key == 32:  # SPACE
                capture(frame)
            elif key in (ord("a"), ord("A")):
                auto_on = not auto_on
                last_auto = now
                print(f"Auto-capture {'ON' if auto_on else 'OFF'} for {CLASSES[class_idx]}")
    finally:
        camera.release()
        cv2.destroyAllWindows()

    print("\n" + "=" * 65)
    print("DATA COLLECTION SUMMARY")
    for c in CLASSES:
        print(f"  {c.upper():<15}: {count_photos(folders[c]):>4} photos  ({folders[c]})")
    print("=" * 65)


if __name__ == "__main__":
    main()
