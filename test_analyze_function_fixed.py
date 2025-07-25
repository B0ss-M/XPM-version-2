#!/usr/bin/env python3
"""
Direct test of the analyze_xpm_issues functionality
"""

import sys
import os
import xml.etree.ElementTree as ET
import tkinter as tk

# Add current directory to path
sys.path.append('/Users/marlsz/Documents/GitHub/XPM-version-2')

# Import the main script using importlib to avoid module naming issues
import importlib.util
spec = importlib.util.spec_from_file_location("main_script", "/Users/marlsz/Documents/GitHub/XPM-version-2/Gemini wav_TO_XpmV2.py")
main_script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main_script)

def test_analyze_xpm_issues():
    """Test the analyze_xpm_issues method directly"""
    print("🔍 Testing analyze_xpm_issues method...")
    
    # Create a mock tkinter root (required for ExpansionDoctorWindow)
    root = tk.Tk()
    root.withdraw()  # Hide the window
    
    # Create a mock master with required attributes
    class MockMaster:
        def __init__(self):
            self.root = root
            self.firmware_version = tk.StringVar(value="3.5.0")
            self.folder_path = tk.StringVar(value="")
    
    try:
        # Create ExpansionDoctorWindow instance with proper mock master
        mock_master = MockMaster()
        doctor = main_script.ExpansionDoctorWindow(mock_master)
        
        # Test with the VOCAL STRING file
        test_file = '/Volumes/MPC LIVE 2/Test/VOCAL STRING.xpm'
        if os.path.exists(test_file):
            print(f"   Testing with: {test_file}")
            result = doctor.analyze_xpm_issues(test_file)
            
            print(f"   Analysis result keys: {list(result.keys())}")
            print(f"   Issues found: {len(result.get('issues', []))}")
            print(f"   Fixes suggested: {result.get('fixes', [])}")
            print(f"   Keygroup count: {result.get('keygroup_count', 'unknown')}")
            
            if result.get('issues'):
                print("   Issues detected:")
                for issue in result['issues']:
                    print(f"     - {issue}")
            else:
                print("   ✅ No issues detected")
                
        else:
            print("   ⚠️ Test file not found, creating synthetic test...")
            
            # Create a synthetic test file with bloat
            test_bloat_file = '/tmp/test_bloat.xpm'
            create_bloated_test_file(test_bloat_file)
            
            result = doctor.analyze_xpm_issues(test_bloat_file)
            print(f"   Synthetic test result: {result}")
            
            # Clean up
            if os.path.exists(test_bloat_file):
                os.remove(test_bloat_file)
        
        root.destroy()
        return True
        
    except Exception as e:
        print(f"   ❌ Error testing analyze_xpm_issues: {e}")
        import traceback
        traceback.print_exc()
        root.destroy()
        return False

def create_bloated_test_file(filename):
    """Create a synthetic XPM file with structural bloat for testing"""
    
    xml_content = '''<?xml version='1.0' encoding='utf-8'?>
<MPCVObject>
  <Version>
  </Version>
  <Program type="Keygroup">
  </Program>
  <File_Version>2.1</File_Version>
  <KeygroupNumKeygroups>10</KeygroupNumKeygroups>
  <Instruments>'''
    
    # Add 100 empty instruments to simulate bloat
    for i in range(100):
        xml_content += f'    <Instrument number="{i}"></Instrument>\n'
    
    xml_content += '''  </Instruments>
</MPCVObject>'''
    
    with open(filename, 'w') as f:
        f.write(xml_content)

def main():
    print("🚀 Direct test of analyze_xpm_issues functionality\n")
    os.chdir('/Users/marlsz/Documents/GitHub/XPM-version-2')
    
    if test_analyze_xpm_issues():
        print("\n✅ analyze_xpm_issues method works correctly!")
    else:
        print("\n❌ Issues found with analyze_xpm_issues method")

if __name__ == "__main__":
    main()
