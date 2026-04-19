import sys
import os
import math
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer, QRectF, QPointF
from PyQt5.QtGui import QFont, QPainter, QPen, QColor, QLinearGradient, QPainterPath, QBrush
from PyQt5.QtWidgets import (
    QApplication, QLabel, QHBoxLayout, QVBoxLayout, QWidget, QFrame,
    QStackedWidget, QPushButton,
)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ui.base_window import BaseWindow


TILE_TEXT = QColor(67, 63, 92)        # richer deep indigo-violet
TILE_BG_TOP = QColor(206, 200, 232)   # brighter lavender
TILE_BG_BOT = QColor(192, 185, 222)   # brighter bottom
TILE_DIVIDER = QColor(67, 63, 92, 30)
TILE_HIGHLIGHT = QColor(255, 255, 255, 110)
FILL_LIGHT = QColor(160, 150, 200)    # #a096c8
FILL_MID = QColor(122, 111, 168)      # #7a6fa8
FILL_DARK = QColor(92, 82, 136)       # #5c5288


def _mic_paths():
    """SVG-derived paths from the reference preview.html, viewBox 72x104."""
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
    """Contour microphone with liquid-style level fill inside the capsule."""

    VIEW_W = 72
    VIEW_H = 104

    def __init__(self, parent=None):
        super().__init__(parent)
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
        # Peak-hold VU style: fast rise, slow fall — catches the eye.
        if self._target > self._level:
            self._level += (self._target - self._level) * 0.38
        else:
            self._level += (self._target - self._level) * 0.10
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        head, yoke, stem, base = _mic_paths()

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
        p.fillRect(fill_rect, FILL_MID)
        p.restore()

        pen = QPen(TILE_TEXT, 5.5)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawPath(head)
        p.drawPath(yoke)
        p.drawPath(stem)
        p.drawPath(base)


class CircleButton(QPushButton):
    """Minimal iOS-style icon button — contour icon, soft circular hover plate."""

    def __init__(self, icon_kind='cross', size=28, parent=None):
        super().__init__(parent)
        self.icon_kind = icon_kind
        self.SIZE = size
        from PyQt5.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
        self._hover = False
        self._pressed = False
        self.setFlat(True)
        # Local stylesheet MUST override global QPushButton min-width
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
        # Keep the widget square even if the layout gives us non-square geometry.
        side = min(self.width(), self.height())
        cx = self.width() / 2
        cy = self.height() / 2
        r = QRectF(cx - side / 2 + 0.5, cy - side / 2 + 0.5, side - 1, side - 1)

        if self._pressed:
            bg_alpha = 38
        elif self._hover:
            bg_alpha = 22
        else:
            bg_alpha = 0

        if bg_alpha > 0:
            p.setBrush(QBrush(QColor(79, 77, 96, bg_alpha)))
            p.setPen(Qt.NoPen)
            p.drawEllipse(r)

        # Faint icon by default, clearer on hover/press
        if self._pressed:
            icon_color = QColor(79, 77, 96, 255)
            stroke_w = 2.0
        elif self._hover:
            icon_color = QColor(79, 77, 96, 235)
            stroke_w = 1.9
        else:
            icon_color = QColor(79, 77, 96, 200)
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
        elif self.icon_kind == 'check':
            path = QPainterPath()
            path.moveTo(cx - s, cy + 0.4)
            path.lineTo(cx - 1.4, cy + s - 0.8)
            path.lineTo(cx + s + 0.4, cy - s + 1.2)
            p.drawPath(path)


class PillButton(QPushButton):
    """Ghost pill by default (outline only); fills on hover and swaps label."""

    OUTLINE = QColor(122, 111, 168, 200)
    FILL_HOVER = QColor(175, 165, 220)
    FILL_PRESS = QColor(155, 145, 205)
    FILL_DISABLED = QColor(200, 195, 225)
    TEXT_IDLE = QColor(122, 111, 168)
    TEXT_ACTIVE = QColor(67, 63, 92)
    TEXT_DISABLED = QColor(67, 63, 92, 150)

    def __init__(self, idle_text, hover_text=None, parent=None):
        super().__init__(idle_text, parent)
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
            p.setBrush(QBrush(self.FILL_DISABLED))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(r, radius, radius)
            p.setPen(self.TEXT_DISABLED)
        elif self._pressed:
            p.setBrush(QBrush(self.FILL_PRESS))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(r, radius, radius)
            p.setPen(QPen(QColor(255, 255, 255, 95), 1))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), radius - 0.5, radius - 0.5)
            p.setPen(self.TEXT_ACTIVE)
        elif self._hover:
            p.setBrush(QBrush(self.FILL_HOVER))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(r, radius, radius)
            p.setPen(QPen(QColor(255, 255, 255, 95), 1))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), radius - 0.5, radius - 0.5)
            p.setPen(self.TEXT_ACTIVE)
        else:
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(self.OUTLINE, 1.4))
            p.drawRoundedRect(r.adjusted(0.25, 0.25, -0.25, -0.25), radius - 0.25, radius - 0.25)
            p.setPen(self.TEXT_IDLE)

        p.setFont(self.font())
        p.drawText(r, Qt.AlignCenter, self.text())


class WaveformWidget(QWidget):
    """Animated vertical bars — shown while transcribing."""

    VIEW_W = 72
    VIEW_H = 104
    N_BARS = 7

    def __init__(self, parent=None):
        super().__init__(parent)
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

        pen = QPen(FILL_MID, 5.5)
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


class StatusWindow(BaseWindow):
    statusSignal = pyqtSignal(str)
    levelSignal = pyqtSignal(float)
    closeSignal = pyqtSignal()
    cancelRequested = pyqtSignal()
    finishRequested = pyqtSignal()

    def __init__(self):
        super().__init__('WhisperWriter Status', 200, 220)
        self._corner_radius = 24
        self.title_bar.hide()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self._status_name = 'recording'
        self.initStatusUI()
        self.statusSignal.connect(self.updateStatus)
        self.levelSignal.connect(self.updateLevels)

    def initStatusUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)

        self.mic_widget = MicLevelWidget()
        self.waveform_widget = WaveformWidget()
        self.icon_stack = QStackedWidget()
        self.icon_stack.setStyleSheet("background: transparent;")
        self.icon_stack.addWidget(self.mic_widget)
        self.icon_stack.addWidget(self.waveform_widget)
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
        self.divider.setStyleSheet("background: rgba(79, 77, 96, 22); border: none;")

        # Close button lives on the central widget (top-right corner), very subtle.
        self.cancel_btn = CircleButton('cross', size=20, parent=self.main_widget)
        self.cancel_btn.setToolTip('Cancel recording')
        self.cancel_btn.clicked.connect(self.cancelRequested)

        # Action pill (recording) — ghost style, swaps label to "Done" on hover.
        self.action_btn = PillButton('Listening', 'Done')
        self.action_btn.setToolTip('Finish and transcribe')
        self.action_btn.clicked.connect(self.finishRequested)

        # Plain status label shown during transcription (no button).
        self.status_label = QLabel('Transcribing')
        self.status_label.setFont(QFont('Segoe UI', 13, QFont.Normal))
        self.status_label.setStyleSheet("color: #7a6fa8; background: transparent; font-weight: 400;")
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
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, TILE_BG_TOP)
        grad.setColorAt(1.0, TILE_BG_BOT)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawPath(path)

        highlight_path = QPainterPath()
        highlight_rect = rect.adjusted(1.5, 1.5, -1.5, -1.5)
        highlight_path.addRoundedRect(highlight_rect, radius - 1.5, radius - 1.5)
        p.setPen(QPen(TILE_HIGHLIGHT, 1))
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
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        window_width = self.width()
        window_height = self.height()
        x = (screen_geometry.width() - window_width) // 2
        y = screen_geometry.height() - window_height - 120
        self.move(x, y)
        self._pin_cancel_btn()
        super().show()

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
            self.icon_stack.setCurrentWidget(self.waveform_widget)
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
    status_window = StatusWindow()
    status_window.statusSignal.emit('recording')
    sys.exit(app.exec_())
