"""Background thread: camera -> detector -> frames for the window.

Running detection here keeps the window responsive. Settings (confidence,
tracking, camera) are plain attributes the window sets; the loop reads them
every frame.
"""
import time

import cv2
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

from core import CameraManager, LiveDetector, YoloOnnxDetector

MAX_READ_FAILURES = 30


class DetectionWorker(QThread):
    frame_ready = Signal(QImage, list, dict)   # image, detections, stats
    model_ready = Signal(list, str)            # class names, device label
    camera_changed = Signal(int, bool)         # index now in use, request succeeded
    failed = Signal(str)                       # fatal error message

    def __init__(self, model_path, camera_index, conf, use_tracking, parent=None):
        super().__init__(parent)
        self.model_path = str(model_path)
        self.conf = conf
        self.use_tracking = use_tracking
        self._camera_index = camera_index
        self._pending_camera = None
        self._running = False

    def request_camera(self, index):
        self._pending_camera = index

    def stop(self):
        self._running = False

    def run(self):
        self._running = True
        try:
            detector = YoloOnnxDetector(self.model_path, conf_threshold=self.conf)
        except Exception as e:  # missing or broken model file
            self.failed.emit(f"Couldn't load the model:\n{self.model_path}\n\n{e}")
            return
        self.model_ready.emit(list(detector.class_names), detector.device_label)
        live = LiveDetector(detector)

        camera = CameraManager(resolution=(1280, 720))  # widescreen fills the panel better
        if camera.open_index(self._camera_index):
            self.camera_changed.emit(camera.index, True)
        elif camera.open_first_available():
            self.camera_changed.emit(camera.index, False)
        else:
            self.failed.emit("No camera found. Close the Camera app or Zoom, "
                             "check the USB cable, and try again.")
            return

        fps, last, failures = 0.0, time.perf_counter(), 0
        try:
            while self._running:
                if self._pending_camera is not None:
                    wanted, self._pending_camera = self._pending_camera, None
                    ok = camera.open_index(wanted)
                    live.reset()
                    self.camera_changed.emit(camera.index, ok)

                live.conf_threshold = self.conf
                live.use_tracking = self.use_tracking

                ok, frame = camera.read()
                if not ok or frame is None:
                    failures += 1
                    if failures > MAX_READ_FAILURES:
                        self.failed.emit("The camera stopped sending pictures.")
                        break
                    time.sleep(0.03)
                    continue
                failures = 0

                t0 = time.perf_counter()
                dets = live.process(frame)
                infer_ms = (time.perf_counter() - t0) * 1000

                now = time.perf_counter()
                dt, last = now - last, now
                if dt > 0:
                    fps = 0.9 * fps + 0.1 / dt if fps else 1 / dt

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w = rgb.shape[:2]
                image = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()
                self.frame_ready.emit(
                    image,
                    [(d.box, d.conf, d.cls_id, d.label) for d in dets],
                    {"fps": fps, "infer_ms": infer_ms},
                )
        finally:
            camera.release()
