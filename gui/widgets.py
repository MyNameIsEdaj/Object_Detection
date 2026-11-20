"""Hand-drawn comic widgets: thick ink outlines and solid offset shadows."""
import math

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QVariantAnimation, QEasingCurve
from PySide6.QtGui import (QBrush, QColor, QFontMetricsF, QPainter, QPainterPath, QPen,
                           QPixmap, QPolygonF)
from PySide6.QtWidgets import QAbstractButton, QFrame, QPushButton, QSizePolicy, QSlider, QWidget

from . import cursors, theme

SHADOW = 5
BORDER = 3


# ----------------------------------------------------------------- helpers
def ink_pen(width=BORDER, color=None):
    pen = QPen(color or theme.INK, width)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    return pen


def paint_comic_box(p, rect, fill, radius=12, shadow=SHADOW, border=BORDER, pressed=False):
    """Box with a solid black shadow. When pressed, the box sinks onto its shadow."""
    radius = theme.r(radius)
    body = QRectF(rect).adjusted(border / 2, border / 2,
                                 -shadow - border / 2, -shadow - border / 2)
    radius = min(radius, body.height() / 2, body.width() / 2)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(theme.SHADOW)
    if not pressed and shadow:
        p.drawRoundedRect(body.translated(shadow, shadow), radius, radius)
    if pressed:
        body.translate(shadow, shadow)
    p.setBrush(QBrush(fill))
    p.setPen(ink_pen(border))
    p.drawRoundedRect(body, radius, radius)
    return body


def draw_outlined_text(p, rect, text, font, fill, stroke=None, width=4,
                       align=Qt.AlignmentFlag.AlignCenter):
    """Comic lettering: text filled with a colour and stroked with black ink."""
    fm = QFontMetricsF(font)
    tw = fm.horizontalAdvance(text)
    rect = QRectF(rect)
    if align & Qt.AlignmentFlag.AlignLeft:
        x = rect.left() + width
    elif align & Qt.AlignmentFlag.AlignRight:
        x = rect.right() - tw - width
    else:
        x = rect.center().x() - tw / 2
    y = rect.center().y() + (fm.ascent() - fm.descent()) / 2
    path = QPainterPath()
    path.addText(QPointF(x, y), font, text)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.strokePath(path, ink_pen(width, stroke or theme.INK))
    p.fillPath(path, QBrush(fill))


def starburst(center, r_out, r_in, spikes=12, rotation=0.0):
    pts = []
    for i in range(spikes * 2):
        r = r_out if i % 2 == 0 else r_in
        a = rotation + math.pi * i / spikes
        pts.append(QPointF(center.x() + r * math.cos(a), center.y() + r * math.sin(a)))
    return QPolygonF(pts)


def halftone_pixmap(dot_color, bg_color, step=12, radius=1.6):
    pm = QPixmap(step, step)
    pm.fill(bg_color)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(dot_color)
    p.drawEllipse(QPointF(step / 2, step / 2), radius, radius)
    p.end()
    return pm


# ----------------------------------------------------------------- widgets
def sprinkles_pixmap(bg_color, size=96, count=16, seed=7):
    """Tile of little rounded candy sprinkles."""
    import random
    rng = random.Random(seed)
    colors = [theme.RED, theme.BLUE, theme.GREEN, QColor("#FFC83D"), QColor("#B38CFF")]
    pm = QPixmap(size, size)
    pm.fill(bg_color)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    for i in range(count):
        c = QColor(colors[i % len(colors)])
        c.setAlpha(150)
        p.save()
        p.translate(rng.uniform(4, size - 4), rng.uniform(4, size - 4))
        p.rotate(rng.uniform(0, 180))
        p.setBrush(c)
        p.drawRoundedRect(QRectF(-5, -1.6, 10, 3.2), 1.6, 1.6)
        p.restore()
    p.end()
    return pm


class HalftoneBackground(QWidget):
    """Page background: halftone dots (comic) or sprinkles (candy)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        if theme.BACKGROUND == "sprinkles":
            self._brush = QBrush(sprinkles_pixmap(theme.PAPER))
        else:
            self._brush = QBrush(halftone_pixmap(QColor(theme.DOT), theme.PAPER))

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), self._brush)


class ComicPanel(QFrame):
    """Container drawn as a comic box. Put child widgets in its layout."""

    def __init__(self, fill=theme.WHITE, radius=14, parent=None):
        super().__init__(parent)
        self.fill = QColor(fill)
        self.radius = radius
        pad = 10
        self.setContentsMargins(pad, pad - 2, pad + SHADOW, pad + SHADOW - 2)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        paint_comic_box(p, self.rect(), self.fill, self.radius)


class ComicButton(QPushButton):
    """Chunky button that presses down onto its shadow."""

    def __init__(self, text, fill=theme.BLUE, text_color=theme.WHITE, font_px=24, parent=None):
        super().__init__(text, parent)
        self.fill = QColor(fill)
        self.text_color = QColor(text_color)
        self.font_px = font_px
        self.setCursor(cursors.hand())
        self.setMinimumHeight(font_px * 2 + SHADOW + 8)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_style(self, text, fill, text_color=None):
        self.setText(text)
        self.fill = QColor(fill)
        if text_color is not None:
            self.text_color = QColor(text_color)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        fill = QColor(self.fill)
        if not self.isEnabled():
            fill = QColor("#BBBBBB")
        elif self.underMouse() and not self.isDown():
            fill = fill.lighter(112)
        body = paint_comic_box(p, self.rect(), fill, radius=14, pressed=self.isDown())
        draw_outlined_text(p, body, self.text(), theme.display_font(self.font_px),
                           self.text_color, width=5)

    def enterEvent(self, e):
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.update()
        super().leaveEvent(e)


class ToggleSwitch(QAbstractButton):
    """Big round on/off switch."""

    def __init__(self, checked=True, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(cursors.hand())

    def sizeHint(self):
        return QSize(68, 36)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        p.setPen(ink_pen(3))
        p.setBrush(theme.GREEN if self.isChecked() else QColor("#DDDDDD"))
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        d = r.height() - 8
        x = r.right() - d - 4 if self.isChecked() else r.left() + 4
        p.setBrush(theme.WHITE)
        p.drawEllipse(QRectF(x, r.top() + 4, d, d))


class StickerCard(QAbstractButton):
    """Object sticker: shows the live count, click to show/hide that object."""

    def __init__(self, label, color, parent=None):
        super().__init__(parent)
        self.label = label
        self.color = QColor(color)
        self.count = 0
        self._scale = 1.0
        self.setCheckable(True)
        self.setChecked(True)
        self.setCursor(cursors.hand())
        self.setMinimumSize(90, 78)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setToolTip(f"Click to show / hide {label.lower()}")
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(380)
        self._anim.setStartValue(1.45)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self._anim.valueChanged.connect(self._on_anim)
        self.toggled.connect(lambda _: self.update())

    def sizeHint(self):
        return QSize(130, 84)

    def set_count(self, n):
        if n != self.count:
            grew = n > self.count
            self.count = n
            if grew:
                self._anim.stop()
                self._anim.start()
            self.update()

    def _on_anim(self, v):
        self._scale = float(v)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        on = self.isChecked()
        p.setOpacity(1.0 if on else 0.45)
        body = paint_comic_box(p, self.rect(), self.color, radius=12, pressed=self.isDown())
        title = QRectF(body.left(), body.top() + 4, body.width(), 24)
        draw_outlined_text(p, title, self.label, theme.display_font(18), theme.WHITE, width=4)

        num_rect = QRectF(body.left(), title.bottom(), body.width(), body.bottom() - title.bottom())
        p.save()
        c = num_rect.center()
        p.translate(c)
        p.scale(self._scale, self._scale)
        p.translate(-c)
        text = str(self.count) if on else "OFF"
        draw_outlined_text(p, num_rect, text, theme.display_font(32 if on else 24),
                           theme.WHITE if on else QColor("#EEEEEE"), width=6)
        p.restore()


class SpeechBalloon(QWidget):
    """Comic speech balloon with a tail pointing left at the mascot."""

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._text = text
        self.setMinimumHeight(60)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_text(self, text):
        if text != self._text:
            self._text = text
            self.update()

    def text(self):
        return self._text

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        tail = 22
        r = QRectF(self.rect()).adjusted(tail, 4, -SHADOW - 4, -SHADOW - 4)
        path = QPainterPath()
        path.addRoundedRect(r, min(r.height() / 2, theme.r(22)), min(r.height() / 2, theme.r(22)))
        t = QPainterPath()
        cy = r.center().y()
        t.moveTo(r.left() + 6, cy - 12)
        t.lineTo(2, cy + 6)
        t.lineTo(r.left() + 10, cy + 8)
        t.closeSubpath()
        shape = path.united(t)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(theme.SHADOW)
        p.drawPath(shape.translated(SHADOW, SHADOW))
        p.setBrush(theme.WHITE)
        p.setPen(ink_pen(3))
        p.drawPath(shape)
        p.setFont(theme.display_font(22))
        p.setPen(theme.INK)
        p.drawText(r.adjusted(14, 2, -14, -2),
                   Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self._text)


class OutlinedTitle(QWidget):
    """Big comic title lettering."""

    STROKE = 7
    SHADOW_OFFSET = 4

    def __init__(self, text, fill=theme.RED, px=44, parent=None):
        super().__init__(parent)
        self.text, self.fill, self.px = text, QColor(fill), px
        # size from the real text width in the active font (Fredoka is much wider than Impact)
        fm = QFontMetricsF(theme.display_font(px))
        width = fm.horizontalAdvance(text) + 2 * self.STROKE + self.SHADOW_OFFSET + 8
        self.setMinimumHeight(int(fm.height() + self.STROKE + self.SHADOW_OFFSET + 8))
        self.setFixedWidth(int(width))
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        font = theme.display_font(self.px)
        o = self.SHADOW_OFFSET
        area = QRectF(self.rect()).adjusted(0, 0, -o, -o)  # leave room for the shadow
        draw_outlined_text(p, area.translated(o, o), self.text, font, theme.SHADOW,
                           stroke=theme.SHADOW, width=self.STROKE)
        draw_outlined_text(p, area, self.text, font, self.fill, width=self.STROKE)


class ComicSlider(QSlider):
    """Horizontal slider drawn by hand: track, red fill, big yellow knob on top."""

    KNOB = 26   # knob diameter
    TRACK = 14  # track height

    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setCursor(cursors.hand())
        self.setMinimumHeight(self.KNOB + 8)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def sizeHint(self):
        return QSize(200, self.KNOB + 8)

    def _track_span(self):
        r = self.KNOB / 2 + 2
        return r, self.width() - r - 3  # x of the knob centre at min / max

    def _knob_x(self):
        x0, x1 = self._track_span()
        span = max(1, self.maximum() - self.minimum())
        return x0 + (x1 - x0) * (self.value() - self.minimum()) / span

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cy = self.height() / 2 - 1
        x0, x1 = self._track_span()
        track = QRectF(x0 - self.TRACK / 2, cy - self.TRACK / 2,
                       x1 - x0 + self.TRACK, self.TRACK)
        kx = self._knob_x()
        p.setPen(ink_pen(3))
        p.setBrush(theme.WHITE)
        p.drawRoundedRect(track, self.TRACK / 2, self.TRACK / 2)
        filled = QRectF(track.left(), track.top(), kx - track.left(), track.height())
        if filled.width() > 1:
            p.setBrush(theme.RED)
            p.drawRoundedRect(filled, self.TRACK / 2, self.TRACK / 2)
        # knob: shadow, then the yellow circle on top of everything
        r = self.KNOB / 2
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(theme.SHADOW)
        p.drawEllipse(QPointF(kx + 2.5, cy + 2.5), r, r)
        p.setPen(ink_pen(3))
        p.setBrush(theme.PAPER.lighter(105) if self.isSliderDown() else theme.PAPER)
        p.drawEllipse(QPointF(kx, cy), r - 1.5, r - 1.5)

    def _value_at(self, x):
        x0, x1 = self._track_span()
        k = min(1.0, max(0.0, (x - x0) / max(1.0, x1 - x0)))
        return round(self.minimum() + k * (self.maximum() - self.minimum()))

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.setSliderDown(True)
            self.setValue(self._value_at(e.position().x()))
            e.accept()
        else:
            super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self.isSliderDown():
            self.setValue(self._value_at(e.position().x()))
            e.accept()
        else:
            super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self.isSliderDown():
            self.setSliderDown(False)
            self.update()
            e.accept()
        else:
            super().mouseReleaseEvent(e)
