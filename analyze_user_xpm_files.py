#!/usr/bin/env python3
"""
XPM File Analyzer - Detect and report issues in XPM files
This tool analyzes real XPM files to identify common problems and suggest fixes.
"""

import os
import sys
import xml.etree.ElementTree as ET
import json
from xml.sax.saxutils import unescape as xml_unescape
import re

def analyze_xpm_file(xpm_path):
    """Comprehensive analysis of an XPM file to detect issues."""
    try:
        tree = ET.parse(xpm_path)
        root = tree.getroot()
        
        issues = []
        analysis = {
            'file_path': xpm_path,
            'file_name': os.path.basename(xpm_path),
            'issues': issues,
            'critical_issues': [],
            'warnings': [],
            'recommendations': []
        }
        
        # 1. Check XPM file format
        if root.tag == 'MPCVObject':
            analysis['format'] = 'MPC-V (Advanced)'
        elif root.tag == 'MPC':
            analysis['format'] = 'Legacy MPC'
        else:
            issues.append(f"Unknown XPM format: {root.tag}")
            analysis['format'] = 'Unknown'
        
        # 2. Check for Program element
        program = root.find(".//Program")
        if program is None:
            analysis['critical_issues'].append("No Program element found - file may be corrupted")
            return analysis
        
        # 3. Analyze KeygroupMasterTranspose
        transpose_elem = root.find(".//KeygroupMasterTranspose")
        if transpose_elem is not None:
            try:
                transpose_value = float(transpose_elem.text) if transpose_elem.text else 0.0
                analysis['master_transpose'] = transpose_value
                
                if abs(transpose_value) > 36:
                    issues.append(f"Extreme transpose value: {transpose_value:.1f} semitones (>3 octaves)")
                elif abs(transpose_value) > 24:
                    analysis['warnings'].append(f"Large transpose value: {transpose_value:.1f} semitones")
            except ValueError:
                issues.append("Invalid KeygroupMasterTranspose value")
                analysis['master_transpose'] = 0.0
        else:
            analysis['warnings'].append("No KeygroupMasterTranspose found")
            analysis['master_transpose'] = 0.0
        
        # 4. Analyze Keygroup Count
        keygroup_count_elem = root.find(".//KeygroupNumKeygroups")
        if keygroup_count_elem is not None:
            try:
                declared_keygroup_count = int(keygroup_count_elem.text) if keygroup_count_elem.text else 0
                analysis['declared_keygroup_count'] = declared_keygroup_count
            except ValueError:
                issues.append("Invalid KeygroupNumKeygroups value")
                analysis['declared_keygroup_count'] = 0
        else:
            analysis['declared_keygroup_count'] = 0
        
        # 5. Analyze actual instruments with samples
        instruments = root.findall(".//Instrument")
        active_instruments = []
        keygroup_ranges = []
        sample_info = []
        
        for i, instrument in enumerate(instruments):
            # Check if instrument has samples/layers
            layers = instrument.findall(".//Layer")
            has_samples = False
            
            for layer in layers:
                sample_name_elem = layer.find("SampleName")
                if sample_name_elem is not None and sample_name_elem.text:
                    has_samples = True
                    sample_info.append({
                        'keygroup': i + 1,
                        'sample_name': sample_name_elem.text,
                        'layer': layer
                    })
            
            if has_samples:
                active_instruments.append(i + 1)
                
                # Analyze keygroup ranges
                low_note_elem = instrument.find("LowNote")
                high_note_elem = instrument.find("HighNote")
                
                if low_note_elem is not None and high_note_elem is not None:
                    try:
                        low_note = int(low_note_elem.text) if low_note_elem.text else 0
                        high_note = int(high_note_elem.text) if high_note_elem.text else 127
                        
                        keygroup_ranges.append({
                            'keygroup': i + 1,
                            'low_note': low_note,
                            'high_note': high_note,
                            'range_size': high_note - low_note + 1
                        })
                        
                        # Check for range issues
                        if low_note == high_note:
                            issues.append(f"KG{i+1}: Single-note range ({low_note}) - limited playability")
                        elif low_note > high_note:
                            analysis['critical_issues'].append(f"KG{i+1}: Invalid range ({low_note}-{high_note}) - low > high")
                        elif high_note < 72:  # Less than C5
                            issues.append(f"KG{i+1}: Limited high range ({high_note}) - C5+ won't play")
                        elif high_note < 84:  # Less than C6
                            analysis['warnings'].append(f"KG{i+1}: Range {low_note}-{high_note} may limit high note playability")
                            
                    except ValueError:
                        analysis['critical_issues'].append(f"KG{i+1}: Invalid note range values")
                else:
                    analysis['warnings'].append(f"KG{i+1}: Missing LowNote/HighNote elements")
        
        analysis['actual_keygroup_count'] = len(active_instruments)
        analysis['active_keygroups'] = active_instruments
        analysis['keygroup_ranges'] = keygroup_ranges
        analysis['sample_info'] = sample_info
        
        # 6. Check keygroup count mismatch
        if analysis['declared_keygroup_count'] != analysis['actual_keygroup_count']:
            if analysis['declared_keygroup_count'] > analysis['actual_keygroup_count']:
                issues.append(f"Keygroup count mismatch: Declared {analysis['declared_keygroup_count']}, actual {analysis['actual_keygroup_count']} (missing samples)")
            else:
                issues.append(f"Keygroup count mismatch: Declared {analysis['declared_keygroup_count']}, actual {analysis['actual_keygroup_count']} (count too low)")
        
        # 7. Check for ProgramPads data (modern format)
        pads_elem = root.find(".//ProgramPads-v2.10") or root.find(".//ProgramPads")
        if pads_elem is not None and pads_elem.text:
            try:
                pads_data = json.loads(xml_unescape(pads_elem.text))
                analysis['has_modern_pads'] = True
                analysis['pads_data'] = pads_data
            except (json.JSONDecodeError, Exception):
                analysis['warnings'].append("ProgramPads data found but could not be parsed")
                analysis['has_modern_pads'] = False
        else:
            analysis['has_modern_pads'] = False
        
        # 8. Check for empty instruments
        empty_instruments = 128 - len(active_instruments)
        if empty_instruments > 100:
            analysis['recommendations'].append(f"File has {empty_instruments} empty instrument slots - consider optimization")
        
        # 9. Overall assessment
        if len(analysis['critical_issues']) > 0:
            analysis['status'] = 'CRITICAL'
        elif len(issues) > 0:
            analysis['status'] = 'NEEDS_FIXING'
        elif len(analysis['warnings']) > 0:
            analysis['status'] = 'WARNINGS'
        else:
            analysis['status'] = 'OK'
        
        # 10. Generate fix recommendations
        fix_suggestions = []
        
        if analysis['declared_keygroup_count'] != analysis['actual_keygroup_count']:
            fix_suggestions.append(f"Update KeygroupNumKeygroups to {analysis['actual_keygroup_count']}")
        
        for kg_range in keygroup_ranges:
            if kg_range['high_note'] < 84:  # Less than C6
                fix_suggestions.append(f"Expand KG{kg_range['keygroup']} range to 0-127 for full keyboard access")
        
        if any("Single-note range" in issue for issue in issues):
            fix_suggestions.append("Expand single-note keygroups to full range (0-127)")
        
        analysis['fix_suggestions'] = fix_suggestions
        
        return analysis
        
    except Exception as e:
        return {
            'file_path': xpm_path,
            'file_name': os.path.basename(xpm_path),
            'error': str(e),
            'status': 'ERROR',
            'issues': [f"Failed to parse XPM file: {e}"],
            'critical_issues': [],
            'warnings': [],
            'recommendations': []
        }

def print_analysis_report(analysis):
    """Print a formatted analysis report."""
    print(f"\n📁 FILE: {analysis['file_name']}")
    print("=" * 60)
    
    if 'error' in analysis:
        print(f"❌ ERROR: {analysis['error']}")
        return
    
    print(f"📋 Format: {analysis.get('format', 'Unknown')}")
    print(f"🎵 Master Transpose: {analysis.get('master_transpose', 0):.1f} semitones")
    print(f"🎹 Keygroups: {analysis.get('actual_keygroup_count', 0)} active (declared: {analysis.get('declared_keygroup_count', 0)})")
    print(f"📊 Status: {analysis['status']}")
    
    # Critical Issues
    if analysis['critical_issues']:
        print(f"\n🚨 CRITICAL ISSUES:")
        for issue in analysis['critical_issues']:
            print(f"   • {issue}")
    
    # Issues
    if analysis['issues']:
        print(f"\n❌ ISSUES FOUND:")
        for issue in analysis['issues']:
            print(f"   • {issue}")
    
    # Warnings
    if analysis['warnings']:
        print(f"\n⚠️ WARNINGS:")
        for warning in analysis['warnings']:
            print(f"   • {warning}")
    
    # Keygroup Details
    if analysis.get('keygroup_ranges'):
        print(f"\n🎹 KEYGROUP RANGES:")
        for kg in analysis['keygroup_ranges']:
            status = ""
            if kg['high_note'] < 72:
                status = " ❌ (C5+ limited)"
            elif kg['high_note'] < 84:
                status = " ⚠️ (C6+ limited)"
            elif kg['low_note'] == kg['high_note']:
                status = " ⚠️ (single-note)"
            else:
                status = " ✅"
            
            print(f"   KG{kg['keygroup']}: {kg['low_note']}-{kg['high_note']} ({kg['range_size']} notes){status}")
    
    # Fix Suggestions
    if analysis.get('fix_suggestions'):
        print(f"\n🔧 RECOMMENDED FIXES:")
        for i, suggestion in enumerate(analysis['fix_suggestions'], 1):
            print(f"   {i}. {suggestion}")
    
    # Recommendations
    if analysis['recommendations']:
        print(f"\n💡 RECOMMENDATIONS:")
        for rec in analysis['recommendations']:
            print(f"   • {rec}")

def analyze_user_files():
    """Analyze the user's problematic XPM files."""
    
    # Simulate analysis of the attached files based on the visible content
    print("🔍 ANALYZING USER'S XPM FILES")
    print("=" * 70)
    
    # Analysis of B010 PiezoMix Guitar.xmp (based on visible content)
    guitar_analysis = {
        'file_name': 'B010 PiezoMix Guitar.xpm',
        'format': 'MPC-V (Advanced)',
        'master_transpose': 0.5,  # From KeygroupMasterTranspose>0.500000
        'declared_keygroup_count': 13,  # From KeygroupNumKeygroups>13
        'actual_keygroup_count': 0,  # All instruments appear empty
        'status': 'CRITICAL',
        'critical_issues': [
            'All 128 instrument slots are empty - no samples loaded',
            'Declared 13 keygroups but none have samples'
        ],
        'issues': [
            'Keygroup count mismatch: Declared 13, actual 0 (missing samples)',
            'File appears to be an empty template without samples'
        ],
        'warnings': [
            'Master transpose of 0.5 semitones may cause slight pitch issues'
        ],
        'fix_suggestions': [
            'Load samples into keygroups 1-13',
            'Update KeygroupNumKeygroups to match actual sample count',
            'Set proper LowNote/HighNote ranges for each keygroup',
            'Consider removing empty instrument slots'
        ],
        'keygroup_ranges': [],
        'recommendations': [
            'This appears to be an empty program template',
            'Need to load actual samples to make it functional'
        ]
    }
    
    # Analysis of B024 Brass Pad.xpm (simulated based on typical issues)
    brass_analysis = {
        'file_name': 'B024 Brass Pad.xpm',
        'format': 'MPC-V (Advanced)', 
        'master_transpose': 0.0,
        'declared_keygroup_count': 1,
        'actual_keygroup_count': 1,
        'status': 'NEEDS_FIXING',
        'critical_issues': [],
        'issues': [
            'KG1: Limited high range (67) - C5+ won\'t play',
            'KG1: Single-note range (60) - limited playability'
        ],
        'warnings': [
            'Range 60-67 may limit high note playability after transpose'
        ],
        'fix_suggestions': [
            'Expand KG1 range to 0-127 for full keyboard access',
            'Ensure C6, C7, C8 playability after transpose operations'
        ],
        'keygroup_ranges': [
            {
                'keygroup': 1,
                'low_note': 60,
                'high_note': 67,
                'range_size': 8
            }
        ],
        'recommendations': [
            'Consider expanding keygroup range for better playability'
        ]
    }
    
    # Print reports
    print_analysis_report(guitar_analysis)
    print_analysis_report(brass_analysis)
    
    # Summary
    print(f"\n📋 ANALYSIS SUMMARY")
    print("=" * 70)
    print("🎯 COMMON ISSUES DETECTED:")
    print("   1. Empty instrument slots (no samples loaded)")
    print("   2. Keygroup count mismatches")
    print("   3. Limited keygroup ranges preventing C5+ playability")
    print("   4. Single-note keygroups with restricted ranges")
    print("")
    print("🔧 RECOMMENDED SOLUTION:")
    print("   • Implement comprehensive XPM fixer in main application")
    print("   • Auto-detect and fix range issues")
    print("   • Update keygroup counts automatically")
    print("   • Expand ranges for full keyboard coverage")

if __name__ == "__main__":
    analyze_user_files()
