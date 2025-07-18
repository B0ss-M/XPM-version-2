#!/usr/bin/env python3
"""Test script for note detection from filenames."""

import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG if '--debug' in sys.argv else logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

# Add the parent directory to the path so we can import the modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from xpm_parameter_editor import infer_note_from_filename, name_to_midi

# Reference table mapping note names to expected MIDI values
NOTE_REFERENCE = {
    "C3": 48, "C#3": 49, "DB3": 49, "D3": 50, "D#3": 51, "EB3": 51, 
    "E3": 52, "F3": 53, "F#3": 54, "GB3": 54, "G3": 55, "G#3": 56, 
    "AB3": 56, "A3": 57, "A#3": 58, "BB3": 58, "B3": 59,
    "C4": 60, "C0": 12, "C-1": 0, "G9": 127, "CB3": 47
}

# Test cases
TEST_FILENAMES = [
    # Basic note formats
    "sample_c3.wav",         # Standard C3
    "sample_C3.wav",         # Upper case C3
    "sample_c#3.wav",        # Standard C#3
    "sample_C#3.wav",        # Upper case C#3
    "sample_cb3.wav",        # Flat notation
    
    # No separator
    "sampleC3.wav",          # No separator
    "sampleC#3.wav",         # No separator with sharp
    
    # Special cases
    "******f#3.wav",         # Special case
    "piano_f#3_mono.wav",    # Middle underscore
    "f#3.wav",               # Just the note
    "f#_3.wav",              # Note and octave separated
    
    # MIDI numbers
    "sample-60.wav",         # MIDI number
    
    # Additional test cases
    "piano_Bb2.wav",         # Flat with uppercase B
    "sample_Db4_stereo.wav", # Flat with underscore
    "Bass-E1.wav",           # Note with hyphen
    "Strings-C-1.wav",       # Negative octave
    "Piano C4 Soft.wav",     # Note with spaces
]

def main():
    print("Testing note detection from filenames:")
    print("======================================")
    
    # Print out reference table
    if '--show-reference' in sys.argv:
        print("\nReference MIDI Note Values:")
        print("-------------------------")
        for note, midi in sorted(NOTE_REFERENCE.items(), key=lambda x: x[1]):
            print(f"{note:<5} -> {midi}")
        print()
    
    # Test all filenames
    success_count = 0
    total_count = len(TEST_FILENAMES)
    
    print("Filename Tests:")
    print("--------------")
    for filename in TEST_FILENAMES:
        midi = infer_note_from_filename(filename)
        
        # Custom expected values for specific test cases
        expected_values = {
            "sample_cb3.wav": 47,      # Cb3 is B2 (47)
            "f#_3.wav": 54,            # F#3 is 54
            "Strings-C-1.wav": 0,      # C-1 is 0
        }
        
        # Check if there's an expected value we can validate against
        expected = expected_values.get(filename)
        if expected is None:
            for note, value in NOTE_REFERENCE.items():
                if note.lower() in filename.lower() or str(value) in filename:
                    expected = value
                    break
        
        # Format the output
        result = str(midi) if midi is not None else 'None'
        is_valid = "✅" if expected is None or midi == expected else f"❌ (expected {expected})"
        
        if expected is not None and midi == expected:
            success_count += 1
            
        print(f"{filename:<25} -> {result:<3} {is_valid}")
    
    # Print summary
    if any(note.lower() in filename.lower() for note in NOTE_REFERENCE for filename in TEST_FILENAMES):
        print(f"\nSuccess rate: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
    
    # Test direct note name to MIDI conversion
    if '--test-direct' in sys.argv:
        print("\nDirect Note Name Tests:")
        print("----------------------")
        for note, expected in NOTE_REFERENCE.items():
            midi = name_to_midi(note)
            is_valid = "✅" if midi == expected else f"❌ (got {midi}, expected {expected})"
            print(f"{note:<5} -> {expected:<3} {is_valid}")

if __name__ == "__main__":
    main()
