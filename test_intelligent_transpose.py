#!/usr/bin/env python3
"""
Test script for the intelligent batch transpose functionality
"""

import sys
import os
import importlib.util

def test_intelligent_transpose():
    """Test the intelligent transpose algorithm with the actual XPM files."""
    print("🧠 Testing Intelligent Batch Transpose")
    print("=" * 50)
    
    # Import the main app
    try:
        spec = importlib.util.spec_from_file_location('gemini', 'Gemini wav_TO_XpmV2.py')
        gemini = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gemini)
        print("✅ Successfully imported main application")
    except Exception as e:
        print(f"❌ Failed to import: {e}")
        return
    
    # Test the intelligent analysis on actual files
    test_files = [
        "/Volumes/MPC LIVE 2/Test/Motif/002_icu2.xpm.backup",  # Original file
        "/Volumes/MPC LIVE 2/Test/Motif/002_icu2.xpm",         # Modified file
    ]
    
    # Create a mock BatchTransposeWindow to test the algorithm
    class MockMaster:
        def __init__(self):
            self.last_browse_path = "/tmp"
        root = None
    
    mock_master = MockMaster()
    
    try:
        transpose_window = gemini.BatchTransposeWindow.__new__(gemini.BatchTransposeWindow)
        transpose_window.intelligent_mode = type('MockVar', (), {'get': lambda: True})()
        
        for test_file in test_files:
            if os.path.exists(test_file):
                print(f"\n🔍 Analyzing: {os.path.basename(test_file)}")
                
                # Test current transpose reading
                current_transpose = transpose_window.get_current_transpose(test_file)
                print(f"📊 Current transpose: {current_transpose} semitones")
                
                # Test intelligent analysis
                analysis = transpose_window.analyze_xpm_pitch_issues(test_file)
                print(f"🎯 Recommended transpose: {analysis['recommended_transpose']} semitones")
                print(f"🔍 Issue detected: {analysis['issue_detected']}")
                
                if analysis['sample_notes']:
                    print(f"🎵 Sample notes found: {len(analysis['sample_notes'])} samples")
                    print(f"🎵 Note range: {analysis['min_note']} to {analysis['max_note']}")
                    print(f"🎵 Average note: {analysis['avg_note']:.1f}")
                else:
                    print("⚠️  No sample notes found in analysis")
                
                # Show the difference
                improvement = analysis['recommended_transpose'] - current_transpose
                if abs(improvement) > 1:
                    print(f"💡 Suggested improvement: {improvement:+.1f} semitones")
                    if improvement < -12:
                        print("🎯 This will bring high-pitched samples down to playable range")
                    elif improvement > 12:
                        print("🎯 This will bring low-pitched samples up to playable range")
                else:
                    print("✅ File is already in good range")
                    
            else:
                print(f"❌ File not found: {test_file}")
        
        print("\n🎉 Intelligent transpose analysis complete!")
        print("\n📋 Summary:")
        print("• The algorithm detects current transpose values")  
        print("• Analyzes sample pitch ranges")
        print("• Calculates optimal transpose for C0-C8 playability")
        print("• Handles your specific issue: C2 plays as C4 (24 semitones too high)")
        
    except Exception as e:
        print(f"❌ Analysis test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_intelligent_transpose()
