# elara/utils.py

import pyttsx3
import threading
import re # Import the regular expression module

# --- Text-to-Speech (TTS) Engine ---

tts_engine = None
is_muted = False
tts_lock = threading.Lock()

def initialize_tts():
    """Initializes the TTS engine."""
    global tts_engine
    try:
        tts_engine = pyttsx3.init()
    except Exception as e:
        print(f"Failed to initialize TTS engine: {e}")

def clean_text_for_speech(text):
    """
    Removes emojis and other non-speakable special characters from a string.
    It will now attempt to speak code blocks.
    """
    if not text:
        return ""
    
    # This regex pattern keeps letters (including international ones), numbers, 
    # spaces, common punctuation, and some code-friendly characters like underscore and hash.
    # It removes most other symbols.
    speakable_pattern = re.compile(r'[^\w\s.,?!$€£¥\'"-_#]')
    
    # Code blocks are now processed by the main pattern instead of being replaced.
    # The ``` backticks will be removed by the pattern above.
    
    cleaned_text = speakable_pattern.sub(' ', text) # Replace with space to avoid words running together
    
    return cleaned_text

def speak(text, volume=1.0):
    """
    Converts text to speech in a separate thread to avoid blocking.
    Respects the global mute state and cleans the text before speaking.
    """
    if tts_engine and not is_muted:
        
        cleaned_text = clean_text_for_speech(text)
        if not cleaned_text.strip(): # Don't try to speak if the text is empty after cleaning
            return

        def tts_task():
            with tts_lock:
                try:
                    tts_engine.setProperty('volume', volume)
                    tts_engine.say(cleaned_text)
                    tts_engine.runAndWait()
                except Exception as e:
                    print(f"TTS Error: {e}")
        
        # Run in a daemon thread so it doesn't block app exit
        threading.Thread(target=tts_task, daemon=True).start()

def set_mute_status(muted: bool):
    """Sets the global mute status."""
    global is_muted
    is_muted = muted

# Initialize the engine once on import
initialize_tts()
