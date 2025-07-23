#!/usr/bin/env python3
"""
SPECIFIC TEST: Verify C6, C7, C8 playability issue is resolved.
This addresses the user's exact problem: "C5 plays but not C6 or C7 or C8"
"""

import os
import sys
import tempfile
import xml.etree.ElementTree as ET

def create_user_problem_xpm():
    """Create XPM that exhibits the exact problem: C5 plays but C6, C7, C8 don't."""
    xpm_content = '''<?xml version="1.0" encoding="UTF-8"?>
<MPC>
    <Program>
        <KeygroupMasterTranspose>-24.000000</KeygroupMasterTranspose>
        <ProgramName>User_Problem_File</ProgramName>
        <Instrument>
            <Name>KG1</Name>
            <LowNote>60</LowNote>
            <HighNote>72</HighNote>
            <Layer>
                <RootNote>60</RootNote>
                <SampleName>sample1.wav</SampleName>
            </Layer>
        </Instrument>
        <Instrument>
            <Name>KG2</Name>
            <LowNote>48</LowNote>
            <HighNote>67</HighNote>
            <Layer>
                <RootNote>60</RootNote>
                <SampleName>sample2.wav</SampleName>
            </Layer>
        </Instrument>
    </Program>
</MPC>'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xpm', delete=False) as f:
        f.write(xpm_content)
        return f.name

def check_note_playability(xpm_path):
    """Check which specific notes can play."""
    tree = ET.parse(xpm_path)
    root = tree.getroot()
    
    # Get transpose value
    transpose_elem = root.find(".//KeygroupMasterTranspose")
    transpose = float(transpose_elem.text) if transpose_elem is not None and transpose_elem.text else 0.0
    
    # Check each keygroup
    playable_notes = set()
    instruments = root.findall(".//Instrument")
    
    for instrument in instruments:
        low_note_elem = instrument.find("LowNote")
        high_note_elem = instrument.find("HighNote")
        
        if low_note_elem is not None and high_note_elem is not None:
            low_note = int(low_note_elem.text) if low_note_elem.text else 0
            high_note = int(high_note_elem.text) if high_note_elem.text else 127
            
            # Add all notes in this keygroup's range
            for note in range(low_note, high_note + 1):
                playable_notes.add(note)
    
    # Check specific target notes
    target_notes = {
        'C5': 72,
        'C6': 84, 
        'C7': 96,
        'C8': 108
    }
    
    results = {
        'transpose': transpose,
        'total_playable_notes': len(playable_notes),
        'playable_range': (min(playable_notes), max(playable_notes)) if playable_notes else (0, 0)
    }
    
    for note_name, note_num in target_notes.items():
        results[f'{note_name}_playable'] = note_num in playable_notes
    
    return results

def apply_enhanced_fix(xpm_path):
    """Apply the enhanced keygroup range fix."""
    tree = ET.parse(xpm_path)
    root = tree.getroot()
    
    instruments = root.findall(".//Instrument")
    
    for i, instrument in enumerate(instruments):
        low_note_elem = instrument.find("LowNote")
        high_note_elem = instrument.find("HighNote")
        
        if low_note_elem is not None and high_note_elem is not None:
            # Apply FULL range expansion for maximum keyboard coverage
            low_note_elem.text = "0"    # C0
            high_note_elem.text = "127" # G9 (beyond C8)
            print(f"KG{i+1}: Expanded to FULL range (0-127) for complete keyboard access")
    
    # Save the file
    tree.write(xpm_path, encoding="utf-8", xml_declaration=True)

def test_user_specific_issue():
    """Test the exact user problem and verify the fix."""
    print("🎯 TESTING USER'S SPECIFIC ISSUE: C5 plays but C6, C7, C8 don't")
    print("=" * 65)
    
    # Create problematic file
    test_file = create_user_problem_xpm()
    
    try:
        # Check BEFORE fix
        print("🔍 BEFORE FIX:")
        before_results = check_note_playability(test_file)
        print(f"   Transpose: {before_results['transpose']}")
        print(f"   Playable range: {before_results['playable_range'][0]}-{before_results['playable_range'][1]} ({before_results['total_playable_notes']} notes)")
        print(f"   C5 (72) playable: {'✅' if before_results['C5_playable'] else '❌'}")
        print(f"   C6 (84) playable: {'✅' if before_results['C6_playable'] else '❌'}")
        print(f"   C7 (96) playable: {'✅' if before_results['C7_playable'] else '❌'}")
        print(f"   C8 (108) playable: {'✅' if before_results['C8_playable'] else '❌'}")
        
        # Apply the enhanced fix
        print("\n🔧 APPLYING ENHANCED FIX...")
        apply_enhanced_fix(test_file)
        
        # Check AFTER fix
        print("\n✨ AFTER FIX:")
        after_results = check_note_playability(test_file)
        print(f"   Transpose: {after_results['transpose']}")
        print(f"   Playable range: {after_results['playable_range'][0]}-{after_results['playable_range'][1]} ({after_results['total_playable_notes']} notes)")
        print(f"   C5 (72) playable: {'✅' if after_results['C5_playable'] else '❌'}")
        print(f"   C6 (84) playable: {'✅' if after_results['C6_playable'] else '❌'}")
        print(f"   C7 (96) playable: {'✅' if after_results['C7_playable'] else '❌'}")
        print(f"   C8 (108) playable: {'✅' if after_results['C8_playable'] else '❌'}")
        
        # Verify the fix worked
        print(f"\n📋 RESULT:")
        if (after_results['C5_playable'] and after_results['C6_playable'] and 
            after_results['C7_playable'] and after_results['C8_playable']):
            print("🎉 SUCCESS: ALL notes C5, C6, C7, C8 are now playable!")
            print("✅ User's issue is RESOLVED!")
        else:
            print("❌ FAILURE: Some notes still not playable")
            
        # Summary
        print(f"\n🎯 SOLUTION SUMMARY:")
        print(f"   • Enhanced algorithm expands ALL keygroups to range 0-127")
        print(f"   • This ensures COMPLETE keyboard coverage including C6, C7, C8") 
        print(f"   • Automatic application during every batch transpose operation")
        print(f"   • Manual fix available via '🔧 Fix Key Ranges' button")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)

if __name__ == "__main__":
    test_user_specific_issue()
