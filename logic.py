# elara/logic.py

import os
import json
import shutil
import datetime
import requests
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

# --- Absolute imports to ensure modules are found ---
from elara import config
from elara import utils
from elara.commands import CommandManager

# Lazy-loaded modules for offline mode
transformers = None
torch = None
# Global variables for the offline model to load it only once
offline_model = None
offline_tokenizer = None


class AssistantLogic(QObject):
    """
    Handles all non-GUI logic: state management, API calls, and coordinating other modules.
    """
    new_message_signal = pyqtSignal(str)
    clear_chat_display_signal = pyqtSignal()
    listening_status_signal = pyqtSignal(str)
    mute_status_changed_signal = pyqtSignal(bool)
    context_status_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.mode = "Online (API)"
        self.chat_history = []
        self.current_chat_file = None
        self.document_context = None 
        self.document_filename = None
        self.settings = {}
        self.command_manager = CommandManager(self)
        
        os.makedirs(config.HISTORY_DIR, exist_ok=True)
        self.load_settings()
        self.start_new_chat(greet=False)

    def load_settings(self):
        """Loads settings from a JSON file."""
        default_settings = {"volume": 1.0}
        if os.path.exists(config.SETTINGS_FILE):
            try:
                with open(config.SETTINGS_FILE, 'r') as f:
                    self.settings = json.load(f)
                for key, value in default_settings.items():
                    self.settings.setdefault(key, value)
            except (json.JSONDecodeError, IOError):
                self.settings = default_settings
        else:
            self.settings = default_settings
        self.save_settings()

    def save_settings(self):
        """Saves current settings to a JSON file."""
        try:
            with open(config.SETTINGS_FILE, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")

    @pyqtSlot(dict)
    def update_settings(self, new_settings):
        self.settings.update(new_settings)
        self.save_settings()
        self.new_message_signal.emit("SYSTEM: Settings have been updated.")
        utils.set_mute_status(self.settings.get('is_muted', False))
        utils.initialize_tts()

    def save_current_chat(self):
        """Saves the current chat history to its session file."""
        if not self.current_chat_file or not self.chat_history: return
        try:
            filepath = os.path.join(config.HISTORY_DIR, self.current_chat_file)
            with open(filepath, 'w') as f:
                json.dump(self.chat_history, f, indent=4)
        except Exception as e:
            print(f"Error saving chat history: {e}")

    @pyqtSlot()
    def start_new_chat(self, greet=True):
        """Clears the current session and starts a new one."""
        self.save_current_chat()
        self.chat_history = []
        self.current_chat_file = f"chat_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
        self.clear_document_context()
        self.clear_chat_display_signal.emit()
        if greet:
            greeting = f"Hello! I'm {config.ASSISTANT_NAME}. How can I help you today?"
            self.new_message_signal.emit(f"Assistant: {greeting}")
            utils.speak(greeting, self.settings.get('volume', 1.0))

    @pyqtSlot(str)
    def load_chat(self, filename):
        """Loads a specific chat session from a file."""
        self.save_current_chat()
        self.clear_document_context()
        filepath = os.path.join(config.HISTORY_DIR, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    self.chat_history = json.load(f)
                self.current_chat_file = filename
                self.clear_chat_display_signal.emit()
                for msg_data in self.chat_history:
                    role = "You" if msg_data["role"] == "user" else "Assistant"
                    self.new_message_signal.emit(f"{role}: {msg_data['content']}")
                self.new_message_signal.emit(f"SYSTEM: Loaded Session: {filename}")
            except Exception as e:
                self.new_message_signal.emit(f"SYSTEM: Error loading chat: {e}")
                self.start_new_chat()
    
    @pyqtSlot(str)
    def load_document_context(self, file_path):
        """Reads a file and stores its content for contextual conversation."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.document_context = f.read()
            self.document_filename = os.path.basename(file_path)
            self.context_status_signal.emit(self.document_filename) # Update UI
            self.new_message_signal.emit(f"SYSTEM: I have read the file '{self.document_filename}' and will use it as context.")
        except Exception as e:
            self.new_message_signal.emit(f"SYSTEM: I'm sorry, I couldn't read that file. Error: {e}")

    def clear_document_context(self):
        """Clears the loaded file from memory."""
        if self.document_context:
            self.document_context = None
            self.document_filename = None
            self.context_status_signal.emit(None) # Clear UI
            self.new_message_signal.emit("SYSTEM: I have cleared the file from my context.")

    @pyqtSlot(str)
    def delete_chat(self, filename):
        """Deletes a saved chat session file."""
        filepath = os.path.join(config.HISTORY_DIR, filename)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                self.new_message_signal.emit(f"SYSTEM: Deleted session {filename}.")
                if self.current_chat_file == filename:
                    self.start_new_chat(greet=False)
            except Exception as e:
                self.new_message_signal.emit(f"SYSTEM: Error deleting chat: {e}")

    @pyqtSlot()
    def clear_all_history(self):
        """Deletes all chat session files and the directory."""
        self.save_current_chat()
        try:
            if os.path.exists(config.HISTORY_DIR):
                shutil.rmtree(config.HISTORY_DIR)
            os.makedirs(config.HISTORY_DIR, exist_ok=True)
            self.new_message_signal.emit("SYSTEM: All chat history has been cleared.")
            self.start_new_chat(greet=False)
        except Exception as e:
            self.new_message_signal.emit(f"SYSTEM: Error clearing history: {e}")

    @pyqtSlot()
    def toggle_mute(self):
        is_muted = not utils.is_muted
        utils.set_mute_status(is_muted)
        self.mute_status_changed_signal.emit(is_muted)
        status = "Muted" if is_muted else "Unmuted"
        self.new_message_signal.emit(f"SYSTEM: Voice has been {status}.")

    def set_mode(self, mode):
        self.mode = mode
        self.new_message_signal.emit(f"SYSTEM: Switched to {self.mode} mode.")

    @pyqtSlot(str)
    def process_input(self, user_input):
        """Processes user input by checking for commands or sending to an AI."""
        if not user_input: return
        self.new_message_signal.emit(f"You: {user_input}")

        command_response = self.command_manager.handle(user_input)
        response_text = ""
        
        if command_response:
            response_text = command_response
        else:
            self.chat_history.append({"role": "user", "content": user_input})
            if self.mode == "Online (API)":
                response_text = self._get_api_response()
            else:
                response_text = self._get_offline_response()
            self.chat_history.append({"role": "assistant", "content": response_text})

        if len(self.chat_history) > 20:
            self.chat_history = self.chat_history[-20:]

        self.save_current_chat()
        # Handle cases where a command doesn't need a spoken response
        if response_text:
            self.new_message_signal.emit(f"Assistant: {response_text}")
            utils.speak(response_text, self.settings.get('volume', 1.0))

    def _get_api_response(self):
        """Gets a response from the OpenRouter API."""
        if not config.OPENROUTER_API_KEY or config.OPENROUTER_API_KEY == "YOUR_API_KEY_HERE":
            return "API key not configured. Please set the OPENROUTER_API_KEY environment variable."
        
        self.listening_status_signal.emit("Thinking (API)...")
        headers = {
            "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": f"http://localhost/{config.ASSISTANT_NAME}",
            "X-Title": config.ASSISTANT_NAME,
        }
        
        system_prompt_text = f"You are {config.ASSISTANT_NAME}, a highly polite and helpful AI assistant."
        if self.document_context:
            system_prompt_text += f"\n\nIMPORTANT: Use the following document to answer the user's questions.\nDOCUMENT:\n---\n{self.document_context}\n---"

        system_prompt = {"role": "system", "content": system_prompt_text}
        
        payload = {"model": config.OPENROUTER_MODEL, "messages": [system_prompt] + self.chat_history }
        
        try:
            response = requests.post(config.OPENROUTER_API_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            if choice := result.get('choices', [{}])[0]:
                if message := choice.get('message', {}).get('content'):
                    self.listening_status_signal.emit("Status: Idle")
                    return message.strip()
            return "API returned an unexpected response format."
        except requests.exceptions.RequestException as e:
            return f"API Connection Error: {e}"
        except Exception as e:
            return f"An unexpected API error occurred: {e}"

    def _get_offline_response(self):
        """Generates a response using a local Hugging Face model."""
        global offline_model, offline_tokenizer, transformers, torch
        
        # Step 1: Lazy load libraries if they haven't been loaded yet.
        if not all([transformers, torch]):
            try:
                import torch as pt
                import transformers as hf
                transformers, torch = hf, pt
            except ImportError:
                return "Offline mode requires 'transformers' and 'torch'. Please run: pip install transformers torch accelerate"

        # Step 2: Load the model and tokenizer on first use.
        if not all([offline_model, offline_tokenizer]):
            self.listening_status_signal.emit("Loading offline model...")
            self.new_message_signal.emit("SYSTEM: First time use: downloading offline model...")
            try:
                model_name = "microsoft/phi-3-mini-128k-instruct"
                device = "cuda" if torch.cuda.is_available() else "cpu"
                self.new_message_signal.emit(f"SYSTEM: Loading model to {device.upper()}...")
                
                offline_tokenizer = transformers.AutoTokenizer.from_pretrained(model_name)
                
                model_args = {"trust_remote_code": True}
                if device == "cuda":
                    model_args["torch_dtype"] = "auto"
                    model_args["device_map"] = "auto"

                offline_model = transformers.AutoModelForCausalLM.from_pretrained(model_name, **model_args)

                if device == "cpu":
                    offline_model.to(device)

                self.new_message_signal.emit("SYSTEM: Offline model loaded successfully.")
            except Exception as e:
                self.listening_status_signal.emit("Status: Error")
                return f"Failed to load offline model: {e}"
        
        # Step 3: Generate a response.
        self.listening_status_signal.emit("Thinking (Offline)...")
        try:
            device = offline_model.device
            user_text = self.chat_history[-1]['content']
            
            prompt = f"<|system|>\nYou are Elara, a polite AI assistant.<|end|>\n<|user|>\n{user_text}<|end|>\n<|assistant|>"
            inputs = offline_tokenizer(prompt, return_tensors="pt").to(device)
            
            outputs = offline_model.generate(**inputs, max_new_tokens=70, eos_token_id=offline_tokenizer.eos_token_id)
            response_full = offline_tokenizer.batch_decode(outputs, skip_special_tokens=True)[0]
            
            self.listening_status_signal.emit("Status: Idle")
            
            if "<|assistant|>" in response_full:
                return response_full.split("<|assistant|>")[1].strip()
            else:
                return response_full # Fallback if format is unexpected
        except Exception as e:
            self.listening_status_signal.emit("Status: Error")
            return f"Error during offline generation: {e}"
