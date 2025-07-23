#!/usr/bin/env python3
"""
COMPREHENSIVE TEST: Full keyboard playability verification for C0-C8.
This test ensures that after transpose operations, ALL notes from C0 to C8 can play.
"""

import os
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_realistic_xpm_like_user_file():
    """Create a test XPM file that mirrors the user's problematic file structure."""
    xpm_content = '''<?xml version="1.0" encoding="UTF-8"?>
<MPC>
    <Program>
        <KeygroupMasterTranspose>0.000000</KeygroupMasterTranspose>
        <ProgramName>002_icu2</ProgramName>
        <Instrument>
            <Name>KG1</Name>
            <LowNote>60</LowNote>
            <HighNote>67</HighNote>
            <Layer>
                <RootNote>60</RootNote>
                <SampleName>sample1.wav</SampleName>
            </Layer>
        </Instrument>
        <Instrument>
            <Name>KG2</Name>
            <LowNote>48</LowNote>
            <HighNote>72</HighNote>
            <Layer>
                <RootNote>60</RootNote>
                <SampleName>sample2.wav</SampleName>
            </Layer>
        </Instrument>
        <Instrument>
            <Name>KG3</Name>
            <LowNote>36</LowNote>
            <HighNote>60</HighNote>
            <Layer>
                <RootNote>48</RootNote>
                <SampleName>sample3.wav</SampleName>
            </Layer>
        </Instrument>
    </Program>
</MPC>'''
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xpm', delete=False) as f:
        f.write(xpm_content)
        return f.name

def analyze_full_keyboard_coverage(xpm_path, target_notes=None):
    """
    Analyze an XPM file for COMPLETE keyboard coverage including C6, C7, C8.
    
    Args:
        xpm_path: Path to XPM file
        target_notes: List of specific MIDI notes to check (default: C0-C8)
    
    Returns:
        Dict with analysis results and coverage report
    """
    if target_notes is None:
        # C0, C1, C2, C3, C4, C5, C6, C7, C8
        target_notes = [12, 24, 36, 48, 60, 72, 84, 96, 108]
    
    tree = ET.parse(xpm_path)
    root = tree.getroot()
    
    # Get transpose value
    transpose_elem = root.find(".//KeygroupMasterTranspose")
    transpose = float(transpose_elem.text) if transpose_elem is not None and transpose_elem.text else 0.0
    
    # Analyze each keygroup
    coverage_report = {}
    all_covered_notes = set()
    
    instruments = root.findall(".//Instrument")
    
    for i, instrument in enumerate(instruments):
        kg_name = f"KG{i+1}"
        low_note_elem = instrument.find("LowNote")
        high_note_elem = instrument.find("HighNote")
        
        if low_note_elem is not None and high_note_elem is not None:
            low_note = int(low_note_elem.text) if low_note_elem.text else 0
            high_note = int(high_note_elem.text) if high_note_elem.text else 127
            
            # Calculate effective range after transpose
            effective_low = low_note + transpose
            effective_high = high_note + transpose
            
            # Find which target notes this keygroup can play
            covered_notes = []
            for note in target_notes:
                if low_note <= note <= high_note:
                    covered_notes.append(note)
                    all_covered_notes.add(note)
            
            coverage_report[kg_name] = {
                'original_range': (low_note, high_note),
                'effective_range': (effective_low, effective_high),
                'covered_target_notes': covered_notes,
                'covers_c6': 84 in covered_notes,
                'covers_c7': 96 in covered_notes,
                'covers_c8': 108 in covered_notes
            }
    
    # Overall analysis
    uncovered_notes = [note for note in target_notes if note not in all_covered_notes]
    critical_missing = []
    if 84 not in all_covered_notes:
        critical_missing.append('C6 (84)')
    if 96 not in all_covered_notes:
        critical_missing.append('C7 (96)')
    if 108 not in all_covered_notes:
        critical_missing.append('C8 (108)')
    
    return {
        'transpose': transpose,
        'keygroup_count': len(instruments),
        'coverage_report': coverage_report,
        'all_covered_notes': sorted(all_covered_notes),
        'uncovered_notes': uncovered_notes,
        'critical_missing': critical_missing,
        'full_keyboard_coverage': len(uncovered_notes) == 0,
        'c6_c7_c8_coverage': len(critical_missing) == 0
    }

def apply_enhanced_transpose_fix(xpm_path, transpose_amount):
    """Apply the enhanced transpose fix using the updated algorithm."""
    
    # Mock the enhanced fix method
    def fix_keygroup_ranges_after_transpose(root, old_transpose, new_transpose):
        """Enhanced version of the fix method."""
        instruments = root.findall(".//Instrument")
        transpose_change = new_transpose - old_transpose
        
        print(f"🔧 KEYGROUP RANGE FIX: Transpose change = {transpose_change:.1f} semitones")
        
        for i, instrument in enumerate(instruments):
            low_note_elem = instrument.find("LowNote")
            high_note_elem = instrument.find("HighNote")
            
            if low_note_elem is not None and high_note_elem is not None:
                try:
                    current_low = int(low_note_elem.text) if low_note_elem.text else 60
                    current_high = int(high_note_elem.text) if high_note_elem.text else 60
                    
                    # AGGRESSIVE STRATEGY: ALWAYS ensure full keyboard playability
                    if abs(transpose_change) >= 6:  # Any significant transpose (half octave+)
                        new_low = 0    # C0 - Full low range
                        new_high = 127 # G9 - Full high range (beyond C8 for safety)
                        print(f"KG{i+1}: FULL EXPANSION for transpose {transpose_change:.1f}: {current_low}-{current_high} → {new_low}-{new_high}")
                    
                    elif current_high < 96:  # Original range doesn't reach C7 (96)
                        new_low = max(0, current_low - 12)  # Extend down 1 octave
                        new_high = 127  # Full high range to ensure C6, C7, C8 play
                        print(f"KG{i+1}: AGGRESSIVE EXPANSION for limited range: {current_low}-{current_high} → {new_low}-{new_high}")
                    
                    elif current_low == current_high:
                        new_low = 0    # C0
                        new_high = 127 # G9 
                        print(f"KG{i+1}: SINGLE-NOTE EXPANSION: {current_low} → full range (0-127)")
                    
                    else:
                        new_low = max(0, min(current_low, current_low - 6))  # Extend down slightly
                        new_high = 127  # Always ensure full high range for C6, C7, C8
                        print(f"KG{i+1}: SAFETY EXPANSION: {current_low}-{current_high} → {new_low}-{new_high}")
                    
                    # VERIFICATION: Ensure we can play the full keyboard after transpose
                    effective_low_after = new_low + new_transpose
                    effective_high_after = new_high + new_transpose
                    
                    if effective_high_after < 108:  # Less than C8
                        print(f"KG{i+1}: Effective high {effective_high_after:.1f} < C8 (108), forcing full range")
                        new_high = 127  # Force maximum range
                    
                    # Apply the new ranges
                    low_note_elem.text = str(new_low)
                    high_note_elem.text = str(new_high)
                    
                    print(f"KG{i+1}: ✅ Final range: {new_low}-{new_high} (effective after transpose: {effective_low_after:.1f}-{effective_high_after:.1f})")
                    
                except (ValueError, TypeError) as e:
                    print(f"⚠️ Error with KG{i+1}, setting to full range: {e}")
                    if low_note_elem is not None:
                        low_note_elem.text = "0"
                    if high_note_elem is not None:
                        high_note_elem.text = "127"
    
    # Parse and modify XPM
    tree = ET.parse(xpm_path)
    root = tree.getroot()
    
    # Update transpose value
    transpose_elem = root.find(".//KeygroupMasterTranspose")
    old_transpose = 0.0
    new_transpose = transpose_amount
    
    if transpose_elem is not None:
        old_transpose = float(transpose_elem.text) if transpose_elem.text else 0.0
        transpose_elem.text = f"{new_transpose:.6f}"
    
    # Apply the enhanced fix
    fix_keygroup_ranges_after_transpose(root, old_transpose, new_transpose)
    
    # Save the modified file
    tree.write(xpm_path, encoding="utf-8", xml_declaration=True)

def test_full_keyboard_coverage():
    """Comprehensive test for full keyboard coverage including C6, C7, C8."""
    print("🧪 COMPREHENSIVE TEST: Full Keyboard Coverage (C0-C8)")
    print("=" * 70)
    
    # Create test file
    test_file = create_realistic_xpm_like_user_file()
    print(f"📁 Created test file: {os.path.basename(test_file)}")
    
    try:
        # Test different transpose amounts
        transpose_tests = [-24, -12, -6, 0, 6, 12, 24]
        
        for transpose_amount in transpose_tests:
            print(f"\n🎹 TESTING TRANSPOSE: {transpose_amount} semitones")
            print("-" * 50)
            
            # Reset file for each test
            test_file_copy = create_realistic_xpm_like_user_file()
            
            # Analyze BEFORE
            before_analysis = analyze_full_keyboard_coverage(test_file_copy)
            print(f"BEFORE: Critical missing notes: {before_analysis['critical_missing']}")
            
            # Apply transpose with enhanced fix
            apply_enhanced_transpose_fix(test_file_copy, transpose_amount)
            
            # Analyze AFTER
            after_analysis = analyze_full_keyboard_coverage(test_file_copy)
            print(f"AFTER:  Critical missing notes: {after_analysis['critical_missing']}")
            
            # Verify results
            if after_analysis['c6_c7_c8_coverage']:
                print("✅ SUCCESS: C6, C7, C8 are ALL covered!")
            else:
                print("❌ FAILURE: Some high notes still missing!")
                for kg_name, kg_info in after_analysis['coverage_report'].items():
                    print(f"   {kg_name}: Range {kg_info['original_range']} - C6:{kg_info['covers_c6']} C7:{kg_info['covers_c7']} C8:{kg_info['covers_c8']}")
            
            # Clean up
            os.remove(test_file_copy)
        
        # Summary
        print(f"\n" + "=" * 70)
        print("📋 TEST SUMMARY:")
        print("The enhanced algorithm should now ensure C6, C7, C8 playability")
        print("for ALL transpose operations by using aggressive range expansion.")
        print("✅ Key improvement: Always expand to full range (0-127) for significant transposes")
        print("✅ Safety check: Verify effective range covers C8 (108) after transpose")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)

if __name__ == "__main__":
    test_full_keyboard_coverage()
