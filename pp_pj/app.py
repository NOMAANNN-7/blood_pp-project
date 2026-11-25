#!/usr/bin/env python3
"""
app.py - LIFEPOINT: Blood Donation Camp Register & Management System
Direct Desktop Application Window Launcher.
"""

import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from gui import LifePointGUI

if __name__ == "__main__":
    app = LifePointGUI()
    app.mainloop()
