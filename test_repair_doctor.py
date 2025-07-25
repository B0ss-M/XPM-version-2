#!/usr/bin/env python3
"""
Test script for XPM Repair Doctor
Tests the repair functionality on existing XPM files in the workspace.
"""

import os
import sys
import logging
from pathlib import Path

# Add current directory to path to import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from xpm_repair_doctor import XPMRepairDoctor
    print("✅ Successfully imported XPMRepairDoctor")
except ImportError as e:
    print(f"❌ Failed to import XPMRepairDoctor: {e}")
    sys.exit(1)

def test_repair_doctor():
    """Test the XPM Repair Doctor on workspace files."""
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Find XPM files in current directory
    workspace_dir = Path(__file__).parent
    xpm_files = list(workspace_dir.glob("*.xpm"))
    
    if not xpm_files:
        print("No XPM files found in workspace for testing")
        return
    
    print(f"Found {len(xpm_files)} XPM files to test:")
    for xpm_file in xpm_files[:5]:  # Test first 5 files
        print(f"  - {xpm_file.name}")
    
    # Initialize repair doctor
    doctor = XPMRepairDoctor()
    
    # Test analysis on a few files
    for i, xpm_file in enumerate(xpm_files[:3]):  # Test first 3 files
        print(f"\n=== Testing file {i+1}: {xpm_file.name} ===")
        
        try:
            # Analyze the file
            analysis = doctor.analyze_xpm_structure(str(xpm_file))
            
            print(f"File: {analysis.file_name}")
            print(f"Needs repair: {analysis.needs_repair}")
            print(f"Is repairable: {analysis.is_repairable}")
            print(f"Confidence: {analysis.confidence_score:.1f}%")
            print(f"Issues found: {len(analysis.issues)}")
            
            # Show issues
            for issue in analysis.issues:
                print(f"  - {issue.severity.upper()}: {issue.description}")
            
            # Show metadata
            print(f"Metadata:")
            for key, value in analysis.metadata.items():
                print(f"  {key}: {value}")
            
            # Test repair if needed (but don't actually repair)
            if analysis.needs_repair and analysis.is_repairable:
                print("✅ File would be candidates for repair")
            elif analysis.needs_repair:
                print("⚠️  File needs repair but may not be repairable")
            else:
                print("✅ File appears to be in good condition")
                
        except Exception as e:
            print(f"❌ Error analyzing {xpm_file.name}: {e}")
    
    print("\n=== Repair Doctor Test Complete ===")

if __name__ == "__main__":
    test_repair_doctor()
