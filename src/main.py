import os
import sys
import time
import ctypes
import winsound
from pathlib import Path


_kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
_ERROR_ALREADY_EXISTS = 183


def _acquire_singleton_lock(name=r"Global\WhisperWriter_SingleInstance", timeout_s=8.0):
    deadline = time.time() + timeout_s
    while True:
        handle = _kernel32.CreateMutexW(None, False, name)
        err = ctypes.get_last_error()
        if err != _ERROR_ALREADY_EXISTS:
            return handle
        _kernel32.CloseHandle(handle)
        if time.time() > deadline:
            return None
        time.sleep(0.25)


_singleton_lock = _acquire_singleton_lock()
if _singleton_lock is None:
    print('WhisperWriter is already running — exiting.', flush=True)
    sys.exit(0)


def _ensure_nvidia_dlls_on_path() -> None:
    try:
        import importlib.util as _u
        spec = _u.find_spec("nvidia")
    except ImportError:
        return
    if spec is None or not spec.submodule_search_locations:
        return
    for root in spec.submodule_search_locations:
        root_path = Path(root)
        for lib_dir in list(root_path.glob("*/bin")) + list(root_path.glob("*/lib")):
            if lib_dir.is_dir() and hasattr(os, "add_dll_directory"):
                try:
                    os.add_dll_directory(str(lib_dir))
                except (FileNotFoundError, OSError):
                    pass
            os.environ["PATH"] = str(lib_dir) + os.pathsep + os.environ.get("PATH", "")


_ensure_nvidia_dlls_on_path()

# Load CUDA model BEFORE any PyQt5 imports — PyQt5 DLL loading conflicts with CTranslate2 CUDA init.
from utils import ConfigManager
from transcription import create_local_model

ConfigManager.initialize()


def _ensure_default_sound_paths():
    assets_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets'))
    defaults = {
        'recording_start_sound_path': os.path.join(assets_dir, 'ping-up.wav'),
        'recording_stop_sound_path': os.path.join(assets_dir, 'ping-down.wav'),
    }
    changed = False
    for key, default_path in defaults.items():
        if not ConfigManager.get_config_value('misc', key) and os.path.isfile(default_path):
            ConfigManager.set_config_value(default_path, 'misc', key)
            changed = True
    if changed and ConfigManager.config_file_exists():
        try:
            ConfigManager.save_config()
        except Exception as exc:
            print(f'[DBG] save_config failed: {exc}', flush=True)


_ensure_default_sound_paths()

_PRELOADED_MODEL = None
if ConfigManager.config_file_exists() and not ConfigManager.get_config_section('model_options').get('use_api'):
    _PRELOADED_MODEL = create_local_model()

print('[DBG] before PyQt5 imports', flush=True)
from audioplayer import AudioPlayer
from pynput.keyboard import Controller
from PyQt5.QtCore import QObject, QProcess
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction, QMessageBox
print('[DBG] PyQt5 imports ok', flush=True)

from key_listener import KeyListener
from result_thread import ResultThread
from ui.settings_window import SettingsWindow
from ui.status_window import StatusWindow
from input_simulation import InputSimulator
print('[DBG] local imports ok', flush=True)


class WhisperWriterApp(QObject):
    def __init__(self):
        """
        Initialize the application, opening settings window if no configuration file is found.
        """
        super().__init__()
        self._preloaded_model = _PRELOADED_MODEL
        print('[DBG] init: creating QApplication', flush=True)

        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.app.setWindowIcon(self._build_tray_icon())
        self.app.setStyle('Fusion')
        theme = (ConfigManager.get_config_value('misc', 'theme') or 'dark').lower()
        self.app.setStyleSheet(self._light_stylesheet() if theme == 'light' else self._dark_stylesheet())
        print('[DBG] init: QApplication ok', flush=True)

        self.settings_window = SettingsWindow()
        self.settings_window.settings_closed.connect(self.on_settings_closed)
        self.settings_window.settings_saved.connect(self.restart_app)
        print('[DBG] init: settings_window ok', flush=True)

        if ConfigManager.config_file_exists():
            print('[DBG] init: calling initialize_components', flush=True)
            self.initialize_components()
            print('[DBG] init: initialize_components done', flush=True)
        else:
            print('No valid configuration file found. Opening settings window...')
            self.settings_window.show()

    def _dark_stylesheet(self):
        return """
            QWidget { background-color: #1e1e1e; color: #d4d4d4; font-family: 'Segoe UI'; font-size: 10pt; }
            QMainWindow, QDialog { background-color: #1e1e1e; }
            QLabel { color: #d4d4d4; background: transparent; }
            QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QAbstractSpinBox {
                background-color: #2d2d30;
                color: #d4d4d4;
                border: 1px solid #3f3f46;
                padding: 5px 8px;
                border-radius: 4px;
                selection-background-color: #094771;
                selection-color: #ffffff;
            }
            QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
                border: 1px solid #007acc;
            }
            QComboBox::drop-down { border: none; width: 22px; }
            QComboBox QAbstractItemView {
                background-color: #2d2d30;
                color: #d4d4d4;
                border: 1px solid #3f3f46;
                selection-background-color: #094771;
                selection-color: #ffffff;
                outline: 0;
            }
            QPushButton {
                background-color: #2d2d30;
                color: #d4d4d4;
                border: 1px solid #3f3f46;
                padding: 7px 16px;
                border-radius: 4px;
                min-width: 72px;
            }
            QPushButton:hover { background-color: #3e3e42; border-color: #555; }
            QPushButton:pressed { background-color: #094771; border-color: #007acc; }
            QPushButton:disabled { color: #6b6b6b; background-color: #252526; border-color: #333; }
            QCheckBox, QRadioButton { color: #d4d4d4; spacing: 6px; background: transparent; }
            QCheckBox::indicator, QRadioButton::indicator { width: 16px; height: 16px; }
            QCheckBox::indicator:unchecked {
                background-color: #2d2d30; border: 1px solid #555; border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #007acc; border: 1px solid #007acc; border-radius: 3px;
            }
            QTabWidget::pane { border: 1px solid #3f3f46; background-color: #1e1e1e; top: -1px; }
            QTabBar::tab {
                background: #252526;
                color: #969696;
                padding: 8px 18px;
                border: 1px solid #3f3f46;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected { background: #1e1e1e; color: #ffffff; }
            QTabBar::tab:hover:!selected { background: #2d2d30; color: #d4d4d4; }
            QMenu {
                background-color: #252526;
                color: #d4d4d4;
                border: 1px solid #3f3f46;
                padding: 4px;
            }
            QMenu::item { padding: 6px 24px; border-radius: 3px; }
            QMenu::item:selected { background-color: #094771; color: #ffffff; }
            QMessageBox { background-color: #1e1e1e; }
            QMessageBox QLabel { color: #d4d4d4; }
            QScrollBar:vertical { background: #1e1e1e; width: 12px; margin: 0; }
            QScrollBar::handle:vertical { background: #424242; border-radius: 5px; min-height: 24px; }
            QScrollBar::handle:vertical:hover { background: #4f4f4f; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar:horizontal { background: #1e1e1e; height: 12px; margin: 0; }
            QScrollBar::handle:horizontal { background: #424242; border-radius: 5px; min-width: 24px; }
            QScrollBar::handle:horizontal:hover { background: #4f4f4f; }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
            QToolTip {
                background-color: #252526;
                color: #d4d4d4;
                border: 1px solid #3f3f46;
                padding: 4px;
            }
        """

    def _light_stylesheet(self):
        return """
            QWidget { background-color: #f5f5f7; color: #202124; font-family: 'Segoe UI'; font-size: 10pt; }
            QMainWindow, QDialog { background-color: #f5f5f7; }
            QLabel { color: #202124; background: transparent; }
            QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QAbstractSpinBox {
                background-color: #ffffff;
                color: #202124;
                border: 1px solid #cfd2d6;
                padding: 5px 8px;
                border-radius: 4px;
                selection-background-color: #cfe2ff;
                selection-color: #000000;
            }
            QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
                border: 1px solid #0066cc;
            }
            QComboBox::drop-down { border: none; width: 22px; }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #202124;
                border: 1px solid #cfd2d6;
                selection-background-color: #cfe2ff;
                selection-color: #000000;
                outline: 0;
            }
            QPushButton {
                background-color: #ffffff;
                color: #202124;
                border: 1px solid #cfd2d6;
                padding: 7px 16px;
                border-radius: 4px;
                min-width: 72px;
            }
            QPushButton:hover { background-color: #eef1f4; border-color: #b0b4ba; }
            QPushButton:pressed { background-color: #cfe2ff; border-color: #0066cc; }
            QPushButton:disabled { color: #a0a0a0; background-color: #f0f0f2; border-color: #e2e4e8; }
            QCheckBox, QRadioButton { color: #202124; spacing: 6px; background: transparent; }
            QCheckBox::indicator, QRadioButton::indicator { width: 16px; height: 16px; }
            QCheckBox::indicator:unchecked {
                background-color: #ffffff; border: 1px solid #b0b4ba; border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #0066cc; border: 1px solid #0066cc; border-radius: 3px;
            }
            QTabWidget::pane { border: 1px solid #cfd2d6; background-color: #f5f5f7; top: -1px; }
            QTabBar::tab {
                background: #e8e9ec;
                color: #505358;
                padding: 8px 18px;
                border: 1px solid #cfd2d6;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected { background: #f5f5f7; color: #202124; }
            QTabBar::tab:hover:!selected { background: #eef1f4; }
            QMenu {
                background-color: #ffffff;
                color: #202124;
                border: 1px solid #cfd2d6;
                padding: 4px;
            }
            QMenu::item { padding: 6px 24px; border-radius: 3px; }
            QMenu::item:selected { background-color: #cfe2ff; color: #000000; }
            QMessageBox { background-color: #f5f5f7; }
            QMessageBox QLabel { color: #202124; }
            QScrollBar:vertical { background: #f5f5f7; width: 12px; margin: 0; }
            QScrollBar::handle:vertical { background: #c5c8cd; border-radius: 5px; min-height: 24px; }
            QScrollBar::handle:vertical:hover { background: #a8adb3; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar:horizontal { background: #f5f5f7; height: 12px; margin: 0; }
            QScrollBar::handle:horizontal { background: #c5c8cd; border-radius: 5px; min-width: 24px; }
            QScrollBar::handle:horizontal:hover { background: #a8adb3; }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
            QToolTip {
                background-color: #ffffff;
                color: #202124;
                border: 1px solid #cfd2d6;
                padding: 4px;
            }
        """

    def initialize_components(self):
        """
        Initialize the components of the application.
        """
        self.local_model = self._preloaded_model
        print('[DBG] ic: InputSimulator()', flush=True)
        self.input_simulator = InputSimulator()
        print('[DBG] ic: KeyListener()', flush=True)
        self.key_listener = KeyListener()
        print('[DBG] ic: KeyListener ok', flush=True)
        self.key_listener.add_callback("on_activate", self.on_activation)
        self.key_listener.add_callback("on_deactivate", self.on_deactivation)

        from pynput import keyboard as _pynput_kb
        self._pynput_kb = _pynput_kb
        self._cancel_listener = _pynput_kb.Listener(on_press=self._on_cancel_key)
        self._cancel_listener.daemon = True
        self._cancel_listener.start()

        self.result_thread = None

        if not ConfigManager.get_config_value('misc', 'hide_status_window'):
            theme_name = ConfigManager.get_config_value('misc', 'status_window_theme') or 'lavender'
            self.status_window = StatusWindow(theme_name)

        self.create_tray_icon()
        self.key_listener.start()

    def _build_tray_icon(self):
        from PyQt5.QtCore import Qt, QRectF
        from PyQt5.QtGui import QPixmap, QPainter, QColor, QBrush, QPen, QLinearGradient
        size = 64
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        grad = QLinearGradient(0, 0, size, size)
        grad.setColorAt(0.0, QColor('#6366f1'))
        grad.setColorAt(1.0, QColor('#8b5cf6'))
        p.setBrush(QBrush(grad))
        p.setPen(Qt.NoPen)
        p.drawEllipse(3, 3, size - 6, size - 6)
        p.setBrush(QBrush(QColor('white')))
        body = QRectF(size / 2 - 7, 16, 14, 22)
        p.drawRoundedRect(body, 7, 7)
        pen = QPen(QColor('white'), 3)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawArc(int(size / 2 - 12), 28, 24, 20, 180 * 16, 180 * 16)
        p.drawLine(int(size / 2), 48, int(size / 2), 54)
        p.drawLine(int(size / 2 - 7), 54, int(size / 2 + 7), 54)
        p.end()
        return QIcon(pix)

    def create_tray_icon(self):
        """
        Create the system tray icon and its context menu.
        """
        self.tray_icon = QSystemTrayIcon(self._build_tray_icon(), self.app)
        self.tray_icon.setToolTip('WhisperWriter')
        self.tray_icon.activated.connect(self._on_tray_activated)

        tray_menu = QMenu()

        settings_action = QAction('Open Settings', self.app)
        settings_action.triggered.connect(self.settings_window.show)
        tray_menu.addAction(settings_action)

        exit_action = QAction('Exit', self.app)
        exit_action.triggered.connect(self.exit_app)
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        print(f'[DBG] tray activated reason={reason}', flush=True)
        if reason == QSystemTrayIcon.DoubleClick:
            self.settings_window.show()
            self.settings_window.raise_()
            self.settings_window.activateWindow()

    def cleanup(self):
        if self.key_listener:
            self.key_listener.stop()
        if self.input_simulator:
            self.input_simulator.cleanup()

    def exit_app(self):
        """
        Exit the application.
        """
        self.cleanup()
        QApplication.quit()

    def restart_app(self):
        """Restart the application to apply the new settings."""
        print('[DBG] restart_app called', flush=True)
        self.cleanup()
        script_path = os.path.abspath(sys.argv[0])
        work_dir = os.path.dirname(os.path.dirname(script_path))
        QProcess.startDetached(sys.executable, [script_path] + sys.argv[1:], work_dir)
        os._exit(0)

    def on_settings_closed(self):
        """
        If settings is closed without saving on first run, initialize the components with default values.
        """
        if not os.path.exists(os.path.join('src', 'config.yaml')):
            QMessageBox.information(
                self.settings_window,
                'Using Default Values',
                'Settings closed without saving. Default values are being used.'
            )
            self.initialize_components()

    def _on_cancel_key(self, key):
        try:
            if key == self._pynput_kb.Key.esc:
                rt = self.result_thread
                if rt is not None and rt.isRunning() and rt.is_recording:
                    print('[DBG] ESC cancel', flush=True)
                    self._play_feedback('ping-down.wav')
                    rt.cancel()
        except Exception:
            pass

    def _resolve_sound_path(self, filename):
        cfg_map = {
            'ping-up.wav': 'recording_start_sound_path',
            'ping-down.wav': 'recording_stop_sound_path',
        }
        cfg_key = cfg_map.get(filename)
        if cfg_key:
            user_path = ConfigManager.get_config_value('misc', cfg_key)
            if user_path and os.path.isfile(user_path):
                return user_path
        return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets', filename))

    def _play_feedback(self, filename):
        try:
            path = self._resolve_sound_path(filename)
            if os.path.isfile(path):
                winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
        except Exception as exc:
            print(f'[DBG] audio feedback error: {exc}', flush=True)

    def on_activation(self):
        """
        Called when the activation key combination is pressed.
        """
        print('[DBG] on_activation', flush=True)
        if self.result_thread and self.result_thread.isRunning():
            recording_mode = ConfigManager.get_config_value('recording_options', 'recording_mode')
            if recording_mode == 'press_to_toggle':
                self._play_feedback('ping-down.wav')
                self.result_thread.stop_recording()
            elif recording_mode == 'continuous':
                self._play_feedback('ping-down.wav')
                self.stop_result_thread()
            return

        self._play_feedback('ping-up.wav')
        self.start_result_thread()

    def on_deactivation(self):
        """
        Called when the activation key combination is released.
        """
        if ConfigManager.get_config_value('recording_options', 'recording_mode') == 'hold_to_record':
            if self.result_thread and self.result_thread.isRunning():
                self.result_thread.stop_recording()

    def start_result_thread(self):
        """
        Start the result thread to record audio and transcribe it.
        """
        print('[DBG] start_result_thread', flush=True)
        if self.result_thread and self.result_thread.isRunning():
            return

        self.result_thread = ResultThread(self.local_model)
        if not ConfigManager.get_config_value('misc', 'hide_status_window'):
            self.result_thread.statusSignal.connect(self.status_window.updateStatus)
            self.result_thread.levelSignal.connect(self.status_window.updateLevels)
            self.status_window.closeSignal.connect(self.stop_result_thread)
            if not getattr(self, '_ui_buttons_wired', False):
                self.status_window.cancelRequested.connect(self._ui_cancel_recording)
                self.status_window.finishRequested.connect(self._ui_finish_recording)
                self._ui_buttons_wired = True
        self.result_thread.resultSignal.connect(self.on_transcription_complete)
        self.result_thread.start()

    def _ui_cancel_recording(self):
        rt = self.result_thread
        if rt is not None and rt.isRunning() and rt.is_recording:
            self._play_feedback('ping-down.wav')
            rt.cancel()

    def _ui_finish_recording(self):
        rt = self.result_thread
        if rt is not None and rt.isRunning() and rt.is_recording:
            self._play_feedback('ping-down.wav')
            rt.stop_recording()

    def stop_result_thread(self):
        """
        Stop the result thread.
        """
        if self.result_thread and self.result_thread.isRunning():
            self.result_thread.stop()

    def on_transcription_complete(self, result):
        """
        When the transcription is complete, type the result and start listening for the activation key again.
        """
        self.input_simulator.typewrite(result)

        if ConfigManager.get_config_value('misc', 'noise_on_completion'):
            AudioPlayer(os.path.join('assets', 'beep.wav')).play(block=True)

        if ConfigManager.get_config_value('recording_options', 'recording_mode') == 'continuous':
            self.start_result_thread()
        else:
            self.key_listener.start()

    def run(self):
        """
        Start the application.
        """
        sys.exit(self.app.exec_())


if __name__ == '__main__':
    print('[DBG] building app', flush=True)
    app = WhisperWriterApp()
    print('[DBG] app built, running event loop', flush=True)
    app.run()
