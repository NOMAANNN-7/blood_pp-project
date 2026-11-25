#!/usr/bin/env python3
"""
main.py - LIFEPOINT: Blood Donation Camp Register & Management System
Main Desktop Application Entry Point.
Directly launches the Native Graphical Desktop Application Window (Tkinter GUI).
No web browser or internet access required.
"""

import os
import sys

# Ensure root directory is in python path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

def main():
    # If executed with --cli or -c flag, start Terminal CLI
    if len(sys.argv) > 1 and sys.argv[1] in ("--cli", "-c"):
        from cli.main import main_menu
        main_menu()
        return

    # By default: Immediately launch the full Native Desktop Application Window
    from gui import LifePointGUI
    app = LifePointGUI()
    app.mainloop()

if __name__ == "__main__":
    main()
