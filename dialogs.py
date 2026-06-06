# elara/dialogs.py

import os
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QDialogButtonBox, QFormLayout, QSlider, QPushButton, QLabel
from PyQt6.QtCore import pyqtSignal, Qt

# --- Absolute import to ensure module is found ---
from elara import config

class SettingsDialog(QDialog):
    """A dialog to manage user-facing application settings."""
    settings_updated = pyqtSignal(dict)
    clear_all_history_requested = pyqtSignal()

    def __init__(self, current_settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(400)
        self.setStyleSheet("""
            QDialog { background-color: #3B4252; color: #ECEFF4; }
            QSlider { background-color: #4C566A; }
            QPushButton { background-color: #5E81AC; color: #ECEFF4; border: none; padding: 10px; border-radius: 5px; }
            QPushButton:hover { background-color: #81A1C1; }
            QPushButton#destructive_btn { background-color: #BF616A; }
            QPushButton#destructive_btn:hover { background-color: #D08770; }
            QLabel { font-weight: bold; }
        """)
        
        self.current_settings = current_settings
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(int(self.current_settings.get("volume", 1.0) * 100))
        form_layout.addRow("Voice Volume:", self.volume_slider)

        layout.addLayout(form_layout)

        api_info_label = QLabel("Note: The API key is configured via an environment variable or in the config file.")
        api_info_label.setWordWrap(True)
        api_info_label.setStyleSheet("font-weight: normal; font-style: italic;")
        layout.addWidget(api_info_label)

        self.clear_history_button = QPushButton("Clear All Chat History")
        self.clear_history_button.setObjectName("destructive_btn")
        self.clear_history_button.clicked.connect(self.clear_all_history_requested.emit)
        layout.addWidget(self.clear_history_button)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def accept(self):
        updated_settings = {
            "volume": self.volume_slider.value() / 100.0
        }
        self.settings_updated.emit(updated_settings)
        super().accept()

class ChatHistoryDialog(QDialog):
    """A dialog to view, load, and delete past chat sessions."""
    chat_to_load = pyqtSignal(str)
    chat_to_delete = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chat History")
        self.setGeometry(200, 200, 400, 500)
        self.setStyleSheet("""
            QDialog { background-color: #3B4252; }
            QListWidget { background-color: #4C566A; border: 1px solid #5E81AC; border-radius: 5px; color: #ECEFF4; }
            QPushButton { background-color: #5E81AC; color: #ECEFF4; border: none; padding: 10px; border-radius: 5px; }
            QPushButton:hover { background-color: #81A1C1; }
        """)
        layout = QVBoxLayout(self)
        self.chat_list_widget = QListWidget()
        self.populate_chats()
        layout.addWidget(self.chat_list_widget)
        button_box = QDialogButtonBox()
        button_box.addButton("Load", QDialogButtonBox.ButtonRole.AcceptRole)
        self.delete_button = button_box.addButton("Delete", QDialogButtonBox.ButtonRole.DestructiveRole)
        button_box.addButton(QDialogButtonBox.StandardButton.Close)
        layout.addWidget(button_box)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self.delete_button.clicked.connect(self.delete_selected_chat)
        
    def populate_chats(self):
        self.chat_list_widget.clear()
        if os.path.exists(config.HISTORY_DIR):
            files = sorted(os.listdir(config.HISTORY_DIR), reverse=True)
            self.chat_list_widget.addItems(files)

    def accept(self):
        if item := self.chat_list_widget.currentItem():
            self.chat_to_load.emit(item.text())
        super().accept()

    def delete_selected_chat(self):
        if item := self.chat_list_widget.currentItem():
            self.chat_to_delete.emit(item.text())
            self.chat_list_widget.takeItem(self.chat_list_widget.row(item))
