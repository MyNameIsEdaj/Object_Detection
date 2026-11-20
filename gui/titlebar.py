"""Custom title bar (replaces the Windows one) and the theme logo (chicken / gummy bear)."""
from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QBrush, QColor, QIcon, QPainter, QPainterPath, QPixmap, QPolygonF
from PySide6.QtWidgets import QAbstractButton, QHBoxLayout, QWidget

from . import cursors, theme
from .bear import draw_bear_logo
from .widgets import draw_outlined_text, halftone_pixmap, ink_pen

BAR_HEIGHT = 50
BORDER = 5  # ink border around the window (also the resize grip)


# --------------------------------------------------------------- chicken logo
def draw_chicken(p, rect):
    """Cartoon chicken head, drawn on a 100x100 canvas scaled into rect."""
    p.save()
    p.translate(rect.topLeft())
    p.scale(rect.width() / 100, rect.height() / 100)
    pen = ink_pen(5)
    p.setPen(pen)

    # comb (three red bumps)
    p.setBrush(theme.RED)
    for cx, cy, r in ((34, 22, 11), (50, 15, 13), (66, 22, 11)):
        p.drawEllipse(QPointF(cx, cy), r, r)
    # head
    p.setBrush(theme.WHITE)
    p.drawEllipse(QPointF(50, 56), 34, 34)
    # cheeks
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#FF9EC7"))
    p.drawEllipse(QPointF(28, 66), 6, 4)
    p.drawEllipse(QPointF(72, 66), 6, 4)
    p.setPen(pen)
    # eyes
    for ex in (38, 62):
        p.setBrush(theme.INK)
        p.drawEllipse(QPointF(ex, 50), 4.5, 5.5)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(theme.WHITE)
    for ex in (39.5, 63.5):
        p.drawEllipse(QPointF(ex, 48), 1.6, 1.6)
    p.setPen(pen)
    # beak
    p.setBrush(QColor("#FFB020"))
    p.drawPolygon(QPolygonF([QPointF(40, 60), QPointF(60, 60), QPointF(50, 74)]))
    # wattle
    p.setBrush(theme.RED)
    w = QPainterPath()
    w.moveTo(46, 74)
    w.cubicTo(42, 86, 58, 86, 54, 74)
    w.closeSubpath()
    p.drawPath(w)
    p.restore()


def draw_logo(p, rect):
    if theme.MASCOT == "bear":
        draw_bear_logo(p, rect)
    else:
        draw_chicken(p, rect)


def logo_icon():
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        draw_logo(p, QRectF(0, 0, size, size))
        p.end()
        icon.addPixmap(pm)
    return icon


chicken_icon = logo_icon  # old name, kept for compatibility


class LogoBadge(QWidget):
    """Round badge with the theme logo, at the left of the title bar."""

    def __init__(self, size=40, parent=None):
        super().__init__(parent)
        self.setFixedSize(size + 4, size + 4)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        d = self.width() - 6
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(theme.SHADOW)
        p.drawEllipse(QRectF(4, 4, d, d))
        p.setPen(ink_pen(3))
        p.setBrush(theme.PAPER if theme.NAME == "comic" else theme.WHITE)
        p.drawEllipse(QRectF(1.5, 1.5, d, d))
        inset = d * 0.12
        draw_logo(p, QRectF(1.5 + inset, 1.5 + inset * 0.6, d - 2 * inset, d - 2 * inset))


ChickenBadge = LogoBadge


# ------------------------------------------------------------ window buttons
class TitleButton(QAbstractButton):
    COLORS = {"music": theme.WHITE, "sound": theme.WHITE, "theme": theme.WHITE, "min": theme.PAPER, "max": theme.GREEN,
              "close": theme.WHITE}

    def __init__(self, kind, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.maximized = False
        self.setFixedSize(QSize(40, 36))
        self.setCursor(cursors.hand())
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.muted = False
        self.setToolTip({"music": "Music on / off (B)", "sound": "Sound on / off (M)", "theme": "Switch theme", "min": "Minimise",
                         "max": "Maximise", "close": "Close"}[kind])

    def enterEvent(self, e):
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.update()
        super().leaveEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        sh = 3
        down = self.isDown()
        body = QRectF(1.5, 1.5, self.width() - sh - 3, self.height() - sh - 3)
        if not down:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(theme.SHADOW)
            p.drawRoundedRect(body.translated(sh, sh), theme.r(8), theme.r(8))
        else:
            body.translate(sh, sh)
        fill = QColor(self.COLORS[self.kind])
        if self.kind == "close" and self.underMouse():
            fill = QColor(theme.INK)
        elif self.underMouse():
            fill = fill.lighter(110)
        p.setPen(ink_pen(3))
        p.setBrush(fill)
        p.drawRoundedRect(body, theme.r(8), theme.r(8))

        c = body.center()
        icon_color = theme.RED if self.kind == "close" else theme.INK
        if self.kind == "close" and self.underMouse():
            icon_color = theme.WHITE
        p.setPen(ink_pen(3.5, icon_color))
        p.setBrush(Qt.BrushStyle.NoBrush)
        if self.kind == "music":  # music note, with a slash when off
            p.setPen(ink_pen(2.4))
            p.setBrush(theme.INK)
            p.drawEllipse(QPointF(c.x() - 4, c.y() + 5), 3.6, 2.8)
            p.drawEllipse(QPointF(c.x() + 5, c.y() + 3), 3.6, 2.8)
            p.drawLine(QPointF(c.x() - 0.8, c.y() + 5), QPointF(c.x() - 0.8, c.y() - 7))
            p.drawLine(QPointF(c.x() + 8.2, c.y() + 3), QPointF(c.x() + 8.2, c.y() - 9))
            p.drawLine(QPointF(c.x() - 0.8, c.y() - 7), QPointF(c.x() + 8.2, c.y() - 9))
            if self.muted:
                p.setPen(ink_pen(3, theme.RED))
                p.drawLine(QPointF(c.x() - 9, c.y() + 8), QPointF(c.x() + 9, c.y() - 8))
        elif self.kind == "sound":  # speaker, with a slash when muted
            spk = QPolygonF([QPointF(c.x() - 8, c.y() - 3), QPointF(c.x() - 4, c.y() - 3),
                             QPointF(c.x() + 1, c.y() - 8), QPointF(c.x() + 1, c.y() + 8),
                             QPointF(c.x() - 4, c.y() + 3), QPointF(c.x() - 8, c.y() + 3)])
            p.setPen(ink_pen(2.2))
            p.setBrush(theme.INK)
            p.drawPolygon(spk)
            p.setBrush(Qt.BrushStyle.NoBrush)
            if self.muted:
                p.setPen(ink_pen(3, theme.RED))
                p.drawLine(QPointF(c.x() - 9, c.y() + 8), QPointF(c.x() + 9, c.y() - 8))
            else:
                p.setPen(ink_pen(2.2))
                p.drawArc(QRectF(c.x() - 3, c.y() - 5, 8, 10), -50 * 16, 100 * 16)
                p.drawArc(QRectF(c.x() - 3, c.y() - 9, 13, 18), -50 * 16, 100 * 16)
        elif self.kind == "theme":  # swatch: comic yellow + candy pink
            rr = QRectF(c.x() - 8, c.y() - 8, 16, 16)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#FFE14D"))
            p.drawPie(rr, 45 * 16, 180 * 16)
            p.setBrush(QColor("#FF6FAE"))
            p.drawPie(rr, 225 * 16, 180 * 16)
            p.setPen(ink_pen(2.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(rr)
        elif self.kind == "min":
            p.drawLine(QPointF(c.x() - 7, c.y() + 5), QPointF(c.x() + 7, c.y() + 5))
        elif self.kind == "max":
            if self.maximized:  # "restore" icon: two overlapping squares
                p.drawRect(QRectF(c.x() - 7, c.y() - 3, 10, 10))
                p.drawLine(QPointF(c.x() - 3, c.y() - 7), QPointF(c.x() + 7, c.y() - 7))
                p.drawLine(QPointF(c.x() + 7, c.y() - 7), QPointF(c.x() + 7, c.y() + 3))
            else:
                p.drawRect(QRectF(c.x() - 7, c.y() - 7, 14, 14))
        else:
            p.drawLine(QPointF(c.x() - 6, c.y() - 6), QPointF(c.x() + 6, c.y() + 6))
            p.drawLine(QPointF(c.x() + 6, c.y() - 6), QPointF(c.x() - 6, c.y() + 6))


# ------------------------------------------------------------------ title bar
class TitleBar(QWidget):
    def __init__(self, window, title="OBJECT SPOTTER!", parent=None):
        super().__init__(parent)
        self.win = window
        self.title = title
        self.setFixedHeight(BAR_HEIGHT)
        dot = QColor(theme.INK)
        dot.setAlpha(40)
        self._brush = QBrush(halftone_pixmap(dot, theme.RED, step=10, radius=1.4))

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 3, 10, 6)
        lay.setSpacing(8)
        lay.addWidget(LogoBadge(38))
        lay.addStretch(1)
        self.music_btn = TitleButton("music")
        lay.addWidget(self.music_btn)
        self.sound_btn = TitleButton("sound")
        lay.addWidget(self.sound_btn)
        self.theme_btn = TitleButton("theme")
        other = theme.THEMES[theme.next_theme()]["label"]
        self.theme_btn.setToolTip(f"Switch to {other}")
        lay.addWidget(self.theme_btn)
        lay.addSpacing(10)
        self.min_btn = TitleButton("min")
        self.max_btn = TitleButton("max")
        self.close_btn = TitleButton("close")
        self.min_btn.clicked.connect(window.showMinimized)
        self.max_btn.clicked.connect(self.toggle_maximized)
        self.close_btn.clicked.connect(window.close)
        for b in (self.min_btn, self.max_btn, self.close_btn):
            lay.addWidget(b)

    def toggle_maximized(self):
        if self.win.isMaximized():
            self.win.showNormal()
        else:
            self.win.showMaximized()

    def set_music(self, on, available=True):
        self.music_btn.muted = not on
        if not available:
            self.music_btn.setToolTip("Music needs Qt's multimedia module")
        else:
            self.music_btn.setToolTip("Music is on - click to stop (B)" if on
                                      else "Music is off - click to play (B)")
        self.music_btn.update()

    def set_muted(self, muted):
        self.sound_btn.muted = muted
        self.sound_btn.setToolTip("Sound is off - click to turn on (M)" if muted
                                  else "Sound is on - click to mute (M)")
        self.sound_btn.update()

    def update_state(self):
        self.max_btn.maximized = self.win.isMaximized()
        self.max_btn.setToolTip("Restore" if self.max_btn.maximized else "Maximise")
        self.max_btn.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), self._brush)
        p.setPen(ink_pen(3))
        y = self.height() - 1.5
        p.drawLine(QPointF(0, y), QPointF(self.width(), y))
        draw_outlined_text(p, QRectF(58, 0, self.width() / 2, self.height() - 4), self.title,
                           theme.display_font(26), theme.WHITE, width=5,
                           align=Qt.AlignmentFlag.AlignLeft)

    # drag to move, double-click to maximise (Windows snap still works)
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.win.windowHandle():
            self.win.windowHandle().startSystemMove()
            e.accept()

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.toggle_maximized()


class InkFrame(QWidget):
    """Thick ink border around the whole window; dragging it resizes the window."""

    def __init__(self, window, parent=None):
        super().__init__(parent)
        self.win = window
        self.setMouseTracking(True)
        self.set_border(True)

    def set_border(self, on):
        b = BORDER if on else 0
        self._border = b
        self.setContentsMargins(b, b, b, b)
        self.update()

    def paintEvent(self, _):
        if self._border:
            QPainter(self).fillRect(self.rect(), theme.INK)

    def _edges(self, pos):
        """Window edges under the mouse (None when not on the border)."""
        if not self._border:
            return None
        m = self._border + 3
        found = []
        if pos.x() <= m:
            found.append(Qt.Edge.LeftEdge)
        if pos.x() >= self.width() - m:
            found.append(Qt.Edge.RightEdge)
        if pos.y() <= m:
            found.append(Qt.Edge.TopEdge)
        if pos.y() >= self.height() - m:
            found.append(Qt.Edge.BottomEdge)
        if not found:
            return None
        edges = found[0]
        for e in found[1:]:
            edges = edges | e
        return edges

    def mouseMoveEvent(self, e):
        edges = self._edges(e.position().toPoint())
        if edges is None:
            self.unsetCursor()
            return
        lr = bool(edges & Qt.Edge.LeftEdge) or bool(edges & Qt.Edge.RightEdge)
        tb = bool(edges & Qt.Edge.TopEdge) or bool(edges & Qt.Edge.BottomEdge)
        if lr and tb:
            tl_br = (bool(edges & Qt.Edge.LeftEdge) and bool(edges & Qt.Edge.TopEdge)) or \
                    (bool(edges & Qt.Edge.RightEdge) and bool(edges & Qt.Edge.BottomEdge))
            self.setCursor(Qt.CursorShape.SizeFDiagCursor if tl_br else Qt.CursorShape.SizeBDiagCursor)
        elif lr:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        else:
            self.setCursor(Qt.CursorShape.SizeVerCursor)

    def mousePressEvent(self, e):
        edges = self._edges(e.position().toPoint())
        if e.button() == Qt.MouseButton.LeftButton and edges is not None and self.win.windowHandle():
            self.win.windowHandle().startSystemResize(edges)
            e.accept()
