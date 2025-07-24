#!/usr/bin/env python3
"""
MPC XPM File Analysis Tool
Analyzes MPC XPM files created by Expansion Doctor to identify playback issues
"""

import xml.etree.ElementTree as ET
import json
import html
import re
import os
from pathlib import Path

def analyze_xmp_file(file_path):
    """Analyze an XPM file for structural issues that could cause playback problems"""
    print(f"\n🔍 ANALYZING: {Path(file_path).name}")
    print("=" * 60)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse XML
        try:
            root = ET.fromstring(content)
        except ET.ParseError as e:
            print(f"❌ XML PARSE ERROR: {e}")
            return
        
        # Basic file info
        version = root.find('.//Version')
        if version is not None:
            app_version = version.find('Application_Version')
            platform = version.find('Platform')
            print(f"📋 Application: {app_version.text if app_version is not None else 'Unknown'}")
            print(f"📋 Platform: {platform.text if platform is not None else 'Unknown'}")
        
        program = root.find('.//Program')
        if program is None:
            print("❌ NO PROGRAM ELEMENT FOUND")
            return
            
        program_name = program.find('ProgramName')
        print(f"📋 Program: {program_name.text if program_name is not None else 'Unknown'}")
        
        # Check ProgramPads JSON structure
        program_pads = program.find('ProgramPads-v2.10')
        if program_pads is not None:
            json_content = html.unescape(program_pads.text)
            try:
                pads_data = json.loads(json_content)
                print(f"✅ ProgramPads JSON: Valid")
                
                # Analyze pad assignments
                if 'ProgramPads-v2.10' in pads_data:
                    pads = pads_data['ProgramPads-v2.10'].get('pads', {})
                    assigned_pads = {k: v for k, v in pads.items() if v != 0}
                    print(f"📊 Assigned Pads: {len(assigned_pads)}")
                    
                    if assigned_pads:
                        print(f"📊 Pad Range: {min(assigned_pads.keys())} to {max(assigned_pads.keys())}")
                    
            except json.JSONDecodeError as e:
                print(f"❌ ProgramPads JSON ERROR: {e}")
        else:
            print("❌ NO PROGRAMPADS FOUND")
        
        # Check keygroup count declaration
        keygroup_num = program.find('KeygroupNumKeygroups')
        declared_keygroups = int(keygroup_num.text) if keygroup_num is not None else 0
        print(f"📊 Declared Keygroups: {declared_keygroups}")
        
        # Check Legacy vs Advanced mode
        legacy_mode = program.find('KeygroupLegacyMode')
        is_legacy = legacy_mode.text == 'True' if legacy_mode is not None else False
        print(f"📊 Legacy Mode: {is_legacy}")
        
        # Count actual instruments
        instruments = program.find('Instruments')
        actual_instruments = 0
        empty_instruments = 0
        
        if instruments is not None:
            for instrument in instruments.findall('Instrument'):
                # Check if instrument has content
                layers = instrument.find('Layers')
                low_note = instrument.find('LowNote')
                high_note = instrument.find('HighNote')
                
                if layers is not None and len(list(layers)) > 0:
                    actual_instruments += 1
                elif low_note is not None and high_note is not None:
                    actual_instruments += 1
                else:
                    # Check if instrument has any non-default content
                    if len(list(instrument)) > 10:  # Has more than basic elements
                        actual_instruments += 1
                    else:
                        empty_instruments += 1
        
        total_instrument_elements = len(instruments.findall('Instrument')) if instruments is not None else 0
        print(f"📊 Total Instrument Elements: {total_instrument_elements}")
        print(f"📊 Instruments with Content: {actual_instruments}")
        print(f"📊 Empty Instruments: {empty_instruments}")
        
        # Identify potential issues
        issues = []
        
        if declared_keygroups != actual_instruments:
            issues.append(f"Keygroup count mismatch: {declared_keygroups} declared vs {actual_instruments} actual")
        
        if declared_keygroups == 128 and actual_instruments < 20:
            issues.append("Suspicious: 128 keygroups declared but very few instruments with content")
        
        if total_instrument_elements == 128 and actual_instruments < 20:
            issues.append("Bloated structure: 128 instrument elements created but most are empty")
        
        # Check for range coverage issues
        if instruments is not None:
            note_ranges = []
            for instrument in instruments.findall('Instrument'):
                low_note = instrument.find('LowNote')
                high_note = instrument.find('HighNote')
                if low_note is not None and high_note is not None:
                    try:
                        low = int(low_note.text)
                        high = int(high_note.text)
                        note_ranges.append((low, high))
                    except ValueError:
                        pass
            
            if note_ranges:
                min_note = min(r[0] for r in note_ranges)
                max_note = max(r[1] for r in note_ranges)
                print(f"📊 Note Range Coverage: {min_note} to {max_note}")
                
                if max_note < 84:  # C6 = 84
                    issues.append(f"Limited range: Maximum note {max_note} < C6 (84)")
        
        # Display issues
        if issues:
            print(f"\n⚠️  POTENTIAL ISSUES:")
            for i, issue in enumerate(issues, 1):
                print(f"   {i}. {issue}")
        else:
            print(f"\n✅ NO MAJOR ISSUES DETECTED")
        
        return {
            'declared_keygroups': declared_keygroups,
            'actual_instruments': actual_instruments,
            'total_elements': total_instrument_elements,
            'empty_instruments': empty_instruments,
            'is_legacy': is_legacy,
            'issues': issues
        }
        
    except Exception as e:
        print(f"❌ ANALYSIS ERROR: {e}")
        return None

def main():
    """Main analysis function"""
    print("🎹 MPC XPM FILE ANALYSIS TOOL")
    print("=" * 60)
    print("Analyzing Expansion Doctor created files vs originals...")
    
    # Test files from user's MPC
    test_files = [
        "/Volumes/MPC LIVE 2/Test/New/Ambiana.xpm.backup",
        "/Volumes/MPC LIVE 2/Test/New/B021 Vintage Strat.xpm.backup",
    ]
    
    results = {}
    
    for file_path in test_files:
        if os.path.exists(file_path):
            result = analyze_xmp_file(file_path)
            if result:
                results[file_path] = result
        else:
            print(f"❌ FILE NOT FOUND: {file_path}")
    
    # Summary analysis
    if results:
        print(f"\n🎯 SUMMARY ANALYSIS")
        print("=" * 60)
        
        for file_path, result in results.items():
            print(f"\n📁 {Path(file_path).name}:")
            print(f"   • Declared: {result['declared_keygroups']} keygroups")
            print(f"   • Actual: {result['actual_instruments']} instruments")
            print(f"   • Empty: {result['empty_instruments']} empty elements")
            print(f"   • Issues: {len(result['issues'])}")
            
        # Common patterns
        total_files = len(results)
        bloated_files = sum(1 for r in results.values() if r['total_elements'] >= 128)
        mismatch_files = sum(1 for r in results.values() if r['declared_keygroups'] != r['actual_instruments'])
        
        print(f"\n🔍 PATTERN ANALYSIS:")
        print(f"   • Files with 128+ elements: {bloated_files}/{total_files}")
        print(f"   • Files with count mismatches: {mismatch_files}/{total_files}")
        
        if bloated_files > 0:
            print(f"\n⚠️  LIKELY CAUSE: Expansion Doctor is creating 128 instrument")
            print(f"   elements regardless of actual keygroup count, causing:")
            print(f"   • Bloated file sizes")
            print(f"   • MPC parsing issues")
            print(f"   • Playback problems")
            print(f"   • Memory consumption")

if __name__ == "__main__":
    main()
