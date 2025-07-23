#!/usr/bin/env python3
"""
Real-time Analysis of User's XPM Files
Using the Advanced XPM Doctor Logic
"""

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

def analyze_xpm_file(file_path):
    """Comprehensive XPM file analysis using Advanced XPM Doctor logic"""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Basic file info
        format_type = "MPC-V (Advanced)" if "MPC-V" in str(tree) or root.tag == "InstrumentV2" else "Legacy MPC"
        
        # Get master transpose
        master_transpose_elem = root.find('.//KeygroupMasterTranspose')
        master_transpose = float(master_transpose_elem.text) if master_transpose_elem is not None else 0
        
        # Count declared vs actual keygroups
        declared_count_elem = root.find('.//KeygroupNumKeygroups')
        declared_count = int(declared_count_elem.text) if declared_count_elem is not None else 0
        
        # Count actual active keygroups
        keygroups = root.findall('.//Keygroup')
        active_count = 0
        keygroup_issues = []
        
        for i, kg in enumerate(keygroups):
            # Check if keygroup has meaningful content
            sample_elem = kg.find('.//KeygroupSampleName')
            if sample_elem is not None and sample_elem.text and sample_elem.text.strip():
                active_count += 1
                
                # Check range issues
                low_note_elem = kg.find('.//KeygroupLowNote')
                high_note_elem = kg.find('.//KeygroupHighNote')
                
                if low_note_elem is not None and high_note_elem is not None:
                    low_note = int(low_note_elem.text)
                    high_note = int(high_note_elem.text)
                    
                    # Check for problematic ranges
                    if low_note == high_note:
                        keygroup_issues.append(f"KG{i+1}: Single-note range ({low_note}) - limited playability")
                    elif high_note < 72:  # Below C5
                        keygroup_issues.append(f"KG{i+1}: Low range ending at {high_note} - C5+ won't play")
                    elif high_note < 84:  # Below C6
                        keygroup_issues.append(f"KG{i+1}: Limited high range ({high_note}) - C6+ won't play")
        
        # Determine status
        issues = []
        
        if declared_count != active_count:
            issues.append(f"Keygroup count mismatch: Declared {declared_count}, actual {active_count}")
            
        if active_count == 0:
            issues.append("Empty instrument - no active keygroups")
            
        issues.extend(keygroup_issues)
        
        if declared_count > active_count:
            empty_count = declared_count - active_count
            issues.append(f"{empty_count} empty keygroups declared but not used")
        
        # Status assessment
        if len(issues) > 2 or active_count == 0:
            status = "🚨 CRITICAL"
        elif len(issues) > 0:
            status = "⚠️ NEEDS ATTENTION"
        else:
            status = "✅ HEALTHY"
        
        return {
            'format': format_type,
            'master_transpose': master_transpose,
            'declared_count': declared_count,
            'active_count': active_count,
            'status': status,
            'issues': issues
        }
        
    except Exception as e:
        return {
            'format': 'Unknown',
            'master_transpose': 0,
            'declared_count': 0,
            'active_count': 0,
            'status': '❌ ERROR',
            'issues': [f"Parse error: {str(e)}"]
        }

def main():
    print("🔍 ANALYZING USER'S XPM FILES WITH ADVANCED XPM DOCTOR LOGIC")
    print("=" * 60)
    
    # Find XPM files in current directory
    xpm_files = list(Path('.').glob('*.xpm'))
    
    if not xpm_files:
        print("❌ No XPM files found in current directory")
        return
    
    print(f"📁 Found {len(xpm_files)} XPM files to analyze:\n")
    
    for xpm_file in xpm_files:
        print(f"📋 ANALYZING: {xpm_file.name}")
        print("-" * 40)
        
        analysis = analyze_xpm_file(xpm_file)
        
        print(f"   • File Format: {analysis['format']}")
        print(f"   • Master Transpose: {analysis['master_transpose']} semitones")
        print(f"   • Declared Keygroups: {analysis['declared_count']}")
        print(f"   • Actual Active Keygroups: {analysis['active_count']}")
        print(f"   • Status: {analysis['status']}")
        
        if analysis['issues']:
            print(f"\n❌ ISSUES DETECTED:")
            for issue in analysis['issues']:
                print(f"   • {issue}")
        else:
            print(f"\n✅ No issues detected")
        
        print("\n")
    
    print("🩺 SOLUTION:")
    print("The Advanced XPM Doctor in your main application will:")
    print("✅ Automatically detect all these issues")
    print("✅ Apply comprehensive fixes")
    print("✅ Ensure full keyboard playability (C5, C6, C7, C8)")
    print("✅ Correct keygroup count mismatches")
    print("✅ Expand limited ranges to 0-127")
    print("\nTo use: Run the main app → Batch Transpose → '🩺 Advanced XPM Doctor'")

if __name__ == "__main__":
    main()
