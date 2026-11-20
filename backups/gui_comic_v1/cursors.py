"""Comic mouse cursors: a red ink arrow and a white cartoon-glove pointing hand."""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QCursor, QGuiApplication, QPainter, QPainterPath, QPen, QPixmap, QPolygonF

from . import theme


def ink_pen(width, color=None):
    pen = QPen(color or theme.INK, width)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    return pen

SIZE = 32  # logical pixels (scaled for Windows display scaling)
_cache = {}

ARROW = [(3, 2), (3, 25), (9, 19.5), (13.5, 29), (18, 27), (13.8, 18), (21.5, 18)]


def _canvas():
    screen = QGuiApplication.primaryScreen()
    dpr = screen.devicePixelRatio() if screen else 1.0
    pm = QPixmap(int(SIZE * dpr), int(SIZE * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    return pm, p


def _arrow_pixmap():
    pm, p = _canvas()
    shape = QPolygonF([QPointF(x, y) for x, y in ARROW])
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(theme.INK)
    p.drawPolygon(shape.translated(2, 2))           # comic shadow
    p.setPen(ink_pen(2.2))
    p.setBrush(theme.RED)
    p.drawPolygon(shape)
    p.setPen(ink_pen(1.6, theme.WHITE))             # little shine
    p.drawLine(QPointF(5.5, 8), QPointF(5.5, 15))
    p.end()
    return pm


def _hand_pixmap():
    pm, p = _canvas()
    hand = QPainterPath()
    hand.addEllipse(QRectF(4, 15, 8, 8))                  # thumb
    for x0, y0, x1, y1, r in ((8, 13, 25, 30, 4),        # palm
                              (11, 1, 17, 19, 3),        # pointing finger
                              (16, 10, 21, 19, 2.5),     # folded fingers
                              (20, 12, 25, 20, 2.5),
                              (8, 26, 25, 31, 1.5)):     # glove cuff
        part = QPainterPath()
        part.addRoundedRect(QRectF(x0, y0, x1 - x0, y1 - y0), r, r)
        hand = hand.united(part)

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(theme.INK)
    p.drawPath(hand.translated(2, 2))                    # comic shadow
    p.setPen(ink_pen(2))
    p.setBrush(theme.WHITE)
    p.drawPath(hand)
    # creases between the folded fingers and the cuff line
    p.setPen(ink_pen(1.4))
    p.drawLine(QPointF(17, 13.5), QPointF(17, 19))
    p.drawLine(QPointF(21, 14), QPointF(21, 19.5))
    p.drawLine(QPointF(8.5, 26), QPointF(24.5, 26))
    p.setPen(ink_pen(1.2, theme.RED))
    p.drawLine(QPointF(10.5, 28.5), QPointF(22.5, 28.5))
    p.end()
    return pm


def arrow():
    if "arrow" not in _cache:
        _cache["arrow"] = QCursor(_arrow_pixmap(), 3, 2)      # hotspot: arrow tip
    return _cache["arrow"]


def hand():
    if "hand" not in _cache:
        _cache["hand"] = QCursor(_hand_pixmap(), 14, 2)       # hotspot: fingertip
    return _cache["hand"]
