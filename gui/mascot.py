"""The mascot: a chicken (comic theme) or a gummy bear (candy theme).
Sleeps, watches, or gets excited."""
import math
import random
import time

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPolygonF
from PySide6.QtWidgets import QWidget

from . import theme
from .bear import draw_bear
from .widgets import draw_outlined_text, ink_pen


class Mascot(QWidget):
    SLEEP, IDLE, EXCITED = "sleep", "idle", "excited"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mood = self.SLEEP
        self._excited_until = 0.0
        self._next_blink = time.monotonic() + 2
        self._blink_until = 0.0
        self._t0 = time.monotonic()
        self._feathers = []  # (start time, x, y, vx, vy, spin)
        self.setFixedSize(QSize(100, 100))
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(33)

    def set_mood(self, mood):
        now = time.monotonic()
        if mood == self.EXCITED:
            self._excited_until = now + 1.4
            for _ in range(5):  # a puff of feathers
                self._feathers.append((now, random.uniform(40, 80), random.uniform(55, 75),
                                       random.uniform(-45, 45), random.uniform(-70, -30),
                                       random.uniform(-3, 3)))
        self.mood = mood
        self.update()

    def _current_mood(self, now):
        if self.mood == self.EXCITED and now > self._excited_until:
            self.mood = self.IDLE
        return self.mood

    # ------------------------------------------------------------------ paint
    def paintEvent(self, _):
        now = time.monotonic()
        t = now - self._t0
        mood = self._current_mood(now)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(self.width() / 120, self.height() / 120)  # artwork uses a 120px canvas

        if mood == self.EXCITED:
            hop, tilt, flap = -abs(math.sin(t * 12)) * 9, math.sin(t * 18) * 4, math.sin(t * 30) * 35
        elif mood == self.IDLE:
            hop, tilt, flap = math.sin(t * 2.5) * 2, math.sin(t * 1.3) * 2, 8 + math.sin(t * 2.5) * 6
        else:
            hop, tilt, flap = math.sin(t * 1.2) * 1.2, -10, 0

        p.save()
        p.translate(60, 112 + hop)  # pivot at the feet
        p.rotate(tilt)
        p.translate(-60, -112)
        if theme.MASCOT == "bear":
            if mood == self.EXCITED:
                arms = 125 + math.sin(t * 30) * 25      # waving both arms
            elif mood == self.IDLE:
                arms = 28 + math.sin(t * 2.5) * 6
            else:
                arms = 12
            draw_bear(p, mood, self._eyes_closed(mood, now), arms)
        else:
            self._draw_chicken(p, mood, now, flap, t)
        p.restore()

        self._draw_feathers(p, now)
        if mood == self.SLEEP:
            for i in range(int(t * 1.5) % 3 + 1):
                draw_outlined_text(p, QRectF(84 + i * 8, 22 - i * 11, 24, 24), "Z",
                                   theme.display_font(16 + i * 4), theme.WHITE, width=3)

    def _draw_chicken(self, p, mood, now, flap, t):
        ink = ink_pen(3.5)
        breathe = 1 + (math.sin(t * 1.6) * 0.02 if mood == self.SLEEP else 0)
        body = QRectF(60 - 38 * breathe, 72 - 36 * breathe, 76 * breathe, 72 * breathe)

        # feet
        p.setPen(ink_pen(4, theme.INK))
        for fx in (48, 72):
            p.drawLine(QPointF(fx, 104), QPointF(fx, 112))
            p.drawLine(QPointF(fx, 112), QPointF(fx - 6, 115))
            p.drawLine(QPointF(fx, 112), QPointF(fx + 6, 115))

        # comb (behind the head)
        p.setPen(ink)
        p.setBrush(theme.RED)
        for cx, cy, r in ((48, 30, 8), (60, 25, 10), (72, 30, 8)):
            p.drawEllipse(QPointF(cx, cy), r, r)

        # body + comic shadow
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(theme.SHADOW)
        p.drawEllipse(body.translated(4, 4))
        p.setPen(ink)
        p.setBrush(theme.WHITE)
        p.drawEllipse(body)

        # wings (flap = degrees)
        for side in (-1, 1):
            p.save()
            p.translate(60 + side * 35, 78)
            p.rotate(-side * flap)
            p.setPen(ink)
            p.setBrush(theme.WHITE)
            wing = QPainterPath()
            wing.moveTo(-side * 2, -13)
            wing.cubicTo(side * 22, -12, side * 24, 12, side * 3, 19)
            wing.cubicTo(-side * 5, 10, -side * 6, -4, -side * 2, -13)
            p.drawPath(wing)
            p.restore()

        # cheeks
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(theme.CHEEK)
        p.drawEllipse(QPointF(38, 76), 6, 4)
        p.drawEllipse(QPointF(82, 76), 6, 4)

        self._draw_eyes(p, mood, now)
        self._draw_beak(p, mood)

    def _eyes_closed(self, mood, now):
        if now > self._next_blink:
            self._blink_until = now + 0.12
            self._next_blink = now + random.uniform(2.0, 4.5)
        return mood == self.SLEEP or (mood == self.IDLE and now < self._blink_until)

    def _draw_eyes(self, p, mood, now):
        closed = self._eyes_closed(mood, now)
        for ex in (47, 73):
            e = QPointF(ex, 62)
            if closed:
                path = QPainterPath()
                path.moveTo(e + QPointF(-7, -1))
                path.quadTo(e + QPointF(0, 6), e + QPointF(7, -1))
                p.setPen(ink_pen(3.5))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawPath(path)
                continue
            big = mood == self.EXCITED
            r = 8.5 if big else 6.5
            p.setPen(ink_pen(3))
            p.setBrush(theme.WHITE)
            p.drawEllipse(e, r, r + 1)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(theme.INK)
            p.drawEllipse(e + QPointF(0.5, 1), r * 0.55, r * 0.6)
            p.setBrush(theme.WHITE)
            p.drawEllipse(e + QPointF(2, -1.5), 1.6, 1.6)

    def _draw_beak(self, p, mood):
        # wattle first, so the beak sits on top of it
        p.setPen(ink_pen(2.5))
        p.setBrush(theme.RED)
        top = 89 if mood == self.EXCITED else 82
        w = QPainterPath()
        w.moveTo(55, top - 2)
        w.cubicTo(48, top + 16, 72, top + 16, 65, top - 2)
        w.closeSubpath()
        p.drawPath(w)

        p.setPen(ink_pen(2.5))
        if mood == self.EXCITED:  # squawk: beak wide open
            p.setBrush(theme.INK)
            p.drawEllipse(QPointF(60, 79), 7, 6)
            p.setBrush(theme.BEAK)
            p.drawPolygon(QPolygonF([QPointF(47, 67), QPointF(73, 67), QPointF(60, 76)]))
            p.drawPolygon(QPolygonF([QPointF(51, 82), QPointF(69, 82), QPointF(60, 91)]))
        else:
            p.setBrush(theme.BEAK)
            p.drawPolygon(QPolygonF([QPointF(48, 68), QPointF(72, 68), QPointF(60, 85)]))
            p.drawLine(QPointF(52, 74), QPointF(68, 74))

    def _draw_feathers(self, p, now):
        alive = []
        for f in self._feathers:
            t0, x, y, vx, vy, spin = f
            age = now - t0
            if age > 1.1:
                continue
            alive.append(f)
            fx, fy = x + vx * age, y + vy * age + 60 * age * age  # drift up, then fall
            p.save()
            p.translate(fx, fy)
            p.rotate(math.degrees(spin * age))
            p.setOpacity(max(0.0, 1 - age / 1.1))
            p.setPen(ink_pen(2))
            p.setBrush(theme.WHITE)
            p.drawEllipse(QRectF(-6, -2.5, 12, 5))
            p.restore()
        self._feathers = alive
