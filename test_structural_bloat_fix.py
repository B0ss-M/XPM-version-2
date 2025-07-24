#!/usr/bin/env python3
"""
Test script to verify structural bloat fix works correctly
"""

import xml.etree.ElementTree as ET
import os
import sys
import shutil

# Add the current directory to Python path
sys.path.append('/Users/marlsz/Documents/GitHub/XPM-version-2')

import importlib.util
spec = importlib.util.spec_from_file_location("gemini_script", "/Users/marlsz/Documents/GitHub/XPM-version-2/Gemini wav_TO_XpmV2.py")
gemini_script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gemini_script)
ExpansionDoctorWindow = gemini_script.ExpansionDoctorWindow
import tkinter as tk

def analyze_file(file_path, description):
    """Analyze an XMP file and report its structure"""
    print(f"\n=== {description} ===")
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Check file version
        version = root.find('.//File_Version')
        app_version = root.find('.//Application_Version')
        print(f"File Version: {version.text if version is not None else 'Not found'}")
        print(f"Application Version: {app_version.text if app_version is not None else 'Not found'}")
        
        # Check instruments
        instruments = root.findall('.//Instrument')
        print(f"Total instruments: {len(instruments)}")
        
        # Check which instruments have samples
        instruments_with_samples = 0
        for i, inst in enumerate(instruments):
            layers = inst.find("Layers")
            has_samples = False
            
            if layers is not None:
                for layer in layers.findall("Layer"):
                    sample_name_elem = layer.find("SampleName")
                    sample_file_elem = layer.find("SampleFile")
                    
                    if ((sample_name_elem is not None and sample_name_elem.text and sample_name_elem.text.strip()) or
                        (sample_file_elem is not None and sample_file_elem.text and sample_file_elem.text.strip())):
                        has_samples = True
                        break
            
            if has_samples:
                instruments_with_samples += 1
        
        print(f"Instruments with samples: {instruments_with_samples}")
        print(f"Empty instruments: {len(instruments) - instruments_with_samples}")
        
        # Check KeygroupNumKeygroups
        kg_count = root.find('.//KeygroupNumKeygroups')
        if kg_count is not None:
            print(f"KeygroupNumKeygroups: {kg_count.text}")
        
        return {
            'total_instruments': len(instruments),
            'instruments_with_samples': instruments_with_samples,
            'empty_instruments': len(instruments) - instruments_with_samples,
            'keygroup_count': kg_count.text if kg_count is not None else 'Not found'
        }
        
    except Exception as e:
        print(f"Error: {e}")
        return None

def test_structural_bloat_fix():
    """Test the structural bloat fix"""
    
    # Source and test files
    source_file = "/Volumes/MPC LIVE 2/Test/B097 Chamber Str/B097 Chamber Str.xpm.backup"
    test_file = "/tmp/test_structure_fix.xpm"
    
    # Copy the original file for testing
    shutil.copy2(source_file, test_file)
    
    # Analyze before fix
    before = analyze_file(test_file, "BEFORE STRUCTURAL BLOAT FIX")
    
    # Create a minimal tkinter app for testing
    root = tk.Tk()
    root.withdraw()  # Hide the window
    
    # Create ExpansionDoctorWindow instance for testing
    doctor = ExpansionDoctorWindow(root)
    
    # Apply the structural bloat fix
    print("\n=== APPLYING STRUCTURAL BLOAT FIX ===")
    result = doctor.fix_structural_bloat(test_file)
    print(f"Fix result: {result}")
    
    # Analyze after fix
    after = analyze_file(test_file, "AFTER STRUCTURAL BLOAT FIX")
    
    # Compare results
    print(f"\n=== COMPARISON ===")
    if before and after:
        print(f"Total instruments: {before['total_instruments']} → {after['total_instruments']}")
        print(f"Instruments with samples: {before['instruments_with_samples']} → {after['instruments_with_samples']}")
        print(f"Empty instruments: {before['empty_instruments']} → {after['empty_instruments']}")
        print(f"KeygroupNumKeygroups: {before['keygroup_count']} → {after['keygroup_count']}")
        
        # Check if fix preserved sample instruments
        if before['instruments_with_samples'] == after['instruments_with_samples']:
            print("✅ SUCCESS: All instruments with samples preserved")
        else:
            print("❌ FAILURE: Sample instruments were lost!")
            
        # Check if empty instruments were removed
        if after['empty_instruments'] == 0:
            print("✅ SUCCESS: All empty instruments removed")
        else:
            print(f"⚠️  WARNING: {after['empty_instruments']} empty instruments remain")
    
    # Clean up
    if os.path.exists(test_file):
        os.remove(test_file)
    
    root.destroy()

if __name__ == "__main__":
    test_structural_bloat_fix()
