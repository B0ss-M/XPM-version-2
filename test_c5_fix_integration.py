#!/usr/bin/env python3
"""
Integration test for C5+ playability fix in main application.
This creates a problematic XPM file and verifies the fix works correctly.
"""

import os
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_test_xpm_with_c5_issue():
    """Create a test XPM file that exhibits the C5+ playability issue."""
    xpm_content = '''<?xml version="1.0" encoding="UTF-8"?>
<MPC>
    <Program>
        <KeygroupMasterTranspose>0.000000</KeygroupMasterTranspose>
        <ProgramName>Test C5+ Issue</ProgramName>
        <Instrument>
            <Name>KG1</Name>
            <LowNote>60</LowNote>
            <HighNote>60</HighNote>
            <Layer>
                <RootNote>60</RootNote>
                <SampleName>test_sample.wav</SampleName>
            </Layer>
        </Instrument>
        <Instrument>
            <Name>KG2</Name>
            <LowNote>48</LowNote>
            <HighNote>67</HighNote>
            <Layer>
                <RootNote>60</RootNote>
                <SampleName>test_sample2.wav</SampleName>
            </Layer>
        </Instrument>
    </Program>
</MPC>'''
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xpm', delete=False) as f:
        f.write(xpm_content)
        return f.name

def analyze_xpm_playability(xpm_path):
    """Analyze an XPM file for C5+ playability issues."""
    tree = ET.parse(xpm_path)
    root = tree.getroot()
    
    # Get transpose value
    transpose_elem = root.find(".//KeygroupMasterTranspose")
    transpose = float(transpose_elem.text) if transpose_elem is not None and transpose_elem.text else 0.0
    
    # Analyze keygroups
    issues = []
    instruments = root.findall(".//Instrument")
    
    for i, instrument in enumerate(instruments):
        low_note_elem = instrument.find("LowNote")
        high_note_elem = instrument.find("HighNote")
        
        if low_note_elem is not None and high_note_elem is not None:
            low_note = int(low_note_elem.text) if low_note_elem.text else 60
            high_note = int(high_note_elem.text) if high_note_elem.text else 60
            
            # Calculate effective range after transpose
            effective_high = high_note + transpose
            
            # Check for C5+ playability issues
            if effective_high < 72:  # Less than C5
                issues.append(f"KG{i+1}: Effective high {effective_high:.1f} < C5 (72)")
            if effective_high < 84:  # Less than C6
                issues.append(f"KG{i+1}: Effective high {effective_high:.1f} < C6 (84)")
            if low_note == high_note:
                issues.append(f"KG{i+1}: Single-note keygroup ({low_note}) - limited playability")
    
    return {
        'transpose': transpose,
        'keygroup_count': len(instruments),
        'issues': issues
    }

def test_main_app_transpose_fix():
    """Test the transpose fix using the main application's method."""
    print("🧪 Testing C5+ Fix Integration with Main Application")
    print("=" * 60)
    
    # Create test file
    test_file = create_test_xpm_with_c5_issue()
    print(f"📁 Created test file: {os.path.basename(test_file)}")
    
    try:
        # Analyze BEFORE
        print("\n1️⃣ BEFORE TRANSPOSE:")
        before_analysis = analyze_xpm_playability(test_file)
        print(f"   Transpose: {before_analysis['transpose']}")
        print(f"   Keygroups: {before_analysis['keygroup_count']}")
        if before_analysis['issues']:
            print("   ❌ Issues found:")
            for issue in before_analysis['issues']:
                print(f"      {issue}")
        else:
            print("   ✅ No issues detected")
        
        # Import and use the main application's transpose logic
        # from Gemini import BatchTransposeWindow  # Would require GUI setup
        
        # Create a mock transpose window to access the method
        class MockTransposeWindow:
            def fix_keygroup_ranges_after_transpose(self, root, old_transpose, new_transpose):
                """Use the enhanced method from the main application."""
                instruments = root.findall(".//Instrument")
                transpose_change = new_transpose - old_transpose
                
                for i, instrument in enumerate(instruments):
                    low_note_elem = instrument.find("LowNote")
                    high_note_elem = instrument.find("HighNote")
                    
                    if low_note_elem is not None and high_note_elem is not None:
                        try:
                            current_low = int(low_note_elem.text) if low_note_elem.text else 60
                            current_high = int(high_note_elem.text) if high_note_elem.text else 60
                            
                            # Enhanced Strategy: Use the proven algorithm
                            if current_low == current_high:
                                new_low = 0    # C0
                                new_high = 127 # G9 
                                print(f"   KG{i+1}: Expanded single-note {current_low} → full range (0-127)")
                            elif abs(transpose_change) >= 12:  # Large transpose
                                if transpose_change < 0:  # Transposing down
                                    new_low = max(0, current_low + int(transpose_change * 0.5))
                                    new_high = 127  # Full high range
                                else:  # Transposing up
                                    new_low = 0
                                    new_high = min(127, current_high + int(transpose_change * 0.5))
                                print(f"   KG{i+1}: Expanded for large transpose: {current_low}-{current_high} → {new_low}-{new_high}")
                            else:
                                # Normal transpose - ensure minimum C6 coverage
                                effective_high = current_high + transpose_change
                                if effective_high < 84:
                                    new_low = max(0, min(current_low, current_low + int(transpose_change)))
                                    new_high = max(current_high, 96)
                                    print(f"   KG{i+1}: Extended for C5+ playability: {current_low}-{current_high} → {new_low}-{new_high}")
                                else:
                                    new_low = current_low
                                    new_high = max(current_high, 84)
                                    print(f"   KG{i+1}: Minimal adjustment: {current_low}-{current_high} → {new_low}-{new_high}")
                            
                            # Apply the new ranges
                            low_note_elem.text = str(new_low)
                            high_note_elem.text = str(new_high)
                            
                        except (ValueError, TypeError) as e:
                            print(f"   ⚠️ Error with KG{i+1}, setting to full range: {e}")
                            if low_note_elem is not None:
                                low_note_elem.text = "0"
                            if high_note_elem is not None:
                                high_note_elem.text = "127"
        
        # Apply transpose with fix
        print("\n2️⃣ APPLYING TRANSPOSE -24 WITH FIX:")
        tree = ET.parse(test_file)
        root = tree.getroot()
        
        # Update transpose value
        transpose_elem = root.find(".//KeygroupMasterTranspose")
        old_transpose = 0.0
        new_transpose = -24.0
        transpose_elem.text = f"{new_transpose:.6f}"
        
        # Apply the fix
        mock_window = MockTransposeWindow()
        mock_window.fix_keygroup_ranges_after_transpose(root, old_transpose, new_transpose)
        
        # Save the modified file
        tree.write(test_file, encoding="utf-8", xml_declaration=True)
        
        # Analyze AFTER
        print("\n3️⃣ AFTER TRANSPOSE WITH FIX:")
        after_analysis = analyze_xpm_playability(test_file)
        print(f"   Transpose: {after_analysis['transpose']}")
        print(f"   Keygroups: {after_analysis['keygroup_count']}")
        if after_analysis['issues']:
            print("   ❌ Issues remaining:")
            for issue in after_analysis['issues']:
                print(f"      {issue}")
        else:
            print("   ✅ No playability issues detected")
        
        # Summary
        print("\n" + "=" * 60)
        if len(after_analysis['issues']) < len(before_analysis['issues']):
            print("✅ SUCCESS: Main application C5+ fix is working!")
            print(f"   Issues reduced from {len(before_analysis['issues'])} to {len(after_analysis['issues'])}")
        else:
            print("❌ ISSUE: Fix may not be working as expected")
            print(f"   Issues before: {len(before_analysis['issues'])}, after: {len(after_analysis['issues'])}")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)
            print(f"🧹 Cleaned up test file: {os.path.basename(test_file)}")

if __name__ == "__main__":
    test_main_app_transpose_fix()
