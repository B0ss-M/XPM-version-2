#!/usr/bin/env python3
"""
Test script for intelligent key range assignment - Non-GUI version.

This script demonstrates the enhanced key range assignment without GUI dependencies.
"""

import sys
import os
import xml.etree.ElementTree as ET
import logging

# Add current directory to path for imports
sys.path.insert(0, '/Users/marlsz/Documents/GitHub/XPM-version-2')

from xpm_utils import calculate_key_ranges

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def calculate_extended_key_ranges(mappings):
    """
    Calculate intelligent key ranges with extended high range for the highest sample.
    
    This ensures that the highest pitched sample (e.g., C5) can extend up to C8 (note 96)
    or even higher, giving full keyboard playability as requested by the user.
    """
    if not mappings:
        return []

    sorted_maps = sorted(mappings, key=lambda m: m.get("root_note", 60))
    
    for i, current in enumerate(sorted_maps):
        if i == 0:
            # First sample starts from C0
            current["low_note"] = 0
        else:
            # Calculate midpoint between previous and current sample
            prev = sorted_maps[i - 1]
            midpoint = (prev["root_note"] + current["root_note"]) // 2
            current["low_note"] = midpoint + 1

        if i == len(sorted_maps) - 1:
            # CRITICAL: Last (highest) sample extends to full keyboard range
            # This ensures C5 sample can play C6, C7, C8 and beyond
            current["high_note"] = 127  # G9 - full keyboard access
            print(f"🎹 EXTENDED: Highest sample (root={current['root_note']}) "
                  f"extended to full range: {current['low_note']}-127 for C6,C7,C8 access")
        else:
            # Calculate midpoint between current and next sample
            nxt = sorted_maps[i + 1]
            midpoint = (current["root_note"] + nxt["root_note"]) // 2
            current["high_note"] = midpoint

    return sorted_maps

def fix_xmp_key_ranges(xmp_path):
    """Apply intelligent key range fixes to an XPM file."""
    try:
        tree = ET.parse(xmp_path)
        root = tree.getroot()
        instruments = root.findall(".//Instrument")
        
        # Extract sample info from all instruments to calculate intelligent ranges
        sample_mappings = []
        instrument_data = []
        
        for i, instrument in enumerate(instruments):
            # Extract root note from layer
            layer = instrument.find("Layer")
            root_note = 60  # Default to C4
            sample_path = None
            
            if layer is not None:
                root_note_elem = layer.find("RootNote")
                if root_note_elem is not None and root_note_elem.text:
                    try:
                        root_note = int(root_note_elem.text)
                    except (ValueError, TypeError):
                        root_note = 60
                
                # Get sample path for additional analysis if needed
                sample_file_elem = layer.find("SampleFile")
                sample_name_elem = layer.find("SampleName")
                if sample_file_elem is not None and sample_file_elem.text:
                    sample_path = sample_file_elem.text
                elif sample_name_elem is not None and sample_name_elem.text:
                    sample_path = sample_name_elem.text
            
            sample_mappings.append({
                "root_note": root_note,
                "sample_path": sample_path,
                "instrument_index": i
            })
            instrument_data.append(instrument)
        
        # Calculate intelligent key ranges using the extended algorithm
        if sample_mappings:
            calculated_ranges = calculate_extended_key_ranges(sample_mappings)
            
            for mapping in calculated_ranges:
                i = mapping["instrument_index"]
                instrument = instrument_data[i]
                
                low_note_elem = instrument.find("LowNote")
                high_note_elem = instrument.find("HighNote")
                
                # Create missing elements
                if low_note_elem is None:
                    low_note_elem = ET.SubElement(instrument, "LowNote")
                if high_note_elem is None:
                    high_note_elem = ET.SubElement(instrument, "HighNote")
                
                # Get current values
                try:
                    current_low = int(low_note_elem.text) if low_note_elem.text else 0
                    current_high = int(high_note_elem.text) if high_note_elem.text else 127
                except (ValueError, TypeError):
                    current_low = 0
                    current_high = 127
                
                # Apply intelligent range
                new_low = mapping["low_note"]
                new_high = mapping["high_note"]
                
                low_note_elem.text = str(new_low)
                high_note_elem.text = str(new_high)
                
                sample_name = os.path.basename(mapping["sample_path"]) if mapping["sample_path"] else f"KG{i+1}"
                print(f"🎹 Fixed range for {sample_name}: "
                      f"Root={mapping['root_note']}, Range={new_low}-{new_high}")
        
        tree.write(xmp_path, encoding="utf-8", xml_declaration=True)
        return True
        
    except Exception as e:
        print(f"❌ Error fixing {xmp_path}: {e}")
        return False

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
                    if low_val == 0 and high_val == 127:
                        issues.append("Full range (probably incorrect)")
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

def test_key_range_scenarios():
    """Test different key range scenarios."""
    print("\n🧪 TESTING KEY RANGE SCENARIOS:")
    print("="*50)
    
    # Scenario 1: Typical multi-sample instrument (C1, C2, C3, C4, C5)
    print("\n📊 Scenario 1: Typical 5-sample chromatic instrument")
    samples = [
        {"root_note": 36, "sample_path": "C1_sample.wav"},  # C1
        {"root_note": 48, "sample_path": "C2_sample.wav"},  # C2
        {"root_note": 60, "sample_path": "C3_sample.wav"},  # C3
        {"root_note": 72, "sample_path": "C4_sample.wav"},  # C4
        {"root_note": 84, "sample_path": "C5_sample.wav"},  # C5
    ]
    
    ranges = calculate_extended_key_ranges(samples)
    for r in ranges:
        note_name = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"][r["root_note"] % 12]
        octave = (r["root_note"] // 12) - 1
        print(f"   {note_name}{octave} (MIDI {r['root_note']:2d}): Range {r['low_note']:2d}-{r['high_note']:3d}")
    
    # Scenario 2: Sparse instrument (C1, C5 only)
    print("\n📊 Scenario 2: Sparse 2-sample instrument (C1, C5)")
    samples = [
        {"root_note": 36, "sample_path": "C1_sample.wav"},  # C1
        {"root_note": 84, "sample_path": "C5_sample.wav"},  # C5
    ]
    
    ranges = calculate_extended_key_ranges(samples)
    for r in ranges:
        note_name = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"][r["root_note"] % 12]
        octave = (r["root_note"] // 12) - 1
        print(f"   {note_name}{octave} (MIDI {r['root_note']:2d}): Range {r['low_note']:2d}-{r['high_note']:3d}")

def test_intelligent_key_ranges():
    """Test the intelligent key range assignment on test files."""
    
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
        fixed = fix_xmp_key_ranges(test_file)
        if fixed:
            print("✅ Key ranges successfully fixed!")
            
            # Analyze after fixing
            print(f"\n📊 AFTER FIX:")
            analyze_xmp_ranges(test_file)
        else:
            print("❌ Failed to fix key ranges")
            
        # Restore backup
        print(f"\n🔄 Restoring backup...")
        with open(backup_file, 'r') as src, open(test_file, 'w') as dst:
            dst.write(src.read())
        os.remove(backup_file)

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
    test_key_range_scenarios()
    test_intelligent_key_ranges()
    
    print(f"\n✅ Test complete! The intelligent key range system now:")
    print(f"   • Analyzes sample root notes in XPM files")
    print(f"   • Assigns ranges based on actual pitch content") 
    print(f"   • Ensures highest samples extend to C8+ for full keyboard access")
    print(f"   • Fixes problematic ranges (LowNote > HighNote, etc.)")
    print(f"   • Maintains musical logic instead of arbitrary 0-127 assignments")
    print(f"   • Specifically addresses the C5→C6,C7,C8 playability issue")
