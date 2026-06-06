# elara/commands.py

import datetime
import webbrowser
import subprocess
import shlex
import sys
from . import config

class CommandManager:
    """A class to register and handle system commands."""
    
    # This __init__ method is now corrected to accept the logic_instance
    def __init__(self, logic_instance):
        self.logic = logic_instance # Store a reference to the main logic class
        self.commands = {
            ("what's the time", "what is the time", "current time"): self.get_time,
            ("what's the date", "what is the date", "today's date"): self.get_date,
            ("weather",): self.get_weather,
            ("search for",): self.search_web,
            ("open", "launch", "start", "run"): self.open_target,
            ("forget file", "clear context"): self.forget_file,
        }

    def handle(self, text):
        """
        Attempts to find and execute a command based on the input text.
        """
        text_lower = text.lower()
        for keywords, handler in self.commands.items():
            for kw in keywords:
                if text_lower.startswith(f"{kw} "):
                    argument = text[len(kw):].strip()
                    return handler(argument)
                elif text_lower == kw:
                    return handler(None) # Handle commands with no argument
        return None

    # --- Command Implementations (Skills) ---

    def forget_file(self, arg=None):
        """Tells the logic to clear the document context."""
        self.logic.clear_document_context()
        # The logic class itself will send the confirmation message to the UI
        return "" # Return empty string as confirmation is handled in logic

    def get_time(self, arg=None):
        """Returns the current time."""
        now = datetime.datetime.now()
        return f"Certainly. The current time is {now.strftime('%I:%M %p')}."

    def get_date(self, arg=None):
        """Returns the current date."""
        today = datetime.date.today()
        return f"Of course. Today's date is {today.strftime('%A, %B %d, %Y')}."

    def get_weather(self, arg=None):
        """Opens a web search for the weather."""
        webbrowser.open("https://www.google.com/search?q=weather+in+my+current+location")
        return "I have opened a web search for the weather in your current location."
    
    def search_web(self, query):
        """Performs a web search for the given query."""
        if not query: return "What would you like me to search for?"
        try:
            webbrowser.open(f"https://www.google.com/search?q={query}")
            return f"Certainly. Here are the search results for '{query}'."
        except Exception as e:
            return f"I apologize, I couldn't perform that search. Error: {e}"

    def open_target(self, target):
        """Intelligently opens a target, trying local apps first, then web search."""
        if not target: return "What would you like me to open?"

        platform_key = 'windows' if sys.platform == 'win32' else 'darwin' if sys.platform == 'darwin' else 'linux'
        app_list = config.APP_COMMANDS.get(platform_key, {})
        if target.lower() in app_list:
            try:
                subprocess.Popen(shlex.split(app_list[target.lower()]))
                return f"Certainly, launching your shortcut for {target}."
            except Exception as e:
                return f"I apologize, an error occurred: {e}"

        try:
            if sys.platform == "win32": subprocess.Popen(f'start "" "{target}"', shell=True)
            else: subprocess.Popen(["open", "-a", target] if sys.platform == "darwin" else shlex.split(target))
            return f"Of course. Opening {target}."
        except Exception:
            try:
                webbrowser.open(f"https://www.google.com/search?q={target}")
                return f"I couldn't find '{target}' on your system, so I've performed a web search for you."
            except Exception as e_web:
                return f"I couldn't find '{target}' or open a web search: {e_web}"
