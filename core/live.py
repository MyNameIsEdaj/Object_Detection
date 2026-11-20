"""Detector + optional tracker for live video, shared by the CLI and the GUI."""
from .tracker import ObjectTracker


class LiveDetector:
    """One call per frame: returns the detections to show.

    With tracking on, weak detections are fetched too so the tracker can keep
    following moving (blurred) objects; with it off you see the raw model output.
    """

    def __init__(self, detector, tracker=None):
        self.detector = detector
        self.tracker = tracker or ObjectTracker()
        self._use_tracking = True

    @property
    def use_tracking(self):
        return self._use_tracking

    @use_tracking.setter
    def use_tracking(self, value):
        value = bool(value)
        if value and not self._use_tracking:
            self.tracker.reset()  # don't resume stale tracks
        self._use_tracking = value

    @property
    def conf_threshold(self):
        return self.detector.conf_threshold

    @conf_threshold.setter
    def conf_threshold(self, value):
        self.detector.conf_threshold = float(value)

    def reset(self):
        self.tracker.reset()

    def process(self, frame):
        if not self._use_tracking:
            return self.detector.detect(frame)
        raw = self.detector.detect(
            frame, conf_threshold=min(self.tracker.low_conf, self.detector.conf_threshold))
        return self.tracker.update(raw, high_conf=self.detector.conf_threshold)
