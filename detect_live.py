"""
Real-time webcam detection for the 5 objects:
Can, Glasses, Marker, Watch, Water Bottle.

Controls:
  [C]        switch camera
  [+] / [=]  raise confidence threshold
  [-]        lower confidence threshold
  [Q] / ESC  quit (closing the window also quits)

Usage:
  uv run python detect_live.py [--model PATH] [--conf 0.25] [--cpu]
"""
import argparse
import sys
import time

import cv2

from core import CameraManager, DEFAULT_MODEL_PATH, ObjectTracker, YoloOnnxDetector, draw_detections

WINDOW_NAME = "Multi-Object Detection"
MAX_READ_FAILURES = 20


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Live webcam object detection")
    p.add_argument("--model", default=str(DEFAULT_MODEL_PATH), help="path to the .onnx model")
    p.add_argument("--conf", type=float, default=0.25, help="starting confidence threshold")
    p.add_argument("--iou", type=float, default=0.45, help="NMS IoU threshold")
    p.add_argument("--cpu", action="store_true", help="force CPU even if a GPU is available")
    return p.parse_args(argv)


def draw_hud(frame, fps, device, cam_idx, conf):
    cv2.putText(frame, f"FPS: {fps:.0f} | {device} | Cam: {cam_idx} ('C' to switch)",
                (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    cv2.putText(frame, f"Threshold: {conf:.2f} ([+] / [-])",
                (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)


def main(argv=None):
    args = parse_args(argv)

    try:
        detector = YoloOnnxDetector(args.model, conf_threshold=args.conf,
                                    iou_threshold=args.iou, prefer_gpu=not args.cpu)
    except Exception as e:  # missing / corrupt model file
        print(f"Error: could not load model '{args.model}':\n  {e}")
        return 1

    camera = CameraManager()
    if not camera.open_first_available():
        print("Error: could not open any camera. Close the Windows Camera app / Zoom and retry.")
        return 1

    tracker = ObjectTracker(alpha=0.6, max_missed_frames=5)

    print("=" * 65)
    print("      LIVE MULTI-OBJECT DETECTION")
    print("=" * 65)
    print(f"Model   : {args.model}")
    print(f"Device  : {detector.device_label}")
    print(f"Camera  : index {camera.index}")
    print(f"Classes : {', '.join(detector.class_names)}")
    print("Keys    : C = camera | +/- = threshold | Q/ESC = quit")
    print("=" * 65)

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_AUTOSIZE)
    prev_time, fps, failures = time.perf_counter(), 0.0, 0

    try:
        while True:
            ok, frame = camera.read()
            if not ok or frame is None:
                failures += 1
                if failures > MAX_READ_FAILURES:
                    print("Camera feed lost. Exiting.")
                    break
                time.sleep(0.05)
                continue
            failures = 0

            now = time.perf_counter()
            dt = now - prev_time
            prev_time = now
            if dt > 0:  # smoothed FPS so the number doesn't flicker
                fps = 0.9 * fps + 0.1 * (1.0 / dt) if fps else 1.0 / dt

            detections = tracker.update(detector.detect(frame))
            draw_detections(frame, detections)
            draw_hud(frame, fps, detector.device_label, camera.index, detector.conf_threshold)
            cv2.imshow(WINDOW_NAME, frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):
                break
            if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                break  # window closed with the X button
            if key in (ord("c"), ord("C")):
                print("Switching camera...")
                if camera.switch_next():
                    tracker.reset()
                    print(f"Now using camera index {camera.index}")
                else:
                    print("No other camera found; staying on the current one.")
            elif key in (ord("+"), ord("=")):
                detector.conf_threshold = min(0.95, detector.conf_threshold + 0.05)
                print(f"Threshold: {detector.conf_threshold:.2f}")
            elif key in (ord("-"), ord("_")):
                detector.conf_threshold = max(0.05, detector.conf_threshold - 0.05)
                print(f"Threshold: {detector.conf_threshold:.2f}")
    finally:
        camera.release()
        cv2.destroyAllWindows()

    print("Camera released. Application finished.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
