#!/usr/bin/env python3
"""Test script for note detection from filenames in the Sample Mapping Checker."""

import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

# Add the parent directory to the path so we can import the modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from xpm_parameter_editor import infer_note_from_filename

# Test cases from the screenshot
TEST_FILENAMES = [
    "1_021_a-1.wav",
    "0_021_a-1.wav",
    "1_024_c0.wav",
    "0_024_c0.wav",
    "1_027_d#0.wav",
    "0_027_d#0.wav",
    "1_030_f#0.wav",
    "0_030_f#0.wav",
    "1_033_a0.wav",
    "0_033_a0.wav",
    "1_036_c1.wav",
    "0_036_c1.wav",
    "1_039_d#1.wav",
    "0_039_d#1.wav",
    "1_042_f#1.wav",
    "0_042_f#1.wav",
    "1_045_a1.wav",
    "0_045_a1.wav",
    "1_048_c2.wav",
]

def main():
    print("Testing note detection from filenames:")
    print("======================================")
    
    for filename in TEST_FILENAMES:
        midi = infer_note_from_filename(filename)
        print(f"{filename:<20} -> {midi if midi is not None else 'None'}")

if __name__ == "__main__":
    main()
