"""Drawing helpers for boxes and labels (BGR colours)."""
import cv2

CLASS_COLORS = {
    "can": (0, 140, 255),            # orange
    "glasses": (255, 0, 255),        # magenta
    "marker": (0, 255, 0),           # green
    "watch": (255, 255, 0),          # cyan
    "water bottle": (255, 120, 0),   # blue
}
FALLBACK_COLORS = [(0, 200, 255), (200, 0, 200), (0, 200, 120), (200, 200, 0)]


def color_for(label, cls_id=0):
    return CLASS_COLORS.get(label.lower(),
                            FALLBACK_COLORS[cls_id % len(FALLBACK_COLORS)])


def draw_detections(frame, detections):
    """Draw boxes + "Label 87%" tags onto the frame in place."""
    for det in detections:
        x, y, w, h = det.box
        color = color_for(det.label, det.cls_id)
        text = f"{det.label.title()} {det.conf * 100:.0f}%"

        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        top = max(0, y - th - 10)
        cv2.rectangle(frame, (x, top), (x + tw, top + th + 10), color, -1)
        cv2.putText(frame, text, (x, top + th + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    return frame
