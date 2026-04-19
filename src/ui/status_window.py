import sys
import os
import math
from dataclasses import dataclass, field
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer, QRectF, QPointF
from PyQt5.QtGui import QFont, QPainter, QPen, QColor, QLinearGradient, QPainterPath, QBrush
from PyQt5.QtWidgets import (
    QApplication, QLabel, QVBoxLayout, QWidget, QFrame,
    QStackedWidget, QPushButton, QSizePolicy,
)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ui.base_window import BaseWindow
from utils import ConfigManager


# -------- Theme --------------------------------------------------------------


@dataclass
class Theme:
    name: str
    bg_top: QColor
    bg_bot: QColor
    highlight: QColor
    divider: QColor
    show_divider: bool
    text: QColor
    mic_primary: QColor
    mic_secondary: QColor
    level_fill: QColor
    button_outline: QColor
    button_text_idle: QColor
    button_fill_hover: QColor
    button_fill_press: QColor
    button_text_active: QColor
    button_fill_disabled: QColor
    button_text_disabled: QColor
    close_icon_color: QColor
    close_hover_bg: QColor
    mic_style: str              # 'contour' or 'solid'
    transcribe_style: str       # 'waveform' or 'spinner'
    border_color: QColor = field(default_factory=lambda: QColor(0, 0, 0, 0))
    border_width: float = 0.0


def _lavender_light_theme() -> Theme:
    """Light lavender tile as shipped in the GitHub commit."""
    return Theme(
        name='lavender_light',
        bg_top=QColor(206, 200, 232),
        bg_bot=QColor(192, 185, 222),
        highlight=QColor(255, 255, 255, 110),
        divider=QColor(79, 77, 96, 30),
        show_divider=True,
        text=QColor(122, 111, 168),
        mic_primary=QColor(67, 63, 92),
        mic_secondary=QColor(67, 63, 92),
        level_fill=QColor(122, 111, 168),
        button_outline=QColor(122, 111, 168, 200),
        button_text_idle=QColor(122, 111, 168),
        button_fill_hover=QColor(175, 165, 220),
        button_fill_press=QColor(155, 145, 205),
        button_text_active=QColor(67, 63, 92),
        button_fill_disabled=QColor(200, 195, 225),
        button_text_disabled=QColor(67, 63, 92, 150),
        close_icon_color=QColor(79, 77, 96),
        close_hover_bg=QColor(79, 77, 96, 22),
        mic_style='contour',
        transcribe_style='waveform',
    )


def _lavender_dark_theme() -> Theme:
    """Dark-grey tile with mid-lavender accents — as rendered in commit f4f611a.

    Visually the background was #1e1e1e (global QSS over centralWidget), not
    the indigo drawn in BaseWindow.paintEvent which was hidden behind it.
    Mic contour TILE_TEXT #433f5c; fill/outline/label FILL_MID #7a6fa8.
    """
    return Theme(
        name='lavender_dark',
        bg_top=QColor(30, 30, 30),
        bg_bot=QColor(30, 30, 30),
        highlight=QColor(0, 0, 0, 0),
        divider=QColor(122, 111, 168, 35),
        show_divider=False,
        text=QColor(122, 111, 168),
        mic_primary=QColor(67, 63, 92),
        mic_secondary=QColor(67, 63, 92),
        level_fill=QColor(122, 111, 168),
        button_outline=QColor(122, 111, 168, 200),
        button_text_idle=QColor(122, 111, 168),
        button_fill_hover=QColor(90, 80, 130),
        button_fill_press=QColor(70, 60, 105),
        button_text_active=QColor(232, 223, 255),
        button_fill_disabled=QColor(55, 55, 55),
        button_text_disabled=QColor(122, 111, 168, 130),
        close_icon_color=QColor(122, 111, 168),
        close_hover_bg=QColor(122, 111, 168, 40),
        mic_style='contour',
        transcribe_style='waveform',
    )


def _lavender_violet_theme() -> Theme:
    """Deep indigo tile with bright lavender accents — 'violet' variant."""
    return Theme(
        name='lavender_violet',
        bg_top=QColor(21, 18, 46),
        bg_bot=QColor(30, 27, 58),
        highlight=QColor(196, 181, 253, 110),
        divider=QColor(196, 181, 253, 40),
        show_divider=True,
        text=QColor(196, 181, 253),
        mic_primary=QColor(221, 214, 254),
        mic_secondary=QColor(221, 214, 254),
        level_fill=QColor(167, 139, 250),
        button_outline=QColor(196, 181, 253, 190),
        button_text_idle=QColor(196, 181, 253),
        button_fill_hover=QColor(139, 92, 246),
        button_fill_press=QColor(124, 58, 237),
        button_text_active=QColor(245, 243, 255),
        button_fill_disabled=QColor(67, 56, 120),
        button_text_disabled=QColor(196, 181, 253, 130),
        close_icon_color=QColor(221, 214, 254),
        close_hover_bg=QColor(196, 181, 253, 40),
        mic_style='contour',
        transcribe_style='waveform',
    )


def _clean_theme() -> Theme:
    return Theme(
        name='clean',
        bg_top=QColor(247, 248, 251),
        bg_bot=QColor(247, 248, 251),
        highlight=QColor(0, 0, 0, 14),
        divider=QColor(0, 0, 0, 14),
        show_divider=False,
        text=QColor(107, 112, 133),
        mic_primary=QColor(95, 100, 120),
        mic_secondary=QColor(63, 68, 86),
        level_fill=QColor(0, 0, 0, 64),
        button_outline=QColor(95, 100, 120),
        button_text_idle=QColor(95, 100, 120),
        button_fill_hover=QColor(230, 234, 242),
        button_fill_press=QColor(215, 220, 232),
        button_text_active=QColor(63, 68, 86),
        button_fill_disabled=QColor(240, 242, 246),
        button_text_disabled=QColor(107, 112, 133, 150),
        close_icon_color=QColor(138, 144, 163),
        close_hover_bg=QColor(0, 0, 0, 18),
        mic_style='solid',
        transcribe_style='spinner',
    )


def _dark_theme() -> Theme:
    return Theme(
        name='dark',
        bg_top=QColor(23, 25, 35),
        bg_bot=QColor(23, 25, 35),
        highlight=QColor(255, 255, 255, 14),
        divider=QColor(255, 255, 255, 14),
        show_divider=False,
        text=QColor(140, 146, 168),
        mic_primary=QColor(143, 148, 173),
        mic_secondary=QColor(95, 100, 122),
        level_fill=QColor(0, 0, 0, 100),
        button_outline=QColor(143, 148, 173),
        button_text_idle=QColor(143, 148, 173),
        button_fill_hover=QColor(42, 47, 61),
        button_fill_press=QColor(32, 37, 51),
        button_text_active=QColor(223, 227, 240),
        button_fill_disabled=QColor(30, 33, 48),
        button_text_disabled=QColor(140, 146, 168, 150),
        close_icon_color=QColor(140, 146, 168),
        close_hover_bg=QColor(255, 255, 255, 24),
        mic_style='solid',
        transcribe_style='spinner',
    )


THEME_FACTORIES = {
    'lavender_light': _lavender_light_theme,
    'lavender_dark': _lavender_dark_theme,
    'lavender_violet': _lavender_violet_theme,
    'clean': _clean_theme,
    'dark': _dark_theme,
}
# Backward-compat alias for configs saved before rename.
_THEME_ALIASES = {'lavender': 'lavender_light'}
THEME_NAMES = list(THEME_FACTORIES.keys())


def get_theme(name: str) -> Theme:
    name = _THEME_ALIASES.get(name, name)
    factory = THEME_FACTORIES.get(name, _lavender_light_theme)
    return factory()


# -------- Microphone (two styles) -------------------------------------------


def _contour_mic_paths():
    """SVG-derived paths — viewBox 72x104 (used by 'contour' style)."""
    head = QPainterPath()
    head.addRoundedRect(QRectF(21, 8, 30, 50), 15, 15)

    yoke = QPainterPath()
    yoke.moveTo(14, 39)
    yoke.lineTo(14, 52)
    yoke.cubicTo(14, 64.1503, 23.8497, 74, 36, 74)
    yoke.cubicTo(48.1503, 74, 58, 64.1503, 58, 52)
    yoke.lineTo(58, 39)

    stem = QPainterPath()
    stem.moveTo(36, 74)
    stem.lineTo(36, 89)

    base = QPainterPath()
    base.moveTo(24, 95)
    base.lineTo(48, 95)

    return head, yoke, stem, base


class MicLevelWidget(QWidget):
    """Microphone with live level fill. Style depends on theme.mic_style."""

    VIEW_W = 72
    VIEW_H = 104

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._idle_target = 0.08
        self._level = self._idle_target
        self._target = self._idle_target
        self.setFixedSize(self.VIEW_W, self.VIEW_H)
        self.setStyleSheet("background: transparent;")
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(30)

    def set_level(self, value):
        self._target = max(self._idle_target, min(1.0, value))

    def reset(self):
        self._level = self._idle_target
        self._target = self._idle_target
        self.update()

    def _animate(self):
        if self._target > self._level:
            self._level += (self._target - self._level) * 0.38
        else:
            self._level += (self._target - self._level) * 0.10
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self.theme.mic_style == 'solid':
            self._paint_solid(p)
        else:
            self._paint_contour(p)

    def _paint_contour(self, p):
        head, yoke, stem, base = _contour_mic_paths()
        inner_head = QPainterPath()
        inner_head.addRoundedRect(QRectF(22.75, 9.75, 26.5, 46.5), 13.25, 13.25)
        fill_top = 9.75
        fill_bot = 9.75 + 46.5
        level_clamped = max(0.08, self._level)
        fill_h = (fill_bot - fill_top) * level_clamped
        fill_y = fill_bot - fill_h
        fill_rect = QRectF(22.75, fill_y, 26.5, fill_h)

        p.save()
        p.setClipPath(inner_head)
        p.fillRect(fill_rect, self.theme.level_fill)
        p.restore()

        pen = QPen(self.theme.mic_primary, 5.5)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawPath(head)
        p.drawPath(yoke)
        p.drawPath(stem)
        p.drawPath(base)

    def _paint_solid(self, p):
        # Head: 40x64 rounded rect, gradient primary→secondary top-down
        head_rect = QRectF(16, 8, 40, 64)
        head_path = QPainterPath()
        head_path.addRoundedRect(head_rect, 20, 20)

        grad = QLinearGradient(0, head_rect.top(), 0, head_rect.bottom())
        grad.setColorAt(0.0, self.theme.mic_primary)
        grad.setColorAt(1.0, self.theme.mic_secondary)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawPath(head_path)

        # Level overlay — dark translucent block from bottom, clipped to head
        level_clamped = max(0.08, self._level)
        fill_h = 64 * level_clamped
        fill_y = head_rect.bottom() - fill_h
        fill_rect = QRectF(head_rect.left(), fill_y, 40, fill_h)
        p.save()
        p.setClipPath(head_path)
        p.fillRect(fill_rect, self.theme.level_fill)
        p.restore()

        # Stem — 2x18 under head
        stem = QRectF(35, 76, 2, 18)
        p.setBrush(QBrush(self.theme.mic_secondary))
        p.drawRoundedRect(stem, 1, 1)

        # Base — 20x3 centered under stem
        base = QRectF(26, 97, 20, 3)
        p.drawRoundedRect(base, 1.5, 1.5)


# -------- Buttons -----------------------------------------------------------


class CircleButton(QPushButton):
    """Minimal icon button — small cross, colour from theme."""

    def __init__(self, theme: Theme, icon_kind='cross', size=28, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.icon_kind = icon_kind
        self.SIZE = size
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
        self._hover = False
        self._pressed = False
        self.setFlat(True)
        self.setStyleSheet(
            f"QPushButton {{"
            f" background: transparent; border: none; padding: 0;"
            f" min-width: {size}px; max-width: {size}px;"
            f" min-height: {size}px; max-height: {size}px;"
            f" }}"
        )
        self.setFixedSize(size, size)
        self.setFocusPolicy(Qt.NoFocus)

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self._pressed = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._pressed = True
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._pressed = False
        self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        side = min(self.width(), self.height())
        cx = self.width() / 2
        cy = self.height() / 2
        r = QRectF(cx - side / 2 + 0.5, cy - side / 2 + 0.5, side - 1, side - 1)

        if self._pressed or self._hover:
            bg = self.theme.close_hover_bg
            if self._pressed:
                bg = QColor(bg.red(), bg.green(), bg.blue(), min(255, bg.alpha() + 20))
            p.setBrush(QBrush(bg))
            p.setPen(Qt.NoPen)
            p.drawEllipse(r)

        base_color = self.theme.close_icon_color
        if self._pressed:
            icon_color = QColor(base_color.red(), base_color.green(), base_color.blue(), 255)
            stroke_w = 2.0
        elif self._hover:
            icon_color = QColor(base_color.red(), base_color.green(), base_color.blue(), 235)
            stroke_w = 1.9
        else:
            icon_color = QColor(base_color.red(), base_color.green(), base_color.blue(), 200)
            stroke_w = 1.8

        icon_pen = QPen(icon_color, stroke_w)
        icon_pen.setCapStyle(Qt.RoundCap)
        icon_pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(icon_pen)
        p.setBrush(Qt.NoBrush)

        s = max(3.5, side * 0.20)
        if self.icon_kind == 'cross':
            p.drawLine(QPointF(cx - s, cy - s), QPointF(cx + s, cy + s))
            p.drawLine(QPointF(cx - s, cy + s), QPointF(cx + s, cy - s))


class PillButton(QPushButton):
    """Ghost pill by default (outline only); fills on hover and swaps label."""

    def __init__(self, theme: Theme, idle_text, hover_text=None, parent=None):
        super().__init__(idle_text, parent)
        self.theme = theme
        self._idle_text = idle_text
        self._hover_text = hover_text if hover_text is not None else idle_text
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFlat(True)
        self._hover = False
        self._pressed = False
        self.setFixedHeight(34)
        self.setMinimumWidth(140)
        f = QFont('Segoe UI', 12, QFont.DemiBold)
        self.setFont(f)
        self.setStyleSheet("background: transparent; border: none;")

    def set_texts(self, idle_text, hover_text=None):
        self._idle_text = idle_text
        self._hover_text = hover_text if hover_text is not None else idle_text
        self.setText(self._hover_text if self._hover else self._idle_text)
        self.update()

    def enterEvent(self, event):
        self._hover = True
        self.setText(self._hover_text)
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self._pressed = False
        self.setText(self._idle_text)
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._pressed = True
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._pressed = False
        self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        radius = r.height() / 2

        if not self.isEnabled():
            p.setBrush(QBrush(self.theme.button_fill_disabled))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(r, radius, radius)
            p.setPen(self.theme.button_text_disabled)
        elif self._pressed:
            p.setBrush(QBrush(self.theme.button_fill_press))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(r, radius, radius)
            p.setPen(self.theme.button_text_active)
        elif self._hover:
            p.setBrush(QBrush(self.theme.button_fill_hover))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(r, radius, radius)
            p.setPen(self.theme.button_text_active)
        else:
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(self.theme.button_outline, 1.4))
            p.drawRoundedRect(r.adjusted(0.25, 0.25, -0.25, -0.25), radius - 0.25, radius - 0.25)
            p.setPen(self.theme.button_text_idle)

        p.setFont(self.font())
        p.drawText(r, Qt.AlignCenter, self.text())


# -------- Transcription indicators ------------------------------------------


class WaveformWidget(QWidget):
    """Animated vertical bars — shown while transcribing (lavender theme)."""

    VIEW_W = 72
    VIEW_H = 104
    N_BARS = 7

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setFixedSize(self.VIEW_W, self.VIEW_H)
        self.setStyleSheet("background: transparent;")
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(40)

    def _tick(self):
        self._phase += 0.22
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()
        cy = h / 2

        pen = QPen(self.theme.level_fill, 5.5)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)

        gap = 5
        available = w - 16
        bar_w = (available - gap * (self.N_BARS - 1)) / self.N_BARS
        start_x = 8 + bar_w / 2
        max_half = h * 0.33
        for i in range(self.N_BARS):
            offset = (i - (self.N_BARS - 1) / 2) / ((self.N_BARS - 1) / 2)
            envelope = math.cos(offset * math.pi / 2) ** 1.4
            wave = 0.5 + 0.5 * math.sin(self._phase + i * 0.85)
            amp = (0.30 + wave * 0.70) * envelope
            half_h = max(6, amp * max_half)
            x = int(start_x + i * (bar_w + gap))
            p.drawLine(x, int(cy - half_h), x, int(cy + half_h))


class SpinnerWidget(QWidget):
    """Circular spinner — used for clean/dark themes during transcription."""

    VIEW_W = 72
    VIEW_H = 104

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setFixedSize(self.VIEW_W, self.VIEW_H)
        self.setStyleSheet("background: transparent;")
        self._angle = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    def _tick(self):
        self._angle = (self._angle + 6) % 360
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()
        size = 64
        rect = QRectF((w - size) / 2, (h - size) / 2, size, size)

        track = QColor(self.theme.mic_primary.red(),
                       self.theme.mic_primary.green(),
                       self.theme.mic_primary.blue(), 40)
        track_pen = QPen(track, 3)
        track_pen.setCapStyle(Qt.FlatCap)
        p.setPen(track_pen)
        p.setBrush(Qt.NoBrush)
        p.drawArc(rect, 0, 360 * 16)

        arc_pen = QPen(self.theme.mic_primary, 3)
        arc_pen.setCapStyle(Qt.FlatCap)
        p.setPen(arc_pen)
        start_angle = int((90 - self._angle) * 16)
        span = int(-270 * 16)
        p.drawArc(rect, start_angle, span)


# -------- Window ------------------------------------------------------------


class StatusWindow(BaseWindow):
    statusSignal = pyqtSignal(str)
    levelSignal = pyqtSignal(float)
    closeSignal = pyqtSignal()
    cancelRequested = pyqtSignal()
    finishRequested = pyqtSignal()

    def __init__(self, theme_name='lavender'):
        self.theme = get_theme(theme_name)
        super().__init__('WhisperWriter Status', 200, 220)
        self._corner_radius = 24
        self.title_bar.hide()
        # Global QApplication stylesheet paints QWidget with #1e1e1e — force
        # centralWidget transparent so our paintEvent draws the tile bg.
        self.main_widget.setStyleSheet("background: transparent;")
        self.main_widget.setAttribute(Qt.WA_TranslucentBackground, True)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self._status_name = 'recording'
        self.initStatusUI()
        self.statusSignal.connect(self.updateStatus)
        self.levelSignal.connect(self.updateLevels)

    def initStatusUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        theme = self.theme

        self.mic_widget = MicLevelWidget(theme)
        if theme.transcribe_style == 'spinner':
            self.transcribe_widget = SpinnerWidget(theme)
        else:
            self.transcribe_widget = WaveformWidget(theme)

        self.icon_stack = QStackedWidget()
        self.icon_stack.setStyleSheet("background: transparent;")
        self.icon_stack.addWidget(self.mic_widget)
        self.icon_stack.addWidget(self.transcribe_widget)
        self.icon_stack.setFixedSize(MicLevelWidget.VIEW_W, MicLevelWidget.VIEW_H)

        top_container = QWidget()
        top_container.setStyleSheet("background: transparent;")
        top_layout = QVBoxLayout(top_container)
        top_layout.setContentsMargins(16, 16, 16, 10)
        top_layout.addStretch(1)
        top_layout.addWidget(self.icon_stack, alignment=Qt.AlignCenter)
        top_layout.addStretch(1)

        self.divider = QFrame()
        self.divider.setFixedHeight(1)
        d = theme.divider
        self.divider.setStyleSheet(
            f"background: rgba({d.red()}, {d.green()}, {d.blue()}, {d.alpha()}); border: none;"
        )
        self.divider.setVisible(theme.show_divider)

        self.cancel_btn = CircleButton(theme, 'cross', size=20, parent=self.main_widget)
        self.cancel_btn.setToolTip('Cancel recording')
        self.cancel_btn.clicked.connect(self.cancelRequested)

        self.action_btn = PillButton(theme, 'Listening', 'Done')
        self.action_btn.setToolTip('Finish and transcribe')
        self.action_btn.clicked.connect(self.finishRequested)

        self.status_label = QLabel('Transcribing')
        self.status_label.setFont(QFont('Segoe UI', 13, QFont.Normal))
        t = theme.text
        self.status_label.setStyleSheet(
            f"color: rgba({t.red()},{t.green()},{t.blue()},{t.alpha()});"
            " background: transparent; font-weight: 400;"
        )
        self.status_label.setAlignment(Qt.AlignCenter)

        bottom_container = QWidget()
        bottom_container.setStyleSheet("background: transparent;")
        bottom_container.setFixedHeight(56)
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(12, 8, 12, 12)
        bottom_layout.setSpacing(0)
        bottom_layout.addWidget(self.action_btn, alignment=Qt.AlignCenter)
        bottom_layout.addWidget(self.status_label, alignment=Qt.AlignCenter)
        self.status_label.hide()

        self.main_layout.addWidget(top_container, 74)
        self.main_layout.addWidget(self.divider)
        self.main_layout.addWidget(bottom_container, 26)

    def paintEvent(self, event):
        radius = self._corner_radius
        theme = self.theme

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        if theme.border_width > 0:
            outer_rect = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)
            fill_path = QPainterPath()
            fill_path.addRoundedRect(outer_rect, radius - 1.5, radius - 1.5)
            grad = QLinearGradient(0, 0, 0, self.height())
            grad.setColorAt(0.0, theme.bg_top)
            grad.setColorAt(1.0, theme.bg_bot)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(grad))
            p.drawPath(fill_path)

            p.setPen(QPen(theme.border_color, theme.border_width))
            p.setBrush(Qt.NoBrush)
            p.drawPath(fill_path)

            inner_rect = QRectF(self.rect()).adjusted(3.5, 3.5, -3.5, -3.5)
            inner_path = QPainterPath()
            inner_path.addRoundedRect(
                inner_rect, max(2.0, radius - 3.5), max(2.0, radius - 3.5)
            )
            p.setPen(QPen(theme.highlight, 1))
            p.drawPath(inner_path)
            return

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)

        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, theme.bg_top)
        grad.setColorAt(1.0, theme.bg_bot)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawPath(path)

        highlight_path = QPainterPath()
        highlight_rect = rect.adjusted(1.5, 1.5, -1.5, -1.5)
        highlight_path.addRoundedRect(highlight_rect, radius - 1.5, radius - 1.5)
        p.setPen(QPen(theme.highlight, 1))
        p.setBrush(Qt.NoBrush)
        p.drawPath(highlight_path)

    def _pin_cancel_btn(self):
        if hasattr(self, 'cancel_btn') and self.cancel_btn is not None:
            parent = self.cancel_btn.parentWidget()
            if parent is None:
                return
            margin = 3
            size = self.cancel_btn.SIZE
            x = parent.width() - size - margin
            y = margin
            self.cancel_btn.setGeometry(x, y, size, size)
            self.cancel_btn.raise_()

    def show(self):
        window_width = self.width()
        window_height = self.height()
        saved = self._load_saved_position(window_width, window_height)
        if saved is not None:
            x, y = saved
        else:
            screen = QApplication.primaryScreen()
            screen_geometry = screen.geometry()
            x = (screen_geometry.width() - window_width) // 2
            y = screen_geometry.height() - window_height - 120
        self.move(x, y)
        self._pin_cancel_btn()
        super().show()

    def _load_saved_position(self, w, h):
        try:
            pos = ConfigManager.get_config_value('misc', 'status_window_position')
        except Exception:
            return None
        if not (isinstance(pos, (list, tuple)) and len(pos) == 2):
            return None
        try:
            x, y = int(pos[0]), int(pos[1])
        except (TypeError, ValueError):
            return None
        app = QApplication.instance()
        if app is None:
            return x, y
        for screen in app.screens():
            g = screen.availableGeometry()
            if (g.left() <= x <= g.right() - w + 1) and (g.top() <= y <= g.bottom() - h + 1):
                return x, y
        return None

    def _save_current_position(self):
        try:
            pos = self.pos()
            ConfigManager.set_config_value([pos.x(), pos.y()], 'misc', 'status_window_position')
            ConfigManager.save_config()
        except Exception as exc:
            print(f'[DBG] save status window position error: {exc}', flush=True)

    def mouseReleaseEvent(self, event):
        was_dragging = getattr(self, 'is_dragging', False)
        super().mouseReleaseEvent(event)
        if was_dragging:
            self._save_current_position()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._pin_cancel_btn()

    def showEvent(self, event):
        super().showEvent(event)
        self._pin_cancel_btn()

    def closeEvent(self, event):
        self.closeSignal.emit()
        super().closeEvent(event)

    @pyqtSlot(str)
    def updateStatus(self, status):
        self._status_name = status
        if status == 'recording':
            self.mic_widget.reset()
            self.icon_stack.setCurrentWidget(self.mic_widget)
            self.cancel_btn.setVisible(True)
            self.action_btn.setVisible(True)
            self.action_btn.setEnabled(True)
            self.action_btn.set_texts('Listening', 'Done')
            self.status_label.hide()
            self.show()
        elif status == 'transcribing':
            self.icon_stack.setCurrentWidget(self.transcribe_widget)
            self.cancel_btn.setVisible(False)
            self.action_btn.setVisible(False)
            self.status_label.setText('Transcribing')
            self.status_label.show()
        if status in ('idle', 'error', 'cancel'):
            self.close()

    @pyqtSlot(float)
    def updateLevels(self, level):
        try:
            self.mic_widget.set_level(level)
        except Exception as exc:
            print(f'[DBG] updateLevels error: {exc}', flush=True)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    status_window = StatusWindow('lavender')
    status_window.statusSignal.emit('recording')
    sys.exit(app.exec_())
