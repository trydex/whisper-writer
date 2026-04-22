import os
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QScrollArea, QWidget, QFrame, QSizePolicy
)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ui.base_window import BaseWindow


class HistoryWindow(BaseWindow):
    def __init__(self, history):
        super().__init__('Transcription History', 560, 520)
        self.history = history
        self._build_ui()

    def _build_ui(self):
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; }")

        self.list_container = QWidget()
        self.list_container.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(4, 4, 4, 4)
        self.list_layout.setSpacing(6)
        self.list_layout.addStretch(1)
        self.scroll.setWidget(self.list_container)

        self.main_layout.addWidget(self.scroll, 1)

        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 4, 0, 0)
        self.empty_label = QLabel('History is empty')
        self.empty_label.setStyleSheet("color: #b0b0b0; background: transparent; padding: 40px;")
        self.empty_label.setAlignment(Qt.AlignCenter)

        self.clear_button = QPushButton('Clear')
        self.clear_button.clicked.connect(self._on_clear)

        bottom.addStretch(1)
        bottom.addWidget(self.clear_button)
        self.main_layout.addLayout(bottom)

    def showEvent(self, event):
        self.refresh()
        super().showEvent(event)

    def refresh(self):
        while self.list_layout.count() > 0:
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        items = list(reversed(self.history.snapshot()))
        if not items:
            self.list_layout.addWidget(self.empty_label)
            self.list_layout.addStretch(1)
            return

        for ts, text in items:
            self.list_layout.addWidget(self._make_entry(ts, text))
        self.list_layout.addStretch(1)

    def _make_entry(self, ts, text):
        entry = QFrame()
        entry.setStyleSheet("""
            QFrame {
                background-color: rgba(45, 45, 52, 200);
                border: 1px solid #3f3f46;
                border-radius: 6px;
            }
        """)
        entry_layout = QHBoxLayout(entry)
        entry_layout.setContentsMargins(10, 8, 10, 8)
        entry_layout.setSpacing(10)

        time_label = QLabel(ts.strftime('%H:%M'))
        time_label.setStyleSheet("color: #8a8a8a; background: transparent; border: none;")
        time_label.setFixedWidth(40)
        time_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        text_label = QLabel(text)
        text_label.setWordWrap(True)
        text_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        text_label.setStyleSheet("color: #e6e6e6; background: transparent; border: none;")
        text_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        copy_button = QPushButton('Copy')
        copy_button.setFixedWidth(70)
        copy_button.clicked.connect(lambda _=False, t=text, b=copy_button: self._copy(t, b))

        entry_layout.addWidget(time_label)
        entry_layout.addWidget(text_label, 1)
        entry_layout.addWidget(copy_button, 0, Qt.AlignTop)
        return entry

    def _copy(self, text, button):
        QApplication.clipboard().setText(text)
        original = button.text()
        button.setText('Copied')
        button.setEnabled(False)
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(1200, lambda: (button.setText(original), button.setEnabled(True)))

    def _on_clear(self):
        self.history.clear()
        self.refresh()
