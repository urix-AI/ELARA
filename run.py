# run.py

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread

# --- FIX for ModuleNotFoundError ---
# This adds the project's root directory (elara_assistant) to the Python path.
# It ensures that Python can find the 'elara' package when you run this script.
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
# -----------------------------------

from elara.logic import AssistantLogic
from elara.gui import AssistantGUI

def main():
    """
    Initializes and runs the Elara Assistant application.
    """
    app = QApplication(sys.argv)
    
    # Create a QThread for the backend logic to run on
    logic_thread = QThread()
    logic_thread.setObjectName("LogicThread")
    
    # Create an instance of the assistant's "brain"
    assistant_logic = AssistantLogic()
    
    # Move the logic object to the new thread. This is crucial for a responsive UI.
    assistant_logic.moveToThread(logic_thread)
    
    # Create the main GUI window, passing it a reference to the logic
    main_window = AssistantGUI(assistant_logic)
    
    # When the logic thread starts, it can begin its work
    # (though in this design, it's mostly event-driven via signals)
    logic_thread.start()
    
    # Cleanly quit the logic thread when the main window closes
    main_window.destroyed.connect(logic_thread.quit)
    logic_thread.finished.connect(app.quit)

    main_window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
