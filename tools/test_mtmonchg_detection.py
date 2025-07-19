#!/usr/bin/env python3
"""Test script for mtmonchg note detection."""

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

from sample_mapping_checker import detect_pitch

# Test cases from the screenshot
TEST_FILENAMES = [
    "mtmonchg2.wav",
    "mtmonchg#2.wav",
    "mtmoncha2.wav",
    "mtmoncha#2.wav",
    "mtmonchb2.wav",
    "mtmonchc3.wav",
    "mtmonchc#3.wav",
    "mtmonchd3.wav",
    "mtmonchd#3.wav",
    "mtmonche3.wav",
    "mtmonche#3.wav",
    "mtmonchf3.wav",
    "mtmonchg3.wav",
    "mtmonchg#3.wav",
    "mtmoncha3.wav",
    "mtmoncha#3.wav",
    "mtmonchb3.wav",
    "mtmonchc4.wav",
    "mtmonchc#4.wav",
    "mtmonchd4.wav",
    "mtmonchd#4.wav",
    "mtmonche4.wav",
    "mtmonchf4.wav",
    "mtmonchg4.wav",
    "mtmonchg#4.wav",
    "mtmoncha4.wav",
    "mtmoncha#4.wav",
    "mtmonchb4.wav",
    "mtmonchc5.wav",
    "mtmonchc#5.wav",
    "mtmonchd5.wav",
    "mtmonchd#5.wav",
    "mtmonche5.wav",
    "mtmonche#5.wav",
]

# Expected values from the screenshot
EXPECTED_VALUES = {
    "mtmonchg2.wav": 44,
    "mtmonchg#2.wav": 45,
    "mtmoncha2.wav": 46,
    "mtmoncha#2.wav": 47,
    "mtmonchb2.wav": 48,
    "mtmonchc3.wav": 49,
    "mtmonchc#3.wav": 50,
    "mtmonchd3.wav": 51,
    "mtmonchd#3.wav": 52,
    "mtmonche3.wav": 53,
    "mtmonche#3.wav": 54,
    "mtmonchf3.wav": 55,
    "mtmonchg3.wav": 56,
    "mtmonchg#3.wav": 57,
    "mtmoncha3.wav": 58,
    "mtmoncha#3.wav": 59,
    "mtmonchb3.wav": 60,
    "mtmonchc4.wav": 61,
    "mtmonchc#4.wav": 62,
    "mtmonchd4.wav": 63,
    "mtmonchd#4.wav": 64,
    "mtmonche4.wav": 65,
    "mtmonche#4.wav": 66,
    "mtmonchf4.wav": 67,
    "mtmonchg4.wav": 68,
    "mtmonchg#4.wav": 69,
    "mtmoncha4.wav": 70,
    "mtmoncha#4.wav": 71,
    "mtmonchb4.wav": 72,
    "mtmonchc5.wav": 73,
    "mtmonchc#5.wav": 74,
    "mtmonchd5.wav": 75,
    "mtmonchd#5.wav": 76,
    "mtmonche5.wav": 77,
    "mtmonche#5.wav": 78,
}

def main():
    print("Testing mtmonchg note detection:")
    print("===============================")
    
    success_count = 0
    total_count = len(TEST_FILENAMES)
    
    for filename in TEST_FILENAMES:
        detected = detect_pitch(filename)
        expected = EXPECTED_VALUES.get(filename)
        
        if detected == expected:
            status = "✅"
            success_count += 1
        else:
            status = f"❌ (expected {expected})"
            
        print(f"{filename:<15} -> {detected:<3} {status}")
    
    # Print summary
    print(f"\nSuccess rate: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")

if __name__ == "__main__":
    main()
