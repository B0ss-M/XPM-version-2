#!/usr/bin/env python3
"""
GUI Test script for XPM Repair Doctor
Launches the GUI interface for testing.
"""

import os
import sys

# Add current directory to path to import our modules  
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from xpm_repair_doctor import XPMRepairDoctorGUI
    print("✅ Successfully imported XPMRepairDoctorGUI")
except ImportError as e:
    print(f"❌ Failed to import XPMRepairDoctorGUI: {e}")
    sys.exit(1)

def launch_gui():
    """Launch the XPM Repair Doctor GUI."""
    try:
        app = XPMRepairDoctorGUI()
        print("🚀 Launching XPM Repair Doctor GUI...")
        app.mainloop()
    except Exception as e:
        print(f"❌ Error launching GUI: {e}")

if __name__ == "__main__":
    launch_gui()
