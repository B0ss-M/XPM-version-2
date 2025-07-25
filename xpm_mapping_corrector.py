#!/usr/bin/env python3
# Professional XPM Standards (based on ConvertWithMoss analysis):
# 1. Root notes should have +1 offset (MPC hardware convention)
# 2. Use File_Version 2.1 and Application_Version v2.11.6.6
# 3. Group samples by key ranges instead of single notes
# 4. Maximum 4 layers per keygroup (MPC hardware limit)
# 5. Use consecutive key ranges for better playability

"""
Enhanced XPM Mapping Corrector - Fixes root note, velocity, and range issues
"""

import xml.etree.ElementTree as ET
import os
import re
import sys
import logging
from typing import Dict, List, Tuple, Optional

# Add current directory to path for imports
sys.path.append('/Users/marlsz/Documents/GitHub/XPM-version-2')

class XPMappingCorrector:
    """Enhanced XPM mapping correction with manual and automatic modes"""
    
    def __init__(self):
        self.note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        self.sample_patterns = {
            # Common naming patterns for automatic detection
            r'.*[_\-\s]([A-G][#b]?\d+).*': 'note_octave',  # C4, F#3, etc.
            r'.*[_\-\s](\d+).*': 'midi_number',            # 60, 64, etc.
            r'.*[_\-\s]([A-G][#b]?).*': 'note_only',       # C, F#, etc. (assume octave 4)
        }
    
    def analyze_mapping_issues(self, xpm_path: str) -> Dict:
        """Analyze XPM file for mapping issues"""
        issues = {
            'incorrect_root_notes': [],
            'velocity_overlaps': [],
            'range_problems': [],
            'missing_samples': [],
            'recommendations': []
        }
        
        try:
            tree = ET.parse(xpm_path)
            root = tree.getroot()
            instruments = root.findall('.//Instrument')
            
            for i, instrument in enumerate(instruments):
                # Check root note issues
                layers = instrument.find('Layers')
                if layers is not None:
                    for j, layer in enumerate(layers.findall('Layer')):
                        root_note_elem = layer.find('RootNote')
                        sample_name_elem = layer.find('SampleName')
                        velocity_low_elem = layer.find('VelocityLow')
                        velocity_high_elem = layer.find('VelocityHigh')
                        
                        if root_note_elem is not None and sample_name_elem is not None:
                            current_root = int(root_note_elem.text) if root_note_elem.text else 0
                            sample_name = sample_name_elem.text or ""
                            
                            # Detect if root note seems wrong
                            if current_root <= 12:  # C0 or below is suspicious
                                detected_note = self.detect_note_from_filename(sample_name)
                                if detected_note and detected_note != current_root:
                                    issues['incorrect_root_notes'].append({
                                        'instrument': i,
                                        'layer': j,
                                        'current_root': current_root,
                                        'detected_root': detected_note,
                                        'sample_name': sample_name,
                                        'note_name': self.midi_to_note_name(detected_note)
                                    })
                            
                            # Check velocity ranges
                            vel_low = int(velocity_low_elem.text) if velocity_low_elem and velocity_low_elem.text else 0
                            vel_high = int(velocity_high_elem.text) if velocity_high_elem and velocity_high_elem.text else 127
                            
                            if vel_low == 0 and vel_high == 127:
                                issues['velocity_overlaps'].append({
                                    'instrument': i,
                                    'layer': j,
                                    'sample_name': sample_name
                                })
                
                # Check instrument ranges
                low_note_elem = instrument.find('LowNote')
                high_note_elem = instrument.find('HighNote')
                
                if low_note_elem is not None and high_note_elem is not None:
                    low_note = int(low_note_elem.text) if low_note_elem.text else 0
                    high_note = int(high_note_elem.text) if high_note_elem.text else 127
                    
                    if low_note == 0 and high_note == 127:
                        issues['range_problems'].append({
                            'instrument': i,
                            'issue': 'Full MIDI range (0-127) - too broad',
                            'recommendation': 'Set specific key ranges for each instrument'
                        })
        
            # Generate recommendations
            if issues['incorrect_root_notes']:
                issues['recommendations'].append("🎵 Fix root note mappings - detected samples with wrong pitch assignments")
            if issues['velocity_overlaps']:
                issues['recommendations'].append("🔊 Fix velocity ranges - all samples respond to full velocity range")
            if issues['range_problems']:
                issues['recommendations'].append("🎹 Fix instrument ranges - overly broad key ranges detected")
                
        except Exception as e:
            issues['error'] = str(e)
            
        return issues
    
    def detect_note_from_filename(self, filename: str) -> Optional[int]:
        """Detect MIDI note number from filename"""
        if not filename:
            return None
            
        # Try different patterns
        for pattern, pattern_type in self.sample_patterns.items():
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                if pattern_type == 'note_octave':
                    # Extract note like "C4", "F#3"
                    note_str = match.group(1).upper()
                    return self.note_string_to_midi(note_str)
                elif pattern_type == 'midi_number':
                    # Direct MIDI number
                    try:
                        midi_num = int(match.group(1))
                        if 0 <= midi_num <= 127:
                            return midi_num
                    except ValueError:
                        continue
                elif pattern_type == 'note_only':
                    # Note without octave, assume octave 4
                    note_str = match.group(1).upper() + '4'
                    return self.note_string_to_midi(note_str)
        
        return None
    
    def note_string_to_midi(self, note_str: str) -> Optional[int]:
        """Convert note string like 'C4' to MIDI number"""
        if len(note_str) < 2:
            return None
            
        # Extract note name and octave
        if '#' in note_str or 'b' in note_str:
            note_name = note_str[:2]
            octave_str = note_str[2:]
        else:
            note_name = note_str[0]
            octave_str = note_str[1:]
        
        try:
            octave = int(octave_str)
        except ValueError:
            return None
        
        # Convert note name to semitone offset
        note_name = note_name.replace('b', '#')  # Convert flats to sharps for simplicity
        
        note_offsets = {
            'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5,
            'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11
        }
        
        if note_name not in note_offsets:
            return None
        
        # Calculate MIDI number: (octave + 1) * 12 + note_offset
        midi_number = (octave + 1) * 12 + note_offsets[note_name]
        
        return midi_number if 0 <= midi_number <= 127 else None
    
    def midi_to_note_name(self, midi_number: int) -> str:
        """Convert MIDI number to note name"""
        if not 0 <= midi_number <= 127:
            return f"INVALID({midi_number})"
        
        octave = (midi_number // 12) - 1
        note_index = midi_number % 12
        note_name = self.note_names[note_index]
        
        return f"{note_name}{octave}"
    
    def fix_mapping_issues(self, xpm_path: str, fixes: Dict = None) -> bool:
        """Fix mapping issues in XPM file"""
        if fixes is None:
            fixes = {
                'fix_root_notes': True,
                'fix_velocity_ranges': True,
                'fix_instrument_ranges': True,
                'auto_detect_ranges': True
            }
        
        try:
            tree = ET.parse(xpm_path)
            root = tree.getroot()
            instruments = root.findall('.//Instrument')
            
            # Create backup
            backup_path = xpm_path + '.mapping_backup'
            if not os.path.exists(backup_path):
                import shutil
                shutil.copy2(xpm_path, backup_path)
            
            changes_made = False
            
            for i, instrument in enumerate(instruments):
                # Fix root notes
                if fixes.get('fix_root_notes'):
                    if self._fix_instrument_root_notes(instrument):
                        changes_made = True
                
                # Fix velocity ranges
                if fixes.get('fix_velocity_ranges'):
                    if self._fix_instrument_velocity_ranges(instrument, i):
                        changes_made = True
                
                # Fix instrument ranges
                if fixes.get('fix_instrument_ranges'):
                    if self._fix_instrument_key_ranges(instrument, i):
                        changes_made = True
            
            if changes_made:
                tree.write(xpm_path, encoding='utf-8', xml_declaration=True)
                logging.info(f"✅ Fixed mapping issues in {os.path.basename(xpm_path)}")
                return True
            
        except Exception as e:
            logging.error(f"Error fixing mapping issues: {e}")
            return False
        
        return False
    
    def _fix_instrument_root_notes(self, instrument) -> bool:
        """Fix root notes for an instrument based on sample names"""
        changed = False
        layers = instrument.find('Layers')
        
        if layers is not None:
            for layer in layers.findall('Layer'):
                root_note_elem = layer.find('RootNote')
                sample_name_elem = layer.find('SampleName')
                
                if root_note_elem is not None and sample_name_elem is not None:
                    current_root = int(root_note_elem.text) if root_note_elem.text else 0
                    sample_name = sample_name_elem.text or ""
                    
                    # Only fix if current root note is suspicious (very low)
                    if current_root <= 12:
                        detected_note = self.detect_note_from_filename(sample_name)
                        if detected_note and detected_note != current_root:
                            root_note_elem.text = str(detected_note + 1)  # ConvertWithMoss +1 offset
                            changed = True
                            logging.info(f"Fixed root note: {sample_name} {current_root} → {detected_note} ({self.midi_to_note_name(detected_note)})")
        
        return changed
    
    def _fix_instrument_velocity_ranges(self, instrument, instrument_index: int) -> bool:
        """Fix velocity ranges to avoid overlap"""
        changed = False
        layers = instrument.find('Layers')
        
        if layers is not None:
            layer_list = layers.findall('Layer')
            num_layers = len(layer_list)
            
            # If multiple layers, split velocity ranges
            if num_layers > 1:
                velocity_split = 127 // num_layers
                
                for i, layer in enumerate(layer_list):
                    vel_low_elem = layer.find('VelocityLow')
                    vel_high_elem = layer.find('VelocityHigh')
                    
                    if vel_low_elem is None:
                        vel_low_elem = ET.SubElement(layer, 'VelocityLow')
                    if vel_high_elem is None:
                        vel_high_elem = ET.SubElement(layer, 'VelocityHigh')
                    
                    # Calculate new velocity range
                    new_low = i * velocity_split
                    new_high = min((i + 1) * velocity_split - 1, 127) if i < num_layers - 1 else 127
                    
                    if vel_low_elem.text != str(new_low) or vel_high_elem.text != str(new_high):
                        vel_low_elem.text = str(new_low)
                        vel_high_elem.text = str(new_high)
                        changed = True
                        logging.info(f"Fixed velocity range for instrument {instrument_index}, layer {i}: {new_low}-{new_high}")
        
        return changed
    
    def _fix_instrument_key_ranges(self, instrument, instrument_index: int) -> bool:
        """Fix instrument key ranges based on root notes"""
        changed = False
        layers = instrument.find('Layers')
        
        if layers is not None:
            # Find the primary root note for this instrument
            root_notes = []
            for layer in layers.findall('Layer'):
                root_note_elem = layer.find('RootNote')
                if root_note_elem is not None and root_note_elem.text:
                    root_notes.append(int(root_note_elem.text))
            
            if root_notes:
                # Use the first/primary root note to set ranges
                primary_root = root_notes[0]
                
                # Set a reasonable range around the root note (±6 semitones by default)
                new_low = max(0, primary_root - 6)
                new_high = min(127, primary_root + 6)
                
                low_note_elem = instrument.find('LowNote')
                high_note_elem = instrument.find('HighNote')
                
                if low_note_elem is None:
                    low_note_elem = ET.SubElement(instrument, 'LowNote')
                if high_note_elem is None:
                    high_note_elem = ET.SubElement(instrument, 'HighNote')
                
                current_low = int(low_note_elem.text) if low_note_elem.text else 0
                current_high = int(high_note_elem.text) if high_note_elem.text else 127
                
                # Only change if currently using full range or clearly wrong
                if (current_low == 0 and current_high == 127) or current_low > current_high:
                    low_note_elem.text = str(new_low)
                    high_note_elem.text = str(new_high)
                    changed = True
                    logging.info(f"Fixed key range for instrument {instrument_index}: {self.midi_to_note_name(new_low)}-{self.midi_to_note_name(new_high)}")
        
        return changed

def main():
    """Test the mapping corrector with VOCAL STRING.xpm"""
    test_file = '/Volumes/MPC LIVE 2/Test/VOCAL STRING.xpm'
    
    if not os.path.exists(test_file):
        print("⚠️ VOCAL STRING.xpm not found")
        return
    
    corrector = XPMappingCorrector()
    
    print("🔍 Analyzing mapping issues...")
    issues = corrector.analyze_mapping_issues(test_file)
    
    print(f"\n📊 Analysis Results:")
    print(f"   Root note issues: {len(issues['incorrect_root_notes'])}")
    print(f"   Velocity overlaps: {len(issues['velocity_overlaps'])}")
    print(f"   Range problems: {len(issues['range_problems'])}")
    
    if issues['incorrect_root_notes']:
        print(f"\n🎵 Root Note Issues:")
        for issue in issues['incorrect_root_notes'][:5]:  # Show first 5
            print(f"   Sample: {issue['sample_name']}")
            print(f"   Current: {issue['current_root']} ({corrector.midi_to_note_name(issue['current_root'])})")
            print(f"   Detected: {issue['detected_root']} ({issue['note_name']})")
            print()
    
    if issues['recommendations']:
        print(f"💡 Recommendations:")
        for rec in issues['recommendations']:
            print(f"   {rec}")

if __name__ == "__main__":
    main()
