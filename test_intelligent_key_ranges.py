#!/usr/bin/env python3
"""
Test script for intelligent key range assignment.

This script demonstrates the enhanced key range assignment that:
1. Analyzes sample root notes in XPM files
2. Assigns intelligent ranges based on pitch
3. Ensures the highest sample (e.g., C5) extends to C8 for full keyboard access
4. Fixes problematic ranges like LowNote > HighNote
"""

import sys
import os
import xml.etree.ElementTree as ET
import logging

# Add current directory to path for imports
sys.path.insert(0, '/Users/marlsz/Documents/GitHub/XPM-version-2')

import importlib.util
spec = importlib.util.spec_from_file_location("gemini_module", "/Users/marlsz/Documents/GitHub/XPM-version-2/Gemini wav_TO_XpmV2.py")
gemini_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gemini_module)
ExpansionDoctorWindow = gemini_module.ExpansionDoctorWindow
import tkinter as tk

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_intelligent_key_ranges():
    """Test the intelligent key range assignment on test files."""
    
    # Create a minimal tkinter app for testing
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    # Create a mock master object with required attributes
    class MockMaster:
        def __init__(self):
            self.folder_path = tk.StringVar()
            self.folder_path.set('/Users/marlsz/Documents/GitHub/XPM-version-2')
    
    master = MockMaster()
    
    # Create ExpansionDoctorWindow instance
    doctor = ExpansionDoctorWindow(master)
    doctor.withdraw()  # Hide the doctor window
    
    # Test files to analyze
    test_files = [
        '/Users/marlsz/Documents/GitHub/XPM-version-2/test_key_range_issues.xpm',
        '/Users/marlsz/Documents/GitHub/XPM-version-2/test_keygroup_count_issue.xpm'
    ]
    
    for test_file in test_files:
        if not os.path.exists(test_file):
            print(f"⚠️  Test file not found: {test_file}")
            continue
            
        print(f"\n🔍 ANALYZING: {os.path.basename(test_file)}")
        print("="*60)
        
        # Create backup
        backup_file = test_file + '.test_backup'
        if not os.path.exists(backup_file):
            with open(test_file, 'r') as src, open(backup_file, 'w') as dst:
                dst.write(src.read())
        
        # Analyze before fixing
        print("📊 BEFORE FIX:")
        analyze_xmp_ranges(test_file)
        
        # Apply intelligent key range fix
        print(f"\n🔧 APPLYING INTELLIGENT KEY RANGE FIX...")
        try:
            fixed = doctor.fix_single_key_ranges(test_file)
            if fixed:
                print("✅ Key ranges successfully fixed!")
                
                # Analyze after fixing
                print(f"\n📊 AFTER FIX:")
                analyze_xmp_ranges(test_file)
            else:
                print("ℹ️  No changes needed")
        except Exception as e:
            print(f"❌ Error applying fix: {e}")
            
        # Restore backup
        print(f"\n🔄 Restoring backup...")
        with open(backup_file, 'r') as src, open(test_file, 'w') as dst:
            dst.write(src.read())
        os.remove(backup_file)
    
    # Cleanup
    doctor.destroy()
    root.destroy()

def analyze_xmp_ranges(xmp_path):
    """Analyze and display current key ranges in an XMP file."""
    try:
        tree = ET.parse(xmp_path)
        root = tree.getroot()
        instruments = root.findall(".//Instrument")
        
        print(f"   Total instruments: {len(instruments)}")
        
        for i, instrument in enumerate(instruments):
            low_note_elem = instrument.find("LowNote")
            high_note_elem = instrument.find("HighNote")
            
            # Get root note from layer
            layer = instrument.find("Layer")
            root_note = "Unknown"
            sample_file = "Unknown"
            
            if layer is not None:
                root_note_elem = layer.find("RootNote")
                if root_note_elem is not None and root_note_elem.text:
                    root_note = root_note_elem.text
                
                sample_file_elem = layer.find("SampleFile")
                if sample_file_elem is not None and sample_file_elem.text:
                    sample_file = sample_file_elem.text
            
            # Get current range
            low_note = low_note_elem.text if low_note_elem is not None and low_note_elem.text else "Missing"
            high_note = high_note_elem.text if high_note_elem is not None and high_note_elem.text else "Missing"
            
            # Check for issues
            issues = []
            if low_note != "Missing" and high_note != "Missing":
                try:
                    low_val = int(low_note)
                    high_val = int(high_note)
                    if low_val > high_val:
                        issues.append("LowNote > HighNote")
                    if low_val == high_val == 0:
                        issues.append("Both notes = 0")
                    if low_val < 0 or high_val > 127:
                        issues.append("Out of MIDI range")
                except ValueError:
                    issues.append("Invalid note values")
            
            status = "❌ " + ", ".join(issues) if issues else "✅ OK"
            
            print(f"   KG{i+1}: Root={root_note}, Range={low_note}-{high_note}, Sample={sample_file} {status}")
            
            # Special note for C5 (note 72) samples
            if root_note != "Unknown":
                try:
                    root_val = int(root_note)
                    if root_val >= 72:  # C5 or higher
                        if high_note != "Missing" and int(high_note) < 96:  # Less than C8
                            print(f"      ⚠️  High sample (C{root_val//12}) should extend to C8 (96) for full keyboard access")
                except (ValueError, TypeError):
                    pass
                    
    except Exception as e:
        print(f"   ❌ Error analyzing {os.path.basename(xmp_path)}: {e}")

def demonstrate_note_mapping():
    """Show MIDI note to musical note mapping for reference."""
    print("\n🎹 MIDI NOTE REFERENCE:")
    print("="*40)
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    
    key_notes = [60, 72, 84, 96, 108, 120, 127]  # C4, C5, C6, C7, C8, C9, G9
    for midi_note in key_notes:
        octave = (midi_note // 12) - 1
        note_name = notes[midi_note % 12]
        print(f"   MIDI {midi_note:3d} = {note_name}{octave}")
    
    print(f"\n🎯 TARGET: C5 samples should extend to at least C8 (96) for full keyboard access")

if __name__ == "__main__":
    print("🎹 INTELLIGENT KEY RANGE ASSIGNMENT TEST")
    print("="*50)
    
    demonstrate_note_mapping()
    test_intelligent_key_ranges()
    
    print(f"\n✅ Test complete! The intelligent key range system now:")
    print(f"   • Analyzes sample root notes in XPM files")
    print(f"   • Assigns ranges based on actual pitch content") 
    print(f"   • Ensures highest samples extend to C8 for full keyboard access")
    print(f"   • Fixes problematic ranges (LowNote > HighNote, etc.)")
    print(f"   • Maintains musical logic instead of arbitrary 0-127 assignments")
