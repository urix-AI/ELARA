# elara/gui.py

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
                             QLineEdit, QPushButton, QComboBox, QLabel, QSizePolicy, QScrollArea, QApplication)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QPoint
from PyQt6.QtGui import QFont, QGuiApplication

# --- Absolute imports to ensure modules are found ---
from elara import config
from elara.dialogs import SettingsDialog, ChatHistoryDialog
import speech_recognition as sr
import threading

class CodeBlockWidget(QWidget):
    """A custom widget to display a block of code with a copy button."""
    def __init__(self, language, code_text, parent=None):
        super().__init__(parent)
        self.language = language
        self.code_text = code_text
        self.init_ui()

    def init_ui(self):
        self.setObjectName("code_block")
        self.setStyleSheet("""
            QWidget#code_block {
                background-color: #2B303B; 
                border-radius: 5px; 
                border: 1px solid #4C566A;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header bar for language and copy button
        header = QWidget()
        header.setStyleSheet("background-color: #434C5E; border-top-left-radius: 5px; border-top-right-radius: 5px;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 5, 10, 5)

        lang_label = QLabel(self.language if self.language else "code")
        lang_label.setStyleSheet("color: #D8DEE9; font-weight: bold; border: none;")
        
        copy_button = QPushButton("Copy")
        copy_button.setFixedSize(60, 25)
        copy_button.setStyleSheet("""
            QPushButton { 
                background-color: #5E81AC; 
                color: #ECEFF4; 
                border: none; 
                border-radius: 3px; 
                font-size: 12px;
            }
            QPushButton:hover { background-color: #81A1C1; }
        """)
        copy_button.clicked.connect(self.copy_code)

        header_layout.addWidget(lang_label)
        header_layout.addStretch()
        header_layout.addWidget(copy_button)

        # Code display area
        self.code_edit = QTextEdit()
        self.code_edit.setPlainText(self.code_text)
        self.code_edit.setReadOnly(True)
        # Use a monospace font for code
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.code_edit.setFont(font)
        self.code_edit.setStyleSheet("""
            QTextEdit { 
                background-color: #2B303B; 
                color: #D8DEE9;
                border: none;
                padding: 10px;
            }
        """)

        main_layout.addWidget(header)
        main_layout.addWidget(self.code_edit)

    def copy_code(self):
        """Copies the code text to the system clipboard."""
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self.code_text)


class AssistantGUI(QWidget):
    """The main graphical user interface for the assistant."""
    user_input_signal = pyqtSignal(str)
    listening_request_signal = pyqtSignal()

    def __init__(self, assistant_logic):
        super().__init__()
        self.assistant_logic = assistant_logic
        self.old_pos = None
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(100, 100, 450, 600)
        
        self.container = QWidget(self)
        self.container.setObjectName("main_container")
        self.container.setStyleSheet("""
            QWidget#main_container { background-color: #2E3440; color: #ECEFF4; font-family: 'Segoe UI', Arial, sans-serif; font-size: 14px; border-radius: 10px; }
            QTextEdit { background-color: #3B4252; border: 1px solid #4C566A; border-radius: 5px; padding: 5px; }
            QLineEdit { background-color: #4C566A; border: 1px solid #5E81AC; border-radius: 5px; padding: 8px; }
            QPushButton { background-color: #5E81AC; color: #ECEFF4; border: none; padding: 10px; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #81A1C1; }
            QPushButton#management_btn { background-color: #434C5E; } QPushButton#management_btn:hover { background-color: #4C566A; }
            QComboBox { background-color: #4C566A; border: 1px solid #5E81AC; border-radius: 5px; padding: 5px; }
            QLabel { background-color: transparent; }
            QLabel#status_label { color: #A3BE8C; font-weight: bold; }
            QLabel#title_label { color: #ECEFF4; font-weight: bold; padding-left: 5px; }
        """)
        
        main_layout = QVBoxLayout(self.container)
        main_layout.setContentsMargins(5, 5, 5, 5) # Add some padding
        main_layout.setSpacing(5)

        self._create_title_bar(main_layout)
        
        # --- NEW Dynamic Chat Display Area ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background-color: #3B4252; border-radius: 5px; }")
        
        # Container widget for the chat layout
        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_layout.setSpacing(10)
        
        self.scroll_area.setWidget(self.chat_container)
        main_layout.addWidget(self.scroll_area)
        # --- END NEW ---
        
        self.status_label = QLabel("Status: Idle")
        self.status_label.setObjectName("status_label")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        self._create_management_buttons(main_layout)
        
        self.mode_selector = QComboBox()
        self.mode_selector.addItems(["Online (API)", "Offline (Local)"])
        main_layout.addWidget(self.mode_selector)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type a message or command...")
        main_layout.addWidget(self.input_field)
        
        self._create_action_buttons(main_layout)
        
        outer_layout = QVBoxLayout(self)
        outer_layout.addWidget(self.container)
        outer_layout.setContentsMargins(0, 0, 0, 0)

    def _create_title_bar(self, parent_layout):
        self.title_bar = QWidget()
        title_bar_layout = QHBoxLayout(self.title_bar)
        title_bar_layout.setContentsMargins(5, 0, 5, 0)
        
        title_label = QLabel(f"{config.ASSISTANT_NAME} AI Assistant")
        title_label.setObjectName("title_label")
        title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        self.mute_button = QPushButton("🔊")
        self.minimize_button = QPushButton("—")
        self.close_button = QPushButton("✕")
        
        for btn in [self.mute_button, self.minimize_button, self.close_button]:
            btn.setFixedSize(30, 30)
            btn.setStyleSheet("""
                QPushButton { background-color: transparent; border: none; font-size: 16px; font-weight: bold; } 
                QPushButton:hover { background-color: #4C566A; }
            """)
        self.close_button.setStyleSheet(self.close_button.styleSheet() + "QPushButton:hover { background-color: #BF616A; }")

        title_bar_layout.addWidget(title_label)
        title_bar_layout.addWidget(self.mute_button)
        title_bar_layout.addWidget(self.minimize_button)
        title_bar_layout.addWidget(self.close_button)
        parent_layout.addWidget(self.title_bar)

    def _create_management_buttons(self, parent_layout):
        management_layout = QHBoxLayout()
        self.new_chat_button = QPushButton("New Chat")
        self.history_button = QPushButton("History")
        self.settings_button = QPushButton("Settings")
        for btn in [self.new_chat_button, self.history_button, self.settings_button]:
            btn.setObjectName("management_btn")
            management_layout.addWidget(btn)
        parent_layout.addLayout(management_layout)

    def _create_action_buttons(self, parent_layout):
        button_layout = QHBoxLayout()
        self.send_button = QPushButton("Send")
        self.mic_button = QPushButton("Speak")
        button_layout.addWidget(self.send_button)
        button_layout.addWidget(self.mic_button)
        parent_layout.addLayout(button_layout)

    def connect_signals(self):
        # GUI -> Logic
        self.send_button.clicked.connect(self.send_text_input)
        self.input_field.returnPressed.connect(self.send_text_input)
        self.mode_selector.currentTextChanged.connect(self.assistant_logic.set_mode)
        self.mute_button.clicked.connect(self.assistant_logic.toggle_mute)
        self.new_chat_button.clicked.connect(self.assistant_logic.start_new_chat)
        self.history_button.clicked.connect(self.show_history_dialog)
        self.settings_button.clicked.connect(self.show_settings_dialog)
        self.user_input_signal.connect(self.assistant_logic.process_input)
        self.mic_button.clicked.connect(self.start_listening_thread)

        # Window controls
        self.minimize_button.clicked.connect(self.showMinimized)
        self.close_button.clicked.connect(self.close)
        
        # Logic -> GUI
        self.assistant_logic.new_message_signal.connect(self.update_chat_display)
        self.assistant_logic.clear_chat_display_signal.connect(self.clear_chat_layout)
        self.assistant_logic.listening_status_signal.connect(self.update_status_label)
        self.assistant_logic.mute_status_changed_signal.connect(self.update_mute_button_status)

    def start_listening_thread(self):
        threading.Thread(target=self._listen, daemon=True).start()

    def _listen(self):
        r = sr.Recognizer()
        with sr.Microphone() as source:
            r.pause_threshold = 1.0; r.adjust_for_ambient_noise(source)
            self.update_status_label("Listening...")
            try:
                audio = r.listen(source, timeout=5, phrase_time_limit=10)
                self.update_status_label("Recognizing..."); text = r.recognize_google(audio)
                self.update_status_label("Status: Idle"); self.user_input_signal.emit(text)
            except sr.UnknownValueError:
                self.update_status_label("Status: Idle"); self.user_input_signal.emit("*[Could not understand audio]*")
            except sr.RequestError as e:
                self.update_status_label("Status: Error"); self.user_input_signal.emit(f"*[Speech recognition service unavailable: {e}]*")

    def show_history_dialog(self):
        dialog = ChatHistoryDialog(self)
        dialog.chat_to_load.connect(self.assistant_logic.load_chat)
        dialog.chat_to_delete.connect(self.assistant_logic.delete_chat)
        dialog.exec()

    def show_settings_dialog(self):
        dialog = SettingsDialog(self.assistant_logic.settings, self)
        dialog.settings_updated.connect(self.assistant_logic.update_settings)
        dialog.clear_all_history_requested.connect(self.assistant_logic.clear_all_history)
        dialog.exec()

    def send_text_input(self):
        if user_text := self.input_field.text().strip():
            self.user_input_signal.emit(user_text); self.input_field.clear()

    @pyqtSlot()
    def clear_chat_layout(self):
        """Removes all widgets from the chat layout."""
        while self.chat_layout.count():
            child = self.chat_layout.takeAt(0)
            if widget := child.widget():
                widget.deleteLater()

    @pyqtSlot(str)
    def update_chat_display(self, message):
        """Parses a message for text and code, adding appropriate widgets."""
        if ":" in message:
            role, content = message.split(":", 1)
            content = content.strip()
            
            role_label = QLabel(f"<b>{role}:</b>")
            role_label.setStyleSheet("font-size: 15px; margin-top: 10px;")
            self.chat_layout.addWidget(role_label)
        else:
            content = message.strip()

        parts = content.split("```")
        for i, part in enumerate(parts):
            if not part.strip(): continue
            
            if i % 2 == 0: # This is regular text
                text_label = QLabel(part.strip())
                text_label.setWordWrap(True)
                text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                self.chat_layout.addWidget(text_label)
            else: # This is code
                lines = part.strip().split('\n', 1)
                language = lines[0].strip() if lines else ""
                code = lines[1].strip() if len(lines) > 1 else ""
                if code:
                    code_widget = CodeBlockWidget(language, code)
                    self.chat_layout.addWidget(code_widget)
        
        # Ensure scrollbar scrolls to the bottom after new content is added
        QApplication.instance().processEvents()
        v_scroll_bar = self.scroll_area.verticalScrollBar()
        v_scroll_bar.setValue(v_scroll_bar.maximum())

    @pyqtSlot(str)
    def update_status_label(self, status):
        self.status_label.setText(f"Status: {status}")

    @pyqtSlot(bool)
    def update_mute_button_status(self, is_muted):
        self.mute_button.setText("🔇" if is_muted else "🔊")
        
    def closeEvent(self, event):
        self.assistant_logic.save_current_chat()
        super().closeEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.title_bar.underMouse():
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = None

    def mouseMoveEvent(self, event):
        if self.old_pos:
            delta = QPoint(event.globalPosition().toPoint() - self.old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()
