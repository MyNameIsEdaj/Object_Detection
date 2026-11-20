"""Webcam helpers shared by the collector, the live detector and (later) the GUI."""
import sys

import cv2

from .config import CAMERA_INDICES


def open_camera(index):
    """Open a camera by index. On Windows DirectShow is tried first (faster startup)."""
    if sys.platform.startswith("win"):
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if cap.isOpened():
            return cap
        cap.release()
    return cv2.VideoCapture(index)


class CameraManager:
    """Owns the active camera and cycles through a list of camera indices.

    Unlike the old inline code, a failed switch never leaves you with a dead
    camera: it tries every other index and falls back to the one that worked.
    """

    def __init__(self, indices=CAMERA_INDICES):
        self.indices = list(indices)
        self._pos = 0
        self.cap = None

    @property
    def index(self):
        return self.indices[self._pos]

    def is_open(self):
        return self.cap is not None and self.cap.isOpened()

    def open_first_available(self):
        """Open the first index in the list that works. Returns True on success."""
        for pos in range(len(self.indices)):
            if self._try_open(pos):
                return True
        return False

    def switch_next(self):
        """Switch to the next working camera. Returns True if the camera changed."""
        old_pos = self._pos
        self.release()
        for step in range(1, len(self.indices)):
            if self._try_open((old_pos + step) % len(self.indices)):
                return True
        # Nothing else worked: reopen the camera we had.
        self._try_open(old_pos)
        return False

    def read(self):
        if not self.is_open():
            return False, None
        return self.cap.read()

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def _try_open(self, pos):
        cap = open_camera(self.indices[pos])
        if cap.isOpened():
            self.cap = cap
            self._pos = pos
            return True
        cap.release()
        return False
