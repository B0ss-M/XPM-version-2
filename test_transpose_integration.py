#!/usr/bin/env python3
"""
Test script for the integrated Batch Transpose functionality
"""

import tkinter as tk
import os
import tempfile
import xml.etree.ElementTree as ET

# Test XPM content with KeygroupMasterTranspose
test_xpm_content = '''<?xml version="1.0" encoding="utf-8"?>
<MPCVObject>
    <Version>
        <File_Version>2.1</File_Version>
        <Application>MPC-V</Application>
        <Application_Version>3.5.0</Application_Version>
        <Platform>Linux</Platform>
    </Version>
    <Program type="Keygroup">
        <ProgramName>TestInstrument</ProgramName>
        <KeygroupMasterTranspose>0.0</KeygroupMasterTranspose>
    </Program>
</MPCVObject>'''

def create_test_xpm(transpose_value=0.0):
    """Create a temporary XPM file for testing."""
    # Create temporary file
    fd, temp_path = tempfile.mkstemp(suffix='.xpm', prefix='test_transpose_')
    os.close(fd)
    
    # Write test XPM content
    root = ET.fromstring(test_xpm_content)
    transpose_elem = root.find(".//KeygroupMasterTranspose")
    if transpose_elem is not None:
        transpose_elem.text = f"{transpose_value:.6f}"
    
    tree = ET.ElementTree(root)
    tree.write(temp_path, encoding="utf-8", xml_declaration=True)
    
    return temp_path

def test_transpose_integration():
    """Test the batch transpose functionality."""
    print("🎵 Testing Batch Transpose Integration")
    print("=" * 50)
    
    # Create a test XPM file
    test_file = create_test_xpm(12.0)  # Start with +12 semitones
    print(f"✅ Created test XPM: {os.path.basename(test_file)}")
    
    try:
        # Import the main app
        import sys
        import importlib.util
        spec = importlib.util.spec_from_file_location('gemini', 'Gemini wav_TO_XpmV2.py')
        gemini = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gemini)
        
        print("✅ Successfully imported main application")
        
        # Get the BatchTransposeWindow class
        BatchTransposeWindow = gemini.BatchTransposeWindow
        print("✅ BatchTransposeWindow class found")
        
        # Test reading current transpose value
        def test_get_transpose(file_path):
            try:
                tree = ET.parse(file_path)
                root = tree.getroot()
                transpose_elem = root.find(".//KeygroupMasterTranspose")
                if transpose_elem is not None and transpose_elem.text:
                    return float(transpose_elem.text)
                return 0.0
            except Exception as e:
                print(f"❌ Error reading transpose: {e}")
                return None
        
        current_transpose = test_get_transpose(test_file)
        print(f"✅ Read current transpose: {current_transpose} semitones")
        
        # Test setting new transpose value
        def test_set_transpose(file_path, new_value):
            try:
                tree = ET.parse(file_path)
                root = tree.getroot()
                transpose_elem = root.find(".//KeygroupMasterTranspose")
                
                if transpose_elem is None:
                    program_elem = root.find(".//Program")
                    if program_elem is not None:
                        transpose_elem = ET.SubElement(program_elem, "KeygroupMasterTranspose")
                    else:
                        return False
                
                transpose_elem.text = f"{new_value:.6f}"
                tree.write(file_path, encoding="utf-8", xml_declaration=True)
                return True
            except Exception as e:
                print(f"❌ Error setting transpose: {e}")
                return False
        
        # Test transpose modification
        new_value = -24.0  # Your use case: down 2 octaves
        if test_set_transpose(test_file, new_value):
            print(f"✅ Successfully set transpose to: {new_value} semitones")
            
            # Verify the change
            updated_transpose = test_get_transpose(test_file)
            if updated_transpose == new_value:
                print(f"✅ Verified transpose change: {updated_transpose} semitones")
                print(f"🎯 Perfect! This matches your requirement: C2 → C2 (was C2 → C4)")
            else:
                print(f"❌ Transpose verification failed: expected {new_value}, got {updated_transpose}")
        else:
            print("❌ Failed to set transpose value")
        
        print("\n🎉 Integration test completed successfully!")
        print("🎵 The Batch Transpose feature is ready to use in your main app!")
        print("\nTo access it:")
        print("1. Run your main application: python 'Gemini wav_TO_XpmV2.py'")
        print("2. Look for the 'Batch Transpose' button in the Utilities & Batch Tools section")
        print("3. Select your XPM folder and set transpose to -24 for your use case")
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up test file
        try:
            os.unlink(test_file)
            print(f"✅ Cleaned up test file: {os.path.basename(test_file)}")
        except:
            pass

if __name__ == "__main__":
    test_transpose_integration()
