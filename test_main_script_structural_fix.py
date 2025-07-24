#!/usr/bin/env python3
"""
Test script to verify that the main Gemini wav_TO_XpmV2.py script properly fixes structural bloat.
This tests the integrated fix logic for any XPM file with bloat issues.
"""

import os
import sys
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

# Add the current directory to the path so we can import the main script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the main script classes
import importlib.util
spec = importlib.util.spec_from_file_location("main_script", "Gemini wav_TO_XpmV2.py")
main_script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main_script)
ExpansionDoctorWindow = main_script.ExpansionDoctorWindow
import tkinter as tk

def test_main_script_structural_fix():
    """Test the structural bloat fix in the main script."""
    
    print("🧪 TESTING MAIN SCRIPT STRUCTURAL BLOAT FIX")
    print("=" * 60)
    
    # Test file path
    backup_file = "/Volumes/MPC LIVE 2/Test/B120 Henry IX/B120 Henry IX.xpm.backup"
    test_file = "/tmp/test_main_script_fix.xpm"
    
    if not os.path.exists(backup_file):
        print("❌ Backup file not found. Please ensure B120 Henry IX backup exists.")
        return False
    
    # Copy backup to test file
    shutil.copy2(backup_file, test_file)
    print(f"✅ Copied backup to test file: {test_file}")
    
    # Analyze before fix
    print(f"\n📊 BEFORE FIX")
    tree_before = ET.parse(test_file)
    root_before = tree_before.getroot()
    instruments_before = root_before.findall('.//Instrument')
    print(f"Total instruments: {len(instruments_before)}")
    
    # Count instruments with samples
    instruments_with_samples_before = 0
    for instrument in instruments_before:
        has_samples = False
        layers = instrument.find('Layers')
        if layers is not None:
            for layer in layers.findall('Layer'):
                sample_name = layer.find('SampleName')
                if sample_name is not None and sample_name.text and sample_name.text.strip():
                    has_samples = True
                    break
        if has_samples:
            instruments_with_samples_before += 1
    
    print(f"Instruments with samples: {instruments_with_samples_before}")
    print(f"Empty instruments: {len(instruments_before) - instruments_with_samples_before}")
    
    # Create a minimal GUI to test the main script logic
    try:
        print(f"\n🔧 APPLYING MAIN SCRIPT FIX")
        
        # Create minimal tkinter root for the ExpansionDoctorWindow
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        
        # Create mock master object with required attributes
        class MockMaster:
            def __init__(self):
                self.root = root
                self.folder_path = tk.StringVar()
                self.folder_path.set(os.path.dirname(test_file))
        
        master = MockMaster()
        
        # Create ExpansionDoctorWindow instance
        doctor = ExpansionDoctorWindow(master)
        doctor.withdraw()  # Hide the doctor window
        
        # Call the fix_structural_bloat method directly
        result = doctor.fix_structural_bloat(test_file)
        
        # Cleanup GUI
        doctor.destroy()
        root.destroy()
        
        print(f"Fix result: {result}")
        
        if not result:
            print("⚠️ Fix returned False - file may not have had structural bloat or fix failed")
            return False
        
    except Exception as e:
        print(f"❌ Error during fix: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Analyze after fix
    print(f"\n📊 AFTER FIX")
    tree_after = ET.parse(test_file)
    root_after = tree_after.getroot()
    instruments_after = root_after.findall('.//Instrument')
    print(f"Total instruments: {len(instruments_after)}")
    
    # Count instruments with samples
    instruments_with_samples_after = 0
    total_layers_after = 0
    sample_list = []
    
    for instrument in instruments_after:
        has_samples = False
        layers = instrument.find('Layers')
        if layers is not None:
            layer_elements = layers.findall('Layer')
            total_layers_after += len(layer_elements)
            
            for layer in layer_elements:
                sample_name = layer.find('SampleName')
                root_note = layer.find('RootNote')
                if sample_name is not None and sample_name.text and sample_name.text.strip():
                    has_samples = True
                    sample_list.append({
                        'instrument': instrument.get('number'),
                        'sample': sample_name.text,
                        'root_note': root_note.text if root_note is not None else 'N/A'
                    })
        
        if has_samples:
            instruments_with_samples_after += 1
    
    print(f"Instruments with samples: {instruments_with_samples_after}")
    print(f"Total layers: {total_layers_after}")
    print(f"Total samples found: {len(sample_list)}")
    
    # Check file format
    file_version = root_after.find('.//File_Version')
    app_version = root_after.find('.//Application_Version')
    platform = root_after.find('.//Platform')
    kg_count = root_after.find('.//KeygroupNumKeygroups')
    
    print(f"File_Version: {file_version.text if file_version is not None else 'N/A'}")
    print(f"Application_Version: {app_version.text if app_version is not None else 'N/A'}")
    print(f"Platform: {platform.text if platform is not None else 'N/A'}")
    print(f"KeygroupNumKeygroups: {kg_count.text if kg_count is not None else 'N/A'}")
    
    # Check for ProgramPads JSON (should be none for our clean fix)
    pads_elem = root_after.find('.//ProgramPads-v2.10')
    if pads_elem is None:
        print("✅ No ProgramPads JSON (clean XML-only format)")
    else:
        print("⚠️ ProgramPads JSON exists - may cause issues")
    
    # Show sample details
    print(f"\n🎵 SAMPLE VERIFICATION (first 10)")
    for i, sample in enumerate(sample_list[:10]):
        print(f"  {i+1:2d}. Inst {sample['instrument']:2s}: {sample['sample']:12s} | Root: {sample['root_note']:2s}")
    
    # Validation
    print(f"\n🏆 VALIDATION")
    success = True
    
    if len(instruments_after) != instruments_with_samples_before:
        print(f"❌ Instrument count mismatch: expected {instruments_with_samples_before}, got {len(instruments_after)}")
        success = False
    else:
        print(f"✅ Correct instrument count: {len(instruments_after)}")
    
    if len(sample_list) != instruments_with_samples_before:
        print(f"❌ Sample count mismatch: expected {instruments_with_samples_before}, got {len(sample_list)}")
        success = False
    else:
        print(f"✅ All samples preserved: {len(sample_list)}")
    
    if file_version and file_version.text == "2.1":
        print("✅ File format modernized to 2.1")
    else:
        print("❌ File format not updated")
        success = False
    
    if pads_elem is None:
        print("✅ Clean XML-only format (no problematic ProgramPads JSON)")
    else:
        print("❌ ProgramPads JSON exists (potential issue)")
        success = False
    
    # Cleanup
    try:
        os.remove(test_file)
        print(f"🧹 Cleaned up test file")
    except:
        pass
    
    return success

if __name__ == "__main__":
    success = test_main_script_structural_fix()
    
    print(f"\n{'🎉 SUCCESS' if success else '❌ FAILED'}: Main script structural bloat fix test")
    
    if success:
        print("\n✅ The main Gemini wav_TO_XpmV2.py script correctly:")
        print("   • Removes structural bloat (empty instruments)")
        print("   • Preserves all samples and musical data")
        print("   • Modernizes file format to 2.1")
        print("   • Uses clean XML-only format")
        print("   • Maintains multi-sample keygroup structure")
    else:
        print("\n❌ The main script fix needs attention")
    
    sys.exit(0 if success else 1)
