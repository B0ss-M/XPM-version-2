#!/usr/bin/env python3
"""
Test the enhanced mapping correction tools on VOCAL STRING.xpm
"""

import os
import shutil
import sys
sys.path.append('/Users/marlsz/Documents/GitHub/XPM-version-2')

# Import our tools
from xpm_mapping_corrector import XPMappingCorrector

def test_vocal_string_correction():
    """Test the mapping corrector on VOCAL STRING.xpm"""
    
    original_file = '/Volumes/MPC LIVE 2/Test/VOCAL STRING.xpm'
    test_file = '/Users/marlsz/Documents/GitHub/XPM-version-2/VOCAL_STRING_TEST.xpm'
    
    if not os.path.exists(original_file):
        print("❌ Original VOCAL STRING.xpm not found")
        return
    
    # Create a copy for testing
    shutil.copy2(original_file, test_file)
    print(f"📋 Created test copy: {test_file}")
    
    # Analyze issues
    corrector = XPMappingCorrector()
    
    print("\n🔍 BEFORE FIXING:")
    print("=" * 50)
    issues = corrector.analyze_mapping_issues(test_file)
    
    print(f"Root note issues: {len(issues['incorrect_root_notes'])}")
    print(f"Velocity overlaps: {len(issues['velocity_overlaps'])}")
    print(f"Range problems: {len(issues['range_problems'])}")
    
    if issues['incorrect_root_notes']:
        print("\n🎵 Sample mapping issues:")
        for issue in issues['incorrect_root_notes'][:5]:  # Show first 5
            print(f"   {issue['sample_name']}: {issue['current_root']} → {issue['detected_root']} ({issue['note_name']})")
    
    # Apply fixes
    print("\n🛠️  APPLYING FIXES...")
    print("=" * 50)
    
    fixes = {
        'fix_root_notes': True,
        'fix_velocity_ranges': True,  
        'fix_instrument_ranges': True,
        'auto_detect_ranges': True
    }
    
    success = corrector.fix_mapping_issues(test_file, fixes)
    
    if success:
        print("✅ Fixes applied successfully!")
        
        # Analyze again to see improvements
        print("\n🔍 AFTER FIXING:")
        print("=" * 50)
        
        issues_after = corrector.analyze_mapping_issues(test_file)
        
        print(f"Root note issues: {len(issues_after['incorrect_root_notes'])}")
        print(f"Velocity overlaps: {len(issues_after['velocity_overlaps'])}")
        print(f"Range problems: {len(issues_after['range_problems'])}")
        
        # Show improvement
        root_fixes = len(issues['incorrect_root_notes']) - len(issues_after['incorrect_root_notes'])
        velocity_fixes = len(issues['velocity_overlaps']) - len(issues_after['velocity_overlaps'])
        range_fixes = len(issues['range_problems']) - len(issues_after['range_problems'])
        
        print("\n📊 IMPROVEMENTS:")
        print(f"   Root notes fixed: {root_fixes}")
        print(f"   Velocity overlaps fixed: {velocity_fixes}")
        print(f"   Range issues fixed: {range_fixes}")
        
        if root_fixes > 0 or velocity_fixes > 0 or range_fixes > 0:
            print("\n🎉 SUCCESS! The XPM file should now play correctly without global transpose!")
            print(f"   Fixed file: {test_file}")
            print("   Load this file in your MPC Live 2 to test the improvements")
        else:
            print("\n⚠️  No improvements detected - may need manual adjustment")
    else:
        print("❌ Failed to apply fixes")
    
    # Clean up
    print(f"\n🧹 Test complete. Test file: {test_file}")

if __name__ == "__main__":
    test_vocal_string_correction()
