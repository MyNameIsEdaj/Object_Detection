"""The 'TV screen': live frame, comic-style boxes and POW! bursts."""
import math
import random
import time

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QFontMetricsF, QImage, QPainter, QPainterPath
from PySide6.QtWidgets import QSizePolicy, QWidget

from . import theme
from .widgets import draw_outlined_text, halftone_pixmap, ink_pen, starburst

BURST_SECONDS = 0.9
GLITTER_SECONDS = 1.4
GLITTER_COLORS = ["#FFFFFF", "#FFE680", "#FF9ED8", "#9EE6FF", "#C9A8FF", "#A8F0C6"]


def paint_detections(p, dets, scale, offset):
    """Draw comic boxes. dets: list of (box(x,y,w,h), conf, cls_id, name).

    scale/offset map frame pixels to the painter's coordinates; the same code
    draws on screen and on saved snapshots.
    """
    s = max(scale, 0.35)
    font = theme.display_font(max(14, 22 * s))
    fm = QFontMetricsF(font)
    for (x, y, w, h), conf, cls_id, name in dets:
        label, color = theme.class_style(name, cls_id)
        r = QRectF(offset.x() + x * scale, offset.y() + y * scale, w * scale, h * scale)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(ink_pen(9 * s))
        p.drawRoundedRect(r, theme.r(8) * s, theme.r(8) * s)
        p.setPen(ink_pen(5 * s, color))
        p.drawRoundedRect(r, theme.r(8) * s, theme.r(8) * s)

        text = f"{label} {conf * 100:.0f}%"
        tw, th = fm.horizontalAdvance(text) + 18 * s, fm.height() + 6 * s
        tag = QRectF(r.left() - 2 * s, r.top() - th - 4 * s, tw, th)
        view = p.clipBoundingRect() if p.hasClipping() else QRectF(offset, QPointF(1e6, 1e6))
        if tag.top() < view.top():
            tag.moveTop(max(r.top(), view.top()) + 4 * s)
        if tag.left() < view.left():
            tag.moveLeft(view.left() + 4 * s)
        if tag.right() > view.right():
            tag.moveRight(view.right() - 4 * s)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(theme.SHADOW)
        p.drawRoundedRect(tag.translated(3 * s, 3 * s), th / 2, th / 2)
        p.setBrush(color)
        p.setPen(ink_pen(3 * s))
        p.drawRoundedRect(tag, th / 2, th / 2)
        draw_outlined_text(p, tag, text, font, theme.WHITE, width=max(3, 4 * s))


class VideoView(QWidget):
    FRAME_PAD = 6  # border + gap around the picture, in px
    def __init__(self, parent=None):
        super().__init__(parent)
        self._image = None
        self._dets = []
        self._bursts = []   # comic: dicts text, x, y (frame px), t0, color
        self._glitter = []  # candy: dicts x, y (frame px), t0, particles
        self._frame_rect = QRectF()
        self._flash_until = 0.0
        dot = QColor(theme.WHITE)
        dot.setAlpha(22)
        self._idle_brush = QBrush(halftone_pixmap(dot, theme.SCREEN, step=14, radius=2))
        self.message = "PRESS START!"
        self.setMinimumSize(400, 260)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._tick)

    # ------------------------------------------------------------- API
    def set_frame(self, image, dets):
        self._image, self._dets = image, dets
        self.update()

    def clear(self, message="PRESS START!"):
        self._image, self._dets, self._bursts, self._glitter = None, [], [], []
        self.message = message
        self.update()

    def add_burst(self, x, y, color):
        if theme.NAME == "candy":
            self._add_glitter(x, y, color)
            return
        self._bursts.append({"text": random.choice(theme.EXCLAIMS), "x": x, "y": y,
                             "t0": time.monotonic(), "color": QColor(color),
                             "rot": random.uniform(-0.25, 0.25)})
        if not self._anim_timer.isActive():
            self._anim_timer.start(16)

    def _add_glitter(self, x, y, color):
        """Cute glitter shower: sparkles, hearts and dots popping out of the object."""
        colors = [QColor(c) for c in GLITTER_COLORS] + [QColor(color)] * 2
        particles = []
        for _ in range(34):
            kind = random.choices(("sparkle", "heart", "dot"), weights=(45, 22, 33))[0]
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(140, 380)  # frame px / s
            particles.append({
                "kind": kind, "vx": math.cos(angle) * speed, "vy": math.sin(angle) * speed - 60,
                "size": random.uniform(7, 15) if kind != "dot" else random.uniform(3, 6),
                "color": random.choice(colors), "spin": random.uniform(-4, 4),
                "phase": random.uniform(0, 6.3), "delay": random.uniform(0, 0.12),
            })
        self._glitter.append({"x": x, "y": y, "t0": time.monotonic(), "particles": particles})
        if not self._anim_timer.isActive():
            self._anim_timer.start(16)

    def flash(self):
        self._flash_until = time.monotonic() + 0.18
        if not self._anim_timer.isActive():
            self._anim_timer.start(16)

    def snapshot(self):
        """Current frame with comic boxes drawn at full resolution (no bursts)."""
        if self._image is None:
            return None
        img = self._image.convertToFormat(QImage.Format.Format_RGB32)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        paint_detections(p, self._dets, 1.0, QPointF(0, 0))
        p.end()
        return img

    # ----------------------------------------------------------- paint
    def _tick(self):
        now = time.monotonic()
        self._bursts = [b for b in self._bursts if now - b["t0"] < BURST_SECONDS]
        self._glitter = [g for g in self._glitter if now - g["t0"] < GLITTER_SECONDS + 0.15]
        if not self._bursts and not self._glitter and now > self._flash_until:
            self._anim_timer.stop()
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        outer = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        p.setPen(ink_pen(4))
        p.setBrush(self._idle_brush)
        p.drawRoundedRect(outer, theme.r(12), theme.r(12))

        if self._image is None:
            px = max(28, min(54, outer.width() / 11))
            draw_outlined_text(p, outer, self.message, theme.display_font(px), theme.PAPER, width=8)
            return

        iw, ih = self._image.width(), self._image.height()
        pad = self.FRAME_PAD - 2
        inner = outer.adjusted(pad, pad, -pad, -pad)
        # FILL: enlarge until the picture covers the whole screen area; the parts
        # that stick out are clipped (detection still uses the full frame).
        scale = max(inner.width() / iw, inner.height() / ih)
        w, h = iw * scale, ih * scale
        self._frame_rect = QRectF(inner.center().x() - w / 2, inner.center().y() - h / 2, w, h)
        clip = QPainterPath()
        clip.addRoundedRect(inner, theme.r(9), theme.r(9))
        p.save()
        p.setClipPath(clip)  # rounded corners like the border
        p.drawImage(self._frame_rect, self._image)
        paint_detections(p, self._dets, scale, self._frame_rect.topLeft())
        if time.monotonic() < self._flash_until:
            p.fillRect(inner, QColor(255, 255, 255, 170))
        p.restore()
        p.save()
        p.setClipRect(QRectF(self.rect()))
        self._paint_bursts(p, scale)  # bursts may pop out over the border
        self._paint_glitter(p, scale)
        p.restore()
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(ink_pen(4))
        p.drawRoundedRect(outer, theme.r(12), theme.r(12))

    def _paint_bursts(self, p, scale):
        now = time.monotonic()
        for b in self._bursts:
            k = (now - b["t0"]) / BURST_SECONDS
            grow = min(1.0, k / 0.25)
            size = (0.4 + 0.75 * grow) * (1.0 + 0.15 * (1 - abs(1 - grow)))
            c = QPointF(self._frame_rect.left() + b["x"] * scale,
                        self._frame_rect.top() + b["y"] * scale)
            r = 70 * size
            p.save()
            p.setOpacity(1.0 if k < 0.7 else max(0.0, (1 - k) / 0.3))
            p.setPen(ink_pen(4))
            n = theme.BURST_SPIKES
            inner = 0.6 if theme.NAME == "comic" else 0.72  # candy bursts are rounder
            p.setBrush(theme.SHADOW)
            p.drawPolygon(starburst(c + QPointF(5, 5), r, r * inner, n, b["rot"]))
            p.setBrush(b["color"])
            p.drawPolygon(starburst(c, r, r * inner, n, b["rot"]))
            p.setBrush(theme.PAPER)
            p.drawPolygon(starburst(c, r * 0.72, r * 0.72 * inner, n, b["rot"] + 0.1))
            draw_outlined_text(p, QRectF(c.x() - r, c.y() - r / 2, 2 * r, r),
                               b["text"], theme.display_font(30 * size), theme.RED, width=5)
            p.restore()

    # ------------------------------------------------------------ glitter
    @staticmethod
    def _sparkle_path(size):
        s, w = size, size * 0.24
        path = QPainterPath()
        path.moveTo(0, -s)
        for x, y in ((w, -w), (s, 0), (w, w), (0, s), (-w, w), (-s, 0), (-w, -w)):
            path.lineTo(x, y)
        path.closeSubpath()
        return path

    @staticmethod
    def _heart_path(size):
        s = size
        path = QPainterPath()
        path.moveTo(0, s * 0.85)
        path.cubicTo(-s * 1.2, s * 0.1, -s * 0.7, -s * 0.9, 0, -s * 0.3)
        path.cubicTo(s * 0.7, -s * 0.9, s * 1.2, s * 0.1, 0, s * 0.85)
        path.closeSubpath()
        return path

    def _paint_glitter(self, p, scale):
        now = time.monotonic()
        for g in self._glitter:
            age = now - g["t0"]
            c = QPointF(self._frame_rect.left() + g["x"] * scale,
                        self._frame_rect.top() + g["y"] * scale)
            if age < 0.45:  # soft ring popping outwards
                k = age / 0.45
                ring = QColor(theme.WHITE)
                ring.setAlphaF(0.85 * (1 - k))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(ink_pen(5 * (1 - k) + 1, ring))
                p.drawEllipse(c, 18 + 70 * k, 18 + 70 * k)
            for pt in g["particles"]:
                t = age - pt["delay"]
                if t <= 0 or t > GLITTER_SECONDS:
                    continue
                drift = (1 - math.exp(-3 * t)) / 3          # fast pop, then slows down
                fx = g["x"] + pt["vx"] * drift
                fy = g["y"] + pt["vy"] * drift + 70 * t * t  # glitter drifts down
                pos = QPointF(self._frame_rect.left() + fx * scale,
                              self._frame_rect.top() + fy * scale)
                twinkle = 1 + 0.35 * math.sin(t * 22 + pt["phase"])
                alpha = 1.0 if t < GLITTER_SECONDS * 0.55 else \
                    max(0.0, (GLITTER_SECONDS - t) / (GLITTER_SECONDS * 0.45))
                p.save()
                p.translate(pos)
                p.rotate(math.degrees(pt["spin"] * t))
                p.setOpacity(alpha)
                size = pt["size"] * twinkle
                if pt["kind"] == "sparkle":
                    p.setPen(ink_pen(1.6))
                    p.setBrush(pt["color"])
                    p.drawPath(self._sparkle_path(size))
                elif pt["kind"] == "heart":
                    p.setPen(ink_pen(1.6))
                    p.setBrush(pt["color"])
                    p.drawPath(self._heart_path(size * 0.8))
                else:
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(pt["color"])
                    p.drawEllipse(QPointF(0, 0), size, size)
                    p.setBrush(theme.WHITE)
                    p.drawEllipse(QPointF(-size * 0.3, -size * 0.3), size * 0.35, size * 0.35)
                p.restore()
