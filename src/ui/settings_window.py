import os
import sys
from dotenv import set_key, load_dotenv
from PyQt5.QtWidgets import (
    QApplication, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QCheckBox,
    QMessageBox, QTabWidget, QWidget, QSizePolicy, QSpacerItem, QToolButton, QStyle, QFileDialog
)
from PyQt5.QtCore import Qt, QCoreApplication, QProcess, pyqtSignal

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ui.base_window import BaseWindow
from utils import ConfigManager

load_dotenv()

class SettingsWindow(BaseWindow):
    settings_closed = pyqtSignal()
    settings_saved = pyqtSignal()

    def __init__(self):
        """Initialize the settings window."""
        super().__init__('Settings', 700, 700)
        self.schema = ConfigManager.get_schema()
        self.init_settings_ui()

    def init_settings_ui(self):
        """Initialize the settings user interface."""
        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        self.create_tabs()
        self.create_buttons()

        # Connect the use_api checkbox state change
        self.use_api_checkbox = self.findChild(QCheckBox, 'model_options_use_api_input')
        if self.use_api_checkbox:
            self.use_api_checkbox.stateChanged.connect(lambda: self.toggle_api_local_options(self.use_api_checkbox.isChecked()))
            self.toggle_api_local_options(self.use_api_checkbox.isChecked())

    def create_tabs(self):
        """Create tabs for each category in the schema."""
        for category, settings in self.schema.items():
            tab = QWidget()
            tab_layout = QVBoxLayout()
            tab.setLayout(tab_layout)
            self.tabs.addTab(tab, category.replace('_', ' ').capitalize())

            self.create_settings_widgets(tab_layout, category, settings)
            tab_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

    def create_settings_widgets(self, layout, category, settings):
        """Create widgets for each setting in a category."""
        for sub_category, sub_settings in settings.items():
            if isinstance(sub_settings, dict) and 'value' in sub_settings:
                self.add_setting_widget(layout, sub_category, sub_settings, category)
            else:
                for key, meta in sub_settings.items():
                    self.add_setting_widget(layout, key, meta, category, sub_category)

    def create_buttons(self):
        """Create reset and save buttons."""
        reset_button = QPushButton('Reset to saved settings')
        reset_button.clicked.connect(self.reset_settings)
        self.main_layout.addWidget(reset_button)

        save_button = QPushButton('Save')
        save_button.clicked.connect(self.save_settings)
        self.main_layout.addWidget(save_button)

    def add_setting_widget(self, layout, key, meta, category, sub_category=None):
        """Add a setting widget to the layout."""
        item_layout = QHBoxLayout()
        label = QLabel(f"{key.replace('_', ' ').capitalize()}:")
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        widget = self.create_widget_for_type(key, meta, category, sub_category)
        if not widget:
            return

        help_button = self.create_help_button(meta.get('description', ''))

        item_layout.addWidget(label)
        if isinstance(widget, QWidget):
            item_layout.addWidget(widget)
        else:
            item_layout.addLayout(widget)
        item_layout.addWidget(help_button)
        layout.addLayout(item_layout)

        # Set object names for the widget, label, and help button
        widget_name = f"{category}_{sub_category}_{key}_input" if sub_category else f"{category}_{key}_input"
        label_name = f"{category}_{sub_category}_{key}_label" if sub_category else f"{category}_{key}_label"
        help_name = f"{category}_{sub_category}_{key}_help" if sub_category else f"{category}_{key}_help"
        
        label.setObjectName(label_name)
        help_button.setObjectName(help_name)
        
        if isinstance(widget, QWidget):
            widget.setObjectName(widget_name)
        else:
            # If it's a layout (for model_path), set the object name on the QLineEdit
            line_edit = widget.itemAt(0).widget()
            if isinstance(line_edit, QLineEdit):
                line_edit.setObjectName(widget_name)

    def create_widget_for_type(self, key, meta, category, sub_category):
        """Create a widget based on the meta type."""
        meta_type = meta.get('type')
        current_value = self.get_config_value(category, sub_category, key, meta)

        if meta_type == 'bool':
            return self.create_checkbox(current_value, key)
        elif meta_type == 'str' and 'options' in meta:
            return self.create_combobox(current_value, meta['options'])
        elif meta_type == 'str':
            return self.create_line_edit(current_value, key)
        elif meta_type in ['int', 'float']:
            return self.create_line_edit(str(current_value))
        return None

    def create_checkbox(self, value, key):
        widget = QCheckBox()
        widget.setChecked(value)
        if key == 'use_api':
            widget.setObjectName('model_options_use_api_input')
        return widget

    def create_combobox(self, value, options):
        widget = QComboBox()
        widget.addItems(options)
        widget.setCurrentText(value)
        return widget

    def create_line_edit(self, value, key=None):
        widget = QLineEdit(value or '')
        if key == 'api_key':
            widget.setEchoMode(QLineEdit.Password)
            widget.setText(os.getenv('OPENAI_API_KEY') or value or '')
        elif key == 'model_path':
            layout = QHBoxLayout()
            layout.addWidget(widget)
            browse_button = QPushButton('Browse')
            browse_button.clicked.connect(lambda: self.browse_model_path(widget))
            layout.addWidget(browse_button)
            layout.setContentsMargins(0, 0, 0, 0)
            container = QWidget()
            container.setLayout(layout)
            return container
        elif key in ('recording_start_sound_path', 'recording_stop_sound_path'):
            return self._create_sound_picker(value)
        return widget

    def _scan_wav_files(self):
        assets_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'assets'))
        if not os.path.isdir(assets_dir):
            return assets_dir, []
        files = sorted(f for f in os.listdir(assets_dir) if f.lower().endswith('.wav'))
        return assets_dir, files

    def _create_sound_picker(self, current_value):
        assets_dir, wav_files = self._scan_wav_files()

        combo = QComboBox()
        combo.setEditable(False)
        combo.addItem('(none)', userData='')
        for name in wav_files:
            combo.addItem(name, userData=os.path.join(assets_dir, name))
        if current_value:
            idx = combo.findData(current_value)
            if idx < 0:
                combo.addItem(os.path.basename(current_value), userData=current_value)
                idx = combo.count() - 1
            combo.setCurrentIndex(idx)

        play_button = QPushButton('▶')
        play_button.setFixedWidth(40)
        play_button.setToolTip('Preview selected sound')

        def _play():
            import winsound
            path = combo.currentData() or ''
            if path and os.path.isfile(path):
                winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
        play_button.clicked.connect(_play)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(combo, 1)
        layout.addWidget(play_button)

        container = QWidget()
        container.setLayout(layout)
        container.setProperty('is_sound_picker', True)
        return container

    def create_help_button(self, description):
        help_button = QToolButton()
        help_button.setIcon(self.style().standardIcon(QStyle.SP_MessageBoxQuestion))
        help_button.setAutoRaise(True)
        help_button.setToolTip(description)
        help_button.setCursor(Qt.PointingHandCursor)
        help_button.setFocusPolicy(Qt.TabFocus)
        help_button.clicked.connect(lambda: self.show_description(description))
        return help_button

    def get_config_value(self, category, sub_category, key, meta):
        if sub_category:
            value = ConfigManager.get_config_value(category, sub_category, key)
        else:
            value = ConfigManager.get_config_value(category, key)
        return meta['value'] if value is None else value

    def browse_model_path(self, widget):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Whisper Model File", "", "Model Files (*.bin);;All Files (*)")
        if file_path:
            widget.setText(file_path)

    def browse_wav_path(self, widget):
        assets_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'assets'))
        file_path, _ = QFileDialog.getOpenFileName(self, "Select WAV sound", assets_dir, "WAV Files (*.wav);;All Files (*)")
        if file_path:
            widget.setText(file_path)

    def show_description(self, description):
        """Show a description dialog."""
        QMessageBox.information(self, 'Description', description)

    def save_settings(self):
        """Save the settings to the config file and .env file."""
        try:
            self._save_settings_impl()
        except Exception as exc:
            import traceback
            print(f'[DBG] save_settings failed: {exc}', flush=True)
            traceback.print_exc()

    # Keys whose change requires a full app restart. Everything else applies live because
    # the rest of the code reads config on every use via ConfigManager.get_config_*.
    _RESTART_REQUIRED_KEYS = frozenset({
        ('model_options', 'use_api'),
        ('model_options', 'local', 'model'),
        ('model_options', 'local', 'model_path'),
        ('model_options', 'local', 'device'),
        ('model_options', 'local', 'compute_type'),
        ('model_options', 'api', 'base_url'),
        ('model_options', 'api', 'model'),
        ('recording_options', 'activation_key'),
        ('recording_options', 'input_backend'),
        ('recording_options', 'sample_rate'),
        ('recording_options', 'sound_device'),
        ('post_processing', 'input_method'),
        ('misc', 'theme'),
    })

    def _changed_keys(self, old, new, path=()):
        """Yield tuple paths for scalar leaves that differ between old and new configs."""
        if isinstance(old, dict) and isinstance(new, dict):
            for key in set(old) | set(new):
                yield from self._changed_keys(old.get(key), new.get(key), path + (key,))
        elif old != new:
            yield path

    def _save_settings_impl(self):
        import copy
        old_config = copy.deepcopy(ConfigManager._instance.config)

        self.iterate_settings(self.save_setting)

        # Save the API key to the .env file
        api_key = ConfigManager.get_config_value('model_options', 'api', 'api_key') or ''
        set_key('.env', 'OPENAI_API_KEY', api_key)
        os.environ['OPENAI_API_KEY'] = api_key

        # Remove the API key from the config
        ConfigManager.set_config_value(None, 'model_options', 'api', 'api_key')

        if ConfigManager._instance.config == old_config:
            self.close()
            return

        ConfigManager.save_config()

        changed = list(self._changed_keys(old_config, ConfigManager._instance.config))
        needs_restart = any(path in self._RESTART_REQUIRED_KEYS for path in changed)
        if needs_restart:
            QMessageBox.information(self, 'Settings Saved', 'Settings have been saved. The application will now restart.')
            self.settings_saved.emit()
        self.close()

    def save_setting(self, widget, category, sub_category, key, meta):
        value = self.get_widget_value_typed(widget, meta.get('type'))
        if sub_category:
            ConfigManager.set_config_value(value, category, sub_category, key)
        else:
            ConfigManager.set_config_value(value, category, key)

    def _has_unsaved_changes(self):
        """Compare current widget values against saved config."""
        import copy
        saved_config = copy.deepcopy(ConfigManager._instance.config)
        try:
            self.iterate_settings(self.save_setting)
            return ConfigManager._instance.config != saved_config
        except Exception as exc:
            import traceback
            print(f'[DBG] _has_unsaved_changes failed: {exc}', flush=True)
            traceback.print_exc()
            return False
        finally:
            ConfigManager._instance.config = saved_config

    def reset_settings(self):
        """Reset the settings to the saved values."""
        ConfigManager.reload_config()
        self.update_widgets_from_config()

    def update_widgets_from_config(self):
        """Update all widgets with values from the current configuration."""
        self.iterate_settings(self.update_widget_value)

    def update_widget_value(self, widget, category, sub_category, key, meta):
        """Update a single widget with the value from the configuration."""
        if sub_category:
            config_value = ConfigManager.get_config_value(category, sub_category, key)
        else:
            config_value = ConfigManager.get_config_value(category, key)

        self.set_widget_value(widget, config_value, meta.get('type'))

    def set_widget_value(self, widget, value, value_type):
        """Set the value of the widget."""
        if isinstance(widget, QCheckBox):
            widget.setChecked(value)
        elif isinstance(widget, QComboBox):
            widget.setCurrentText(value)
        elif isinstance(widget, QLineEdit):
            widget.setText(str(value) if value is not None else '')
        elif isinstance(widget, QWidget) and widget.layout():
            first = widget.layout().itemAt(0).widget()
            if isinstance(first, QLineEdit):
                first.setText(str(value) if value is not None else '')
            elif isinstance(first, QComboBox):
                if widget.property('is_sound_picker'):
                    idx = first.findData(value or '')
                    if idx < 0 and value:
                        first.addItem(os.path.basename(value), userData=value)
                        idx = first.count() - 1
                    if idx >= 0:
                        first.setCurrentIndex(idx)
                else:
                    first.setCurrentText(str(value) if value is not None else '')

    def get_widget_value_typed(self, widget, value_type):
        """Get the value of the widget with proper typing."""
        if isinstance(widget, QCheckBox):
            return widget.isChecked()
        elif isinstance(widget, QComboBox):
            return widget.currentText() or None
        elif isinstance(widget, QLineEdit):
            text = widget.text()
            if value_type == 'int':
                return int(text) if text else None
            elif value_type == 'float':
                return float(text) if text else None
            else:
                return text or None
        elif isinstance(widget, QWidget) and widget.layout():
            first = widget.layout().itemAt(0).widget()
            if isinstance(first, QLineEdit):
                return first.text() or None
            if isinstance(first, QComboBox):
                if widget.property('is_sound_picker'):
                    return first.currentData() or None
                return first.currentText().strip() or None
        return None

    def toggle_api_local_options(self, use_api):
        """Toggle visibility of API and local options."""
        self.iterate_settings(lambda w, c, s, k, m: self.toggle_widget_visibility(w, c, s, k, use_api))

    def toggle_widget_visibility(self, widget, category, sub_category, key, use_api):
        if sub_category in ['api', 'local']:
            widget.setVisible(use_api if sub_category == 'api' else not use_api)
            
            # Also toggle visibility of the corresponding label and help button
            label = self.findChild(QLabel, f"{category}_{sub_category}_{key}_label")
            help_button = self.findChild(QToolButton, f"{category}_{sub_category}_{key}_help")
            
            if label:
                label.setVisible(use_api if sub_category == 'api' else not use_api)
            if help_button:
                help_button.setVisible(use_api if sub_category == 'api' else not use_api)


    def iterate_settings(self, func):
        """Iterate over all settings and apply a function to each."""
        for category, settings in self.schema.items():
            for sub_category, sub_settings in settings.items():
                if isinstance(sub_settings, dict) and 'value' in sub_settings:
                    widget = self.findChild(QWidget, f"{category}_{sub_category}_input")
                    if widget:
                        func(widget, category, None, sub_category, sub_settings)
                else:
                    for key, meta in sub_settings.items():
                        widget = self.findChild(QWidget, f"{category}_{sub_category}_{key}_input")
                        if widget:
                            func(widget, category, sub_category, key, meta)

    def closeEvent(self, event):
        """Confirm before closing the settings window without saving."""
        try:
            unsaved = self._has_unsaved_changes()
        except Exception as exc:
            print(f'[DBG] closeEvent _has_unsaved_changes error: {exc}', flush=True)
            unsaved = False
        if not unsaved:
            self.settings_closed.emit()
            super().closeEvent(event)
            return
        reply = QMessageBox.question(
            self,
            'Close without saving?',
            'Are you sure you want to close without saving?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            ConfigManager.reload_config()  # Revert to last saved configuration
            self.update_widgets_from_config()
            self.settings_closed.emit()
            super().closeEvent(event)
        else:
            event.ignore()
