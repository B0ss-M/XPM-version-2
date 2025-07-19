#!/usr/bin/env python3
"""Test script for MPC-style filename note detection."""

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

# Import the detection functions from the sample mapping checker
from sample_mapping_checker import detect_pitch

# Test filenames from the screenshots
TEST_FILENAMES = [
    # First screenshot examples
    "1_021_a-1.wav",     # XPM root: 22
    "0_021_a-1.wav",     # XPM root: 22  
    "1_024_c0.wav",      # XPM root: 25
    "0_024_c0.wav",      # XPM root: 25
    "1_027_d#0.wav",     # XPM root: 28
    "0_027_d#0.wav",     # XPM root: 28
    
    # Second screenshot examples (mtmonchg pattern)
    "mtmonchg2.wav",     # XPM root: 47
    "mtmonchg3.wav",     # XPM root: 48
    "mtmonchg4.wav",     # XPM root: 49
    "mtnonchg#3.wav",    # XPM root: 50
]

# Expected MIDI values from the XPM root column
EXPECTED_VALUES = {
    "1_021_a-1.wav": 22,
    "0_021_a-1.wav": 22,
    "1_024_c0.wav": 25,
    "0_024_c0.wav": 25,
    "1_027_d#0.wav": 28,
    "0_027_d#0.wav": 28,
    "mtmonchg2.wav": 47,
    "mtmonchg3.wav": 48,
    "mtmonchg4.wav": 49,
    "mtnonchg#3.wav": 50,
}

def main():
    print("\nTesting MPC-style filename note detection:")
    print("=========================================")
    
    success_count = 0
    for filename in TEST_FILENAMES:
        # Create a temporary path (function uses basename anyway)
        test_path = os.path.join(parent_dir, filename)
        
        # Skip real detection logic and just test our filename parsing
        detected = detect_pitch(test_path)
        expected = EXPECTED_VALUES.get(filename)
        
        if detected == expected:
            result = "✅"
            success_count += 1
        else:
            result = f"❌ (expected {expected})"
            
        print(f"{filename:<20} -> {detected:<3} {result}")
    
    # Print summary
    print(f"\nSuccess rate: {success_count}/{len(TEST_FILENAMES)} ({success_count/len(TEST_FILENAMES)*100:.1f}%)")

if __name__ == "__main__":
    main()
