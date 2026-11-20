"""Gummy bear art for the Candy pop theme (mascot + logo)."""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainterPath

from . import theme
from .widgets import ink_pen

SNOUT = QColor("#FFD3E6")
SHINE = QColor(255, 255, 255, 150)


def _head_shapes(p, cx, cy, s, ink):
    """Ears + head + snout + nose for a bear head of scale s centred at (cx, cy)."""
    body = QColor(theme.MASCOT_BODY)
    p.setPen(ink)
    for dx in (-24, 24):  # ears
        p.setBrush(body)
        p.drawEllipse(QPointF(cx + dx * s, cy - 24 * s), 10 * s, 10 * s)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(SNOUT)
        p.drawEllipse(QPointF(cx + dx * s, cy - 24 * s), 5 * s, 5 * s)
        p.setPen(ink)
    p.setBrush(body)
    p.drawEllipse(QPointF(cx, cy), 30 * s, 28 * s)
    p.setBrush(SNOUT)
    p.drawEllipse(QPointF(cx, cy + 12 * s), 13 * s, 10 * s)
    p.setBrush(theme.INK)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QPointF(cx, cy + 7 * s), 5 * s, 3.6 * s)


def _shine(p, cx, cy, rx, ry, angle=-25):
    p.save()
    p.translate(cx, cy)
    p.rotate(angle)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(SHINE)
    p.drawEllipse(QPointF(0, 0), rx, ry)
    p.restore()


def draw_bear(p, mood, eyes_closed, arm_angle):
    """Full-body gummy bear on a 120x120 canvas. arm_angle: degrees from hanging down."""
    ink = ink_pen(3.5)
    body = QColor(theme.MASCOT_BODY)

    # feet
    p.setPen(ink)
    p.setBrush(body)
    for fx in (44, 76):
        p.drawEllipse(QPointF(fx, 108), 11, 7)

    # soft candy shadow behind body + head
    sil = QPainterPath()
    sil.addEllipse(QPointF(60, 88), 30, 23)
    sil.addEllipse(QPointF(60, 52), 30, 28)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(theme.SHADOW)
    p.drawPath(sil.translated(4, 4))

    # body with tummy
    p.setPen(ink)
    p.setBrush(body)
    p.drawEllipse(QPointF(60, 88), 30, 23)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(SNOUT)
    p.drawEllipse(QPointF(60, 92), 15, 12)
    _shine(p, 44, 82, 6, 3)

    # arms, rotated outward from the shoulders (Qt: positive angle = clockwise)
    for side in (-1, 1):
        p.save()
        p.translate(60 + side * 27, 79)
        p.rotate(-side * arm_angle)
        p.setPen(ink)
        p.setBrush(body)
        p.drawRoundedRect(QRectF(-6.5, -3, 13, 25), 6.5, 6.5)
        p.restore()

    _head_shapes(p, 60, 52, 1.0, ink)

    # cheeks
    p.setPen(Qt.PenStyle.NoPen)
    cheek = QColor(theme.RED)
    cheek.setAlpha(110)
    p.setBrush(cheek)
    p.drawEllipse(QPointF(36, 60), 6, 4)
    p.drawEllipse(QPointF(84, 60), 6, 4)

    # eyes
    for ex in (47, 73):
        e = QPointF(ex, 48)
        if eyes_closed:
            path = QPainterPath()
            path.moveTo(e + QPointF(-6, -1))
            path.quadTo(e + QPointF(0, 5), e + QPointF(6, -1))
            p.setPen(ink_pen(3))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)
            continue
        big = mood == "excited"
        r = 7 if big else 5
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(theme.INK)
        p.drawEllipse(e, r, r * 1.15)
        p.setBrush(theme.WHITE)
        p.drawEllipse(e + QPointF(2, -2.2), r * 0.38, r * 0.38)
        if big:
            p.drawEllipse(e + QPointF(-2, 2.5), r * 0.18, r * 0.18)

    # mouth
    m = QPointF(60, 68)
    p.setPen(ink_pen(2.6))
    if mood == "excited":
        p.setBrush(theme.INK)
        p.drawEllipse(QPointF(60, 71), 5.5, 5)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(theme.RED)
        p.drawEllipse(QPointF(60, 73.5), 3.5, 2)
    elif mood == "idle":
        path = QPainterPath()
        path.moveTo(m + QPointF(-7, -1))
        path.quadTo(m + QPointF(-3.5, 4), m + QPointF(0, -1))
        path.quadTo(m + QPointF(3.5, 4), m + QPointF(7, -1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
    else:
        p.drawLine(m + QPointF(-3, 1), m + QPointF(3, 1))

    _shine(p, 44, 38, 7, 4)


def draw_bear_logo(p, rect):
    """Bear head for the title bar badge and app icon (100x100 canvas)."""
    p.save()
    p.translate(rect.topLeft())
    p.scale(rect.width() / 100, rect.height() / 100)
    ink = ink_pen(5)
    _head_shapes(p, 50, 58, 1.35, ink)
    for ex in (38, 62):
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(theme.INK)
        p.drawEllipse(QPointF(ex, 52), 5, 6)
        p.setBrush(theme.WHITE)
        p.drawEllipse(QPointF(ex + 1.6, 49.5), 1.8, 1.8)
    p.setPen(ink_pen(3.5))
    p.setBrush(Qt.BrushStyle.NoBrush)
    path = QPainterPath()
    path.moveTo(41, 77)
    path.quadTo(45.5, 83, 50, 77)
    path.quadTo(54.5, 83, 59, 77)
    p.drawPath(path)
    _shine(p, 30, 40, 9, 5)
    p.restore()
