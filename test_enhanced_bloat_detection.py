#!/usr/bin/env python3
"""
Test the enhanced bloat detection with VOCAL STRING.xpm
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

def test_vocal_string_detection():
    """Test enhanced bloat detection with VOCAL STRING.xpm"""
    print("🔍 Testing enhanced bloat detection with VOCAL STRING.xpm...")
    
    test_file = '/Volumes/MPC LIVE 2/Test/VOCAL STRING.xpm'
    if not os.path.exists(test_file):
        print("⚠️ VOCAL STRING.xpm not found - creating synthetic test")
        test_file = create_synthetic_vocal_string()
    
    # Create a mock tkinter root and master
    root = tk.Tk()
    root.withdraw()
    
    class MockMaster:
        def __init__(self):
            self.root = root
            self.firmware_version = tk.StringVar(value="3.5.0")
            self.folder_path = tk.StringVar(value="")
    
    try:
        # Create ExpansionDoctorWindow instance
        mock_master = MockMaster()
        doctor = main_script.ExpansionDoctorWindow(mock_master)
        
        # Analyze the file
        print(f"   Analyzing: {os.path.basename(test_file)}")
        result = doctor.analyze_xpm_issues(test_file)
        
        print(f"   Analysis results:")
        print(f"     Total instruments: {result.get('keygroup_count', 0)}")
        print(f"     Declared count: {result.get('declared_count', 0)}")
        print(f"     Issues found: {len(result.get('issues', []))}")
        print(f"     Fixes suggested: {len(result.get('fixes', []))}")
        
        if result.get('issues'):
            print(f"     Issues detected:")
            for i, issue in enumerate(result['issues'], 1):
                print(f"       {i}. {issue}")
        else:
            print(f"     ❌ NO ISSUES DETECTED - This is wrong!")
            
        if result.get('fixes'):
            print(f"     Recommended fixes:")
            for fix in result['fixes']:
                print(f"       • {fix}")
        
        # Check if bloat detection is working
        bloat_detected = any("BLOAT" in issue for issue in result.get('issues', []))
        if bloat_detected:
            print("   ✅ BLOAT DETECTION WORKING!")
        else:
            print("   ❌ BLOAT DETECTION FAILED!")
            
        return bloat_detected
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        root.destroy()

def create_synthetic_vocal_string():
    """Create a synthetic XPM file similar to VOCAL STRING.xpm for testing"""
    test_file = '/tmp/synthetic_vocal_string.xpm'
    
    xml_content = '''<?xml version='1.0' encoding='utf-8'?>
<MPCVObject>
  <Version>
  </Version>
  <Program type="Keygroup">
  </Program>
  <File_Version>2.1</File_Version>
  <KeygroupNumKeygroups>11</KeygroupNumKeygroups>
  <Instruments>
    <Instrument number="0">
      <LowNote>60</LowNote>
      <HighNote>60</HighNote>
      <Layers>
        <Layer>
          <SampleName>VOCAL_STRING_C4</SampleName>
          <SampleFile>VOCAL_STRING_C4.wav</SampleFile>
        </Layer>
      </Layers>
    </Instrument>
    <Instrument number="1">
      <LowNote>61</LowNote>
      <HighNote>61</HighNote>
      <Layers>
        <Layer>
          <SampleName>VOCAL_STRING_C#4</SampleName>
          <SampleFile>VOCAL_STRING_C#4.wav</SampleFile>
        </Layer>
      </Layers>
    </Instrument>
    <Instrument number="2">
      <LowNote>0</LowNote>
      <HighNote>0</HighNote>
      <Layers>
        <Layer>
          <SampleName>Unknown</SampleName>
          <SampleFile></SampleFile>
        </Layer>
      </Layers>
    </Instrument>
    <Instrument number="3">
      <LowNote>0</LowNote>
      <HighNote>0</HighNote>
      <Layers>
        <Layer>
          <SampleName>Unknown</SampleName>
          <SampleFile></SampleFile>
        </Layer>
      </Layers>
    </Instrument>
    <Instrument number="4">
      <LowNote>0</LowNote>
      <HighNote>0</HighNote>
      <Layers>
        <Layer>
          <SampleName>Unknown</SampleName>
          <SampleFile></SampleFile>
        </Layer>
      </Layers>
    </Instrument>
    <Instrument number="5">
      <LowNote>0</LowNote>
      <HighNote>0</HighNote>
      <Layers>
        <Layer>
          <SampleName>Unknown</SampleName>
          <SampleFile></SampleFile>
        </Layer>
      </Layers>
    </Instrument>
    <Instrument number="6">
      <LowNote>0</LowNote>
      <HighNote>0</HighNote>
      <Layers>
        <Layer>
          <SampleName>Unknown</SampleName>
          <SampleFile></SampleFile>
        </Layer>
      </Layers>
    </Instrument>
    <Instrument number="7">
      <LowNote>0</LowNote>
      <HighNote>0</HighNote>
      <Layers>
        <Layer>
          <SampleName>Unknown</SampleName>
          <SampleFile></SampleFile>
        </Layer>
      </Layers>
    </Instrument>
    <Instrument number="8">
      <LowNote>0</LowNote>
      <HighNote>0</HighNote>
      <Layers>
        <Layer>
          <SampleName>Unknown</SampleName>
          <SampleFile></SampleFile>
        </Layer>
      </Layers>
    </Instrument>
    <Instrument number="9">
      <LowNote>0</LowNote>
      <HighNote>0</HighNote>
      <Layers>
        <Layer>
          <SampleName>Unknown</SampleName>
          <SampleFile></SampleFile>
        </Layer>
      </Layers>
    </Instrument>
    <Instrument number="10">
      <LowNote>0</LowNote>
      <HighNote>0</HighNote>
      <Layers>
        <Layer>
          <SampleName>Unknown</SampleName>
          <SampleFile></SampleFile>
        </Layer>
      </Layers>
    </Instrument>
  </Instruments>
</MPCVObject>'''
    
    with open(test_file, 'w') as f:
        f.write(xml_content)
    
    print(f"   Created synthetic test file: {test_file}")
    return test_file

def main():
    print("🚀 Testing enhanced Expansion Doctor bloat detection\n")
    os.chdir('/Users/marlsz/Documents/GitHub/XPM-version-2')
    
    if test_vocal_string_detection():
        print("\n✅ ENHANCED BLOAT DETECTION IS WORKING!")
        print("   The Expansion Doctor can now detect smaller-scale bloat patterns")
        print("   including files like VOCAL STRING.xpm with mixed empty/valid instruments")
    else:
        print("\n❌ BLOAT DETECTION STILL HAS ISSUES")

if __name__ == "__main__":
    main()
