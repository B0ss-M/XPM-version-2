#!/usr/bin/env python3
"""
EMERGENCY FIX: Correct the ProgramPads JSON padToInstrument mapping in B120 Henry IX

PROBLEM: The ProgramPads JSON has padToInstrument mapping of {"0": 0} which forces
         all 21 samples into instrument 0, instead of proper 1-to-1 mapping.

SOLUTION: Update the padToInstrument mapping to {"0": 0, "1": 1, ..., "20": 20}
          to restore the original multi-keygroup structure.
"""

import xml.etree.ElementTree as ET
import json
from xml.sax.saxutils import unescape, escape
import shutil
import os

def fix_henry_ix_programpads():
    """Fix the ProgramPads JSON to restore proper multi-keygroup mapping"""
    
    file_path = '/Volumes/MPC LIVE 2/Test/B120 Henry IX/B120 Henry IX.xpm'
    backup_path = file_path + '.programpads_fix.backup'
    
    # Create backup
    shutil.copy2(file_path, backup_path)
    print(f"✅ Created backup: {backup_path}")
    
    # Load and parse
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    # Find ProgramPads element
    pads_elem = root.find('.//ProgramPads-v2.10')
    if pads_elem is None:
        print("❌ No ProgramPads-v2.10 element found")
        return False
    
    if not pads_elem.text:
        print("❌ ProgramPads element has no text content")
        return False
    
    # Parse JSON
    try:
        json_text = unescape(pads_elem.text)
        pads_data = json.loads(json_text)
        print(f"✅ Parsed ProgramPads JSON")
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse JSON: {e}")
        return False
    
    # Check current padToInstrument mapping
    if 'padToInstrument' not in pads_data:
        print("❌ No padToInstrument mapping found")
        return False
    
    current_mapping = pads_data['padToInstrument']
    print(f"🔍 Current padToInstrument: {current_mapping}")
    
    # Count actual instruments in XML
    instruments = root.findall('.//Instrument')
    print(f"🔍 Found {len(instruments)} instruments in XML")
    
    # Count instruments with samples
    instruments_with_samples = 0
    for instrument in instruments:
        has_samples = False
        layers = instrument.find('Layers')
        if layers is not None:
            for layer in layers.findall('Layer'):
                sample_name_elem = layer.find('SampleName')
                if sample_name_elem is not None and sample_name_elem.text and sample_name_elem.text.strip():
                    has_samples = True
                    break
        if has_samples:
            instruments_with_samples += 1
    
    print(f"🔍 Found {instruments_with_samples} instruments with samples")
    
    # Create correct padToInstrument mapping
    correct_mapping = {str(i): i for i in range(instruments_with_samples)}
    print(f"🔧 Creating correct mapping: {correct_mapping}")
    
    # Update the mapping
    pads_data['padToInstrument'] = correct_mapping
    
    # Convert back to JSON and escape for XML
    updated_json = json.dumps(pads_data, separators=(',', ':'))
    pads_elem.text = escape(updated_json)
    
    # Save the fixed file
    tree.write(file_path, encoding='utf-8', xml_declaration=True)
    print(f"✅ Fixed ProgramPads mapping and saved file")
    
    # Verify the fix
    print(f"\n=== VERIFICATION ===")
    tree_verify = ET.parse(file_path)
    root_verify = tree_verify.getroot()
    pads_elem_verify = root_verify.find('.//ProgramPads-v2.10')
    
    if pads_elem_verify and pads_elem_verify.text:
        json_text_verify = unescape(pads_elem_verify.text)
        pads_data_verify = json.loads(json_text_verify)
        final_mapping = pads_data_verify.get('padToInstrument', {})
        print(f"✅ Final padToInstrument: {final_mapping}")
        print(f"✅ Mapping entries: {len(final_mapping)}")
        return True
    else:
        print("❌ Verification failed")
        return False

if __name__ == "__main__":
    print("🚨 EMERGENCY FIX: B120 Henry IX ProgramPads JSON")
    print("="*50)
    
    success = fix_henry_ix_programpads()
    
    if success:
        print("\n🎉 SUCCESS! Multi-keygroup mapping has been restored!")
        print("💡 The file should now load all 21 instruments correctly.")
        print("🔄 Please test the file on your MPC to confirm the fix.")
    else:
        print("\n❌ FAILED! The fix could not be applied.")
        print("🔄 The backup file has been preserved for manual investigation.")
