#!/usr/bin/env python3
"""
Test script to demonstrate and fix the keygroup range issue after transposing.

Problem: After transposing XPM files (especially -24 se            elif current_high < 96:  # Less than C7
                effective_high = current_high + transpose_change
                
                # For transpose down (negative values), extend HIGH range significantly  
                if transpose_change < -12:  # Significant transpose down
                    new_low = max(0, current_low - 12)
                    new_high = 127  # Full high range for maximum compatibility
                    print(f"    KG{i+1}: Expanded for large transpose: {current_low}-{current_high} → {new_low}-{new_high}")
                elif effective_high < 84:  # Less than C6 after transpose
                    new_low = max(0, int(current_low + transpose_change - 12))
                    new_high = min(127, int(current_high + 36))  # More aggressive expansion
                    print(f"    KG{i+1}: Expanded range {current_low}-{current_high} → {new_low}-{new_high}")
                else:
                    new_low = current_low
                    new_high = min(127, max(current_high, 96))
                    print(f"    KG{i+1}: Extended high range {current_high} → {new_high}")otes C5 and above 
don't play because the original keygroup LowNote/HighNote ranges restrict playability.

Solution: The enhanced transpose functionality now updates both KeygroupMasterTranspose 
AND expands keygroup ranges to ensure full keyboard playability.
"""

import xml.etree.ElementTree as ET
import os
import tempfile
import shutil

def create_test_xpm_with_limited_range():
    """Create a test XPM with restricted keygroup ranges that would cause the C5+ issue."""
    
    xpm_content = '''<?xml version='1.0' encoding='utf-8'?>
<MPC>
  <Program type="Keygroup">
    <Application_Version>3.5.0</Application_Version>
    <KeygroupMasterTranspose>0.0</KeygroupMasterTranspose>
    <KeygroupNumKeygroups>3</KeygroupNumKeygroups>
    <Instruments>
      <!-- Single-note keygroup - will cause C5+ issues -->
      <Instrument>
        <LowNote>60</LowNote>
        <HighNote>60</HighNote>
        <Layer>
          <RootNote>60</RootNote>
          <SampleFile>sample1.wav</SampleFile>
        </Layer>
      </Instrument>
      
      <!-- Limited range keygroup - will cause C5+ issues -->
      <Instrument>
        <LowNote>48</LowNote>
        <HighNote>72</HighNote>
        <Layer>
          <RootNote>60</RootNote>
          <SampleFile>sample2.wav</SampleFile>
        </Layer>
      </Instrument>
      
      <!-- Another limited range -->
      <Instrument>
        <LowNote>36</LowNote>
        <HighNote>67</HighNote>
        <Layer>
          <RootNote>48</RootNote>
          <SampleFile>sample3.wav</SampleFile>
        </Layer>
      </Instrument>
    </Instruments>
  </Program>
</MPC>'''
    
    return xpm_content

def analyze_keygroup_ranges(xmp_path):
    """Analyze the keygroup ranges in an XPM file."""
    tree = ET.parse(xmp_path)
    root = tree.getroot()
    
    print(f"\\nAnalyzing: {os.path.basename(xmp_path)}")
    
    # Get transpose value
    transpose_elem = root.find(".//KeygroupMasterTranspose")
    transpose = float(transpose_elem.text) if transpose_elem is not None and transpose_elem.text else 0.0
    print(f"KeygroupMasterTranspose: {transpose}")
    
    # Analyze each keygroup
    instruments = root.findall(".//Instrument")
    print(f"Number of keygroups: {len(instruments)}")
    
    issues = []
    for i, instrument in enumerate(instruments):
        low_elem = instrument.find("LowNote")
        high_elem = instrument.find("HighNote")
        
        if low_elem is not None and high_elem is not None:
            low_note = int(low_elem.text) if low_elem.text else 0
            high_note = int(high_elem.text) if high_elem.text else 127
            
            # Calculate effective range after transpose
            effective_low = low_note + transpose
            effective_high = high_note + transpose
            
            print(f"  KG{i+1}: Range {low_note}-{high_note} (MIDI notes)")
            print(f"       After transpose: {effective_low:.1f}-{effective_high:.1f}")
            
            # Check for C5+ playability (MIDI note 72 = C5)
            if high_note < 72:
                issues.append(f"KG{i+1}: High note {high_note} < C5 (72) - C5+ won't play")
            if low_note == high_note:
                issues.append(f"KG{i+1}: Single-note keygroup ({low_note}) - limited playability")
            if effective_high < 84:  # C6
                issues.append(f"KG{i+1}: Effective high {effective_high:.1f} < C6 after transpose")
    
    if issues:
        print(f"\\n❌ ISSUES FOUND:")
        for issue in issues:
            print(f"   {issue}")
    else:
        print(f"\\n✅ No playability issues detected")
    
    return len(issues) > 0

def apply_enhanced_transpose_with_range_fix(xmp_path, transpose_amount):
    """Apply transpose with the enhanced range fixing logic."""
    tree = ET.parse(xmp_path)
    root = tree.getroot()
    
    # Get current transpose
    transpose_elem = root.find(".//KeygroupMasterTranspose")
    if transpose_elem is None:
        program_elem = root.find(".//Program")
        transpose_elem = ET.SubElement(program_elem, "KeygroupMasterTranspose")
    
    old_transpose = float(transpose_elem.text) if transpose_elem.text else 0.0
    new_transpose = transpose_amount
    
    # Set new transpose
    transpose_elem.text = f"{new_transpose:.6f}"
    
    # Apply enhanced range fixing
    fix_keygroup_ranges_after_transpose(root, old_transpose, new_transpose)
    
    # Save
    tree.write(xmp_path, encoding="utf-8", xml_declaration=True)
    print(f"\\n🔧 Applied transpose {transpose_amount} with range fixes")

def fix_keygroup_ranges_after_transpose(root, old_transpose, new_transpose):
    """Enhanced keygroup range fixing logic."""
    instruments = root.findall(".//Instrument")
    transpose_change = new_transpose - old_transpose
    
    for i, instrument in enumerate(instruments):
        low_note_elem = instrument.find("LowNote")
        high_note_elem = instrument.find("HighNote")
        
        if low_note_elem is not None and high_note_elem is not None:
            current_low = int(low_note_elem.text) if low_note_elem.text else 60
            current_high = int(high_note_elem.text) if high_note_elem.text else 60
            
            # Get root note for intelligent decisions
            layer = instrument.find("Layer")
            root_note = 60
            if layer is not None:
                root_note_elem = layer.find("RootNote")
                if root_note_elem is not None and root_note_elem.text:
                    root_note = int(root_note_elem.text)
            
            # Apply fixing strategy  
            print(f"    KG{i+1}: transpose_change = {transpose_change}")
            if current_low == current_high:
                # Single-note keygroup - expand to full range
                new_low = 0
                new_high = 127
                print(f"    KG{i+1}: Expanded single-note {current_low} → full range (0-127)")
            
            elif current_high < 96:  # Less than C7
                effective_high = current_high + transpose_change
                
                # For transpose down (negative values), extend HIGH range significantly  
                if transpose_change < -12:  # Significant transpose down
                    new_low = max(0, current_low - 12)
                    new_high = 127  # Full high range for maximum compatibility
                    print(f"    KG{i+1}: Expanded for large transpose: {current_low}-{current_high} → {new_low}-{new_high}")
                elif effective_high < 84:  # Less than C6 after transpose
                    new_low = max(0, int(current_low + transpose_change - 12))
                    new_high = min(127, int(current_high + 36))  # More aggressive expansion
                    print(f"    KG{i+1}: Expanded range {current_low}-{current_high} → {new_low}-{new_high}")
                else:
                    new_low = current_low
                    new_high = min(127, max(current_high, 96))
                    print(f"    KG{i+1}: Extended high range {current_high} → {new_high}")
            else:
                # Range already adequate
                new_low = current_low
                new_high = current_high
                print(f"    KG{i+1}: Range {current_low}-{current_high} adequate, no change")
            
            # Apply new ranges
            low_note_elem.text = str(new_low)
            high_note_elem.text = str(new_high)

def main():
    """Test the enhanced transpose functionality."""
    print("🧪 Testing Enhanced Transpose with Keygroup Range Fix")
    print("=" * 60)
    
    # Create temporary test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xpm', delete=False) as f:
        f.write(create_test_xpm_with_limited_range())
        test_file = f.name
    
    try:
        print("\\n1️⃣ BEFORE TRANSPOSE (Original file with issues)")
        has_issues_before = analyze_keygroup_ranges(test_file)
        
        print("\\n2️⃣ APPLYING TRANSPOSE -24 WITH ENHANCED RANGE FIX")
        apply_enhanced_transpose_with_range_fix(test_file, -24.0)
        
        print("\\n3️⃣ AFTER ENHANCED TRANSPOSE (Fixed)")
        has_issues_after = analyze_keygroup_ranges(test_file)
        
        print("\\n" + "=" * 60)
        if has_issues_before and not has_issues_after:
            print("✅ SUCCESS: Enhanced transpose fixed the C5+ playability issues!")
        elif has_issues_before and has_issues_after:
            print("⚠️  PARTIAL: Some issues may remain")
        elif not has_issues_before:
            print("ℹ️  INFO: No issues detected in original file")
        
        print("\\n📝 SUMMARY:")
        print("   - KeygroupMasterTranspose: Updated to -24.0")
        print("   - Keygroup ranges: Expanded to ensure C0-C8 playability")
        print("   - C5+ notes: Should now play correctly")
        
    finally:
        os.unlink(test_file)

if __name__ == "__main__":
    main()
