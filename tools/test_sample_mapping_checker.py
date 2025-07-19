#!/usr/bin/env python3
"""Test utility for Sample Mapping Checker's pitch detection."""

import os
import sys
import logging
import re

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

# Add the parent directory to the path so we can import the modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import the functions we want to test
from xpm_parameter_editor import infer_note_from_filename, extract_root_note_from_wav
from sample_mapping_checker import detect_pitch

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
    # Ask for folder containing the test files
    folder = input("Enter the folder path containing the test files (or press Enter to use test filenames only): ")
    
    print("\nTesting Sample Mapping Checker pitch detection:")
    print("=============================================")
    print(f"{'Filename':<20} | {'XPM Root (Expected)':<20} | {'Detected':<10} | {'Method':<15}")
    print("-" * 70)
    
    for filename in TEST_FILENAMES:
        full_path = os.path.join(folder, filename) if folder else filename
        
        # Extract the expected XPM root note from the filename
        expected = None
        midi_match = re.search(r'_0?(\d{2,3})_', filename)
        if midi_match:
            try:
                expected = int(midi_match.group(1)) + 1  # Add 1 to match the XPM root
            except ValueError:
                pass
                
        # Test direct filename inference
        inferred = infer_note_from_filename(full_path)
        
        # Test the full detection function
        detected = None
        method = "N/A"
        
        if os.path.exists(full_path):
            # First try WAV metadata
            wav_root = extract_root_note_from_wav(full_path)
            if wav_root is not None:
                detected = wav_root
                method = "WAV Metadata"
            else:
                # Then try our improved detection
                detected = detect_pitch(full_path)
                if inferred == detected:
                    method = "Filename"
                else:
                    method = "Other/Fallback"
        else:
            # Just use filename inference for non-existent files
            detected = inferred
            method = "Filename (Test)"
            
        # Format the output
        expected_str = str(expected) if expected is not None else "Unknown"
        detected_str = str(detected) if detected is not None else "None"
        match = "✅" if expected is not None and detected == expected else "❌"
        
        print(f"{filename:<20} | {expected_str:<20} | {detected_str:<10} | {method:<15} {match}")

if __name__ == "__main__":
    main()
