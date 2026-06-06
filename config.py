# elara/config.py

import os

# --- Core Application Configuration ---
ASSISTANT_NAME = "Elara"
HISTORY_DIR = "chat_sessions"
SETTINGS_FILE = "settings.json"

# --- API Configuration ---
# Securely load the API key from an environment variable
# Users will set this on their system, keeping it out of the source code.
# The second argument is a default value if the environment variable isn't found.
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "your_openrouter_key")

# The model is hardcoded to hide this detail from the user settings
OPENROUTER_MODEL = "deepseek/deepseek-chat"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# --- Application Commands (Aliases) ---
# Add common applications or aliases here for quick, guaranteed access.
APP_COMMANDS = {
    "windows": {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "command prompt": "cmd.exe"
    },
    "darwin": { # macOS
        "textedit": "open -a TextEdit",
        "calculator": "open -a Calculator",
        "terminal": "open -a Terminal"
    },
    "linux": {
        "text editor": "gedit",
        "calculator": "gnome-calculator",
        "terminal": "gnome-terminal"
    }
}
