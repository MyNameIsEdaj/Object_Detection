"""Object tracking so boxes stay on objects while they move.

How it keeps following a moving object (ideas from the ByteTrack tracker):

1. Motion prediction - each track remembers its velocity, so it is matched
   against where the object *should* be this frame, not where it was.
2. Low-confidence rescue - when an object moves, motion blur makes the model
   less sure (e.g. 0.12 instead of 0.60). Those weak detections are normally
   thrown away. Here they are allowed to *continue* an existing track, but
   never to start a new one, so they don't add false boxes.
3. Coasting - if the object is missed completely for a few frames, the box
   keeps moving along its last velocity instead of freezing or vanishing.
4. Class voting - the label is a running vote over recent frames, so a can
   that is briefly read as "water bottle" doesn't flicker its label.
5. Confirmation - a new track needs 2 hits (or one very confident one) before
   it is shown, which hides one-frame false positives.
"""
from collections import defaultdict

from .detector import Detection


def iou_xywh(a, b):
    xa, ya = max(a[0], b[0]), max(a[1], b[1])
    xb, yb = min(a[0] + a[2], b[0] + b[2]), min(a[1] + a[3], b[1] + b[3])
    inter = max(0.0, xb - xa) * max(0.0, yb - ya)
    union = a[2] * a[3] + b[2] * b[3] - inter
    return inter / union if union > 0 else 0.0


def center_distance_ratio(a, b):
    """Distance between box centres, relative to the size of box a."""
    dx = (a[0] + a[2] / 2) - (b[0] + b[2] / 2)
    dy = (a[1] + a[3] / 2) - (b[1] + b[3] / 2)
    size = max(a[2], a[3], 1.0)
    return (dx * dx + dy * dy) ** 0.5 / size


class _Track:
    def __init__(self, det, track_id):
        self.id = track_id
        self.box = [float(v) for v in det.box]
        self.vx = self.vy = 0.0
        self.conf = det.conf
        self.votes = defaultdict(float)
        self.votes[det.cls_id] += det.conf
        self.labels = {det.cls_id: det.label}
        self.hits = 1
        self.missed = 0

    def predicted_box(self):
        x, y, w, h = self.box
        return [x + self.vx, y + self.vy, w, h]

    def update(self, det, alpha, vel_alpha):
        px, py = self.box[0] + self.box[2] / 2, self.box[1] + self.box[3] / 2
        pred = self.predicted_box()
        self.box = [alpha * n + (1 - alpha) * p for n, p in zip(det.box, pred)]
        nx, ny = self.box[0] + self.box[2] / 2, self.box[1] + self.box[3] / 2
        self.vx = vel_alpha * (nx - px) + (1 - vel_alpha) * self.vx
        self.vy = vel_alpha * (ny - py) + (1 - vel_alpha) * self.vy
        self.conf = alpha * det.conf + (1 - alpha) * self.conf
        for k in self.votes:
            self.votes[k] *= 0.85  # older votes fade
        self.votes[det.cls_id] += det.conf
        self.labels[det.cls_id] = det.label
        self.hits += 1
        self.missed = 0

    def coast(self):
        self.box = self.predicted_box()
        self.vx *= 0.7
        self.vy *= 0.7
        self.conf *= 0.9
        self.missed += 1

    @property
    def cls_id(self):
        return max(self.votes, key=self.votes.get)

    def to_detection(self):
        cid = self.cls_id
        return Detection(tuple(int(round(v)) for v in self.box),
                         float(self.conf), cid, self.labels[cid])


class ObjectTracker:
    """
    high_conf:         detections at or above this can start new tracks
                       (pass the detector's current threshold each frame)
    low_conf:          weakest detection allowed to continue an existing track;
                       call the detector with this threshold
    alpha:             box smoothing (higher = follows faster, lower = smoother)
    max_missed_frames: how long a lost object keeps coasting before removal
    min_hits:          hits needed before a new track is shown
    """

    def __init__(self, low_conf=0.10, alpha=0.7, velocity_alpha=0.5,
                 max_missed_frames=8, min_hits=2, instant_show_conf=0.6,
                 match_iou=0.2, low_match_iou=0.3, max_center_jump=0.8):
        self.low_conf = low_conf
        self.alpha = alpha
        self.velocity_alpha = velocity_alpha
        self.max_missed = max_missed_frames
        self.min_hits = min_hits
        self.instant_show_conf = instant_show_conf
        self.match_iou = match_iou
        self.low_match_iou = low_match_iou
        self.max_center_jump = max_center_jump
        self.tracks = []
        self._next_id = 1

    def reset(self):
        self.tracks = []

    def update(self, detections, high_conf=0.25):
        high = [d for d in detections if d.conf >= high_conf]
        low = [d for d in detections if self.low_conf <= d.conf < high_conf]

        # Stage 1: confident detections vs all tracks (IoU or a short centre jump)
        unmatched_tracks, unmatched_high = self._associate(
            self.tracks, high, self.match_iou, allow_jump=True)
        # Stage 2: weak detections may only continue tracks that are still unmatched
        still_unmatched, _ = self._associate(
            unmatched_tracks, low, self.low_match_iou, allow_jump=False)

        for t in still_unmatched:
            t.coast()
        self.tracks = [t for t in self.tracks if t.missed <= self.max_missed]

        for d in unmatched_high:  # only confident detections start tracks
            self.tracks.append(_Track(d, self._next_id))
            self._next_id += 1

        return [t.to_detection() for t in self.tracks
                if t.hits >= self.min_hits or t.conf >= self.instant_show_conf]

    def _associate(self, tracks, dets, min_iou, allow_jump):
        """Greedy best-first matching. Returns (unmatched tracks, unmatched dets)."""
        pairs = []
        for ti, t in enumerate(tracks):
            pred = t.predicted_box()
            for di, d in enumerate(dets):
                iou = iou_xywh(pred, d.box)
                score = iou
                if iou < min_iou:
                    if not allow_jump:
                        continue
                    jump = center_distance_ratio(pred, d.box)
                    if jump > self.max_center_jump:
                        continue
                    score = 0.01 * (1 - jump / self.max_center_jump)  # rank below IoU matches
                if d.cls_id == t.cls_id:
                    score += 0.05  # prefer same class, but don't require it
                pairs.append((score, ti, di))

        used_t, used_d = set(), set()
        for _, ti, di in sorted(pairs, reverse=True):
            if ti in used_t or di in used_d:
                continue
            tracks[ti].update(dets[di], self.alpha, self.velocity_alpha)
            used_t.add(ti)
            used_d.add(di)

        return ([t for i, t in enumerate(tracks) if i not in used_t],
                [d for i, d in enumerate(dets) if i not in used_d])
