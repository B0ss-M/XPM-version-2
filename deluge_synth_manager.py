#!/usr/bin/env python3
"""
Deluge Synth File Manager
A comprehensive tool for creating, editing, and managing Deluge drum kits and synth instruments.

Based on core features from XPM converter, adapted for Deluge's XML-based file system.
Supports reading/writing Deluge .xml files and understanding the Deluge filing system.

Features:
- Read and write Deluge drum kit XML files
- Create and manage synth instrument XML files
- Audio file conversion and sample management
- Batch processing capabilities
- GUI interface for easy use
- File validation and error checking

Author: AI Assistant
Date: February 2026
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import shutil
import glob
import wave
import logging
import traceback
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape as xml_escape, unescape as xml_unescape
import json
import sys
import threading
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple, Any, Union
from pathlib import Path
import struct
import re
import time
from collections import defaultdict

# Try to import optional dependencies for enhanced audio support
try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

# Deluge-specific constants and configuration
DELUGE_SAMPLE_RATE = 44100
MAX_DRUM_PADS = 16  # Deluge has 16 drum pads
MAX_VELOCITY_LAYERS = 8  # Maximum velocity layers per pad

# Deluge file system structure
DELUGE_FOLDERS = {
    'kits': 'KITS',
    'samples': 'SAMPLES',
    'synths': 'SYNTHS',
    'songs': 'SONGS'
}

# Supported audio formats for Deluge
SUPPORTED_AUDIO_FORMATS = {
    '.wav': 'WAV Audio',
    '.aiff': 'AIFF Audio', 
    '.aif': 'AIFF Audio',
    '.flac': 'FLAC Audio',
    '.mp3': 'MP3 Audio',
    '.ogg': 'OGG Audio'
}

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to import XPM utilities for MPC conversion
try:
    from xmp_utils import _parse_xmp_for_rebuild
    XPM_UTILS_AVAILABLE = True
except ImportError:
    try:
        from xpm_utils import _parse_xpm_for_rebuild  # Correct name
        XPM_UTILS_AVAILABLE = True
    except ImportError:
        XPM_UTILS_AVAILABLE = False
        logger.warning("XPM utilities not available - MPC conversion disabled")


@dataclass
class DelugeSample:
    """Represents a single sample in a Deluge kit or synth."""
    file_path: str
    name: str = ""
    start_pos: int = 0
    end_pos: Optional[int] = None
    loop_start: Optional[int] = None
    loop_end: Optional[int] = None
    reversed: bool = False
    transpose: int = 0
    volume: float = 0.0  # In dB
    pan: float = 0.0     # -1.0 to 1.0
    
    def __post_init__(self):
        if not self.name:
            self.name = Path(self.file_path).stem


@dataclass
class DelugePad:
    """Represents a drum pad in a Deluge kit."""
    index: int  # 0-15 for the 16 pads
    name: str = ""
    samples: List[DelugeSample] = field(default_factory=list)
    velocity_layers: List[Tuple[int, int]] = field(default_factory=list)  # (min_vel, max_vel) pairs
    mute: bool = False
    solo: bool = False
    volume: float = 0.0
    pan: float = 0.0
    lpf_freq: float = 50.0  # Low-pass filter frequency
    hpf_freq: float = 50.0  # High-pass filter frequency
    
    def add_sample(self, sample: DelugeSample, min_velocity: int = 0, max_velocity: int = 127):
        """Add a sample with velocity layer information."""
        self.samples.append(sample)
        self.velocity_layers.append((min_velocity, max_velocity))


@dataclass
class DelugeSynthParams:
    """Represents synth parameters for a Deluge synth patch."""
    # Oscillators
    osc1_type: str = "SINE"  # SINE, SQUARE, SAW, TRIANGLE, ANALOG_SAW, etc.
    osc1_volume: float = 0.0
    osc1_transpose: int = 0
    osc1_detune: int = 0
    
    osc2_type: str = "SINE"
    osc2_volume: float = -50.0  # Usually quieter by default
    osc2_transpose: int = 0
    osc2_detune: int = 0
    
    # Filter
    lpf_frequency: float = 50.0  # 0-50 range in Deluge
    lpf_resonance: float = 0.0
    hpf_frequency: float = 0.0
    hpf_resonance: float = 0.0
    
    # Envelope
    env1_attack: float = 0.0
    env1_decay: float = 0.0
    env1_sustain: float = 50.0
    env1_release: float = 0.0
    
    # LFO
    lfo1_type: str = "TRIANGLE"
    lfo1_rate: float = 2.0
    
    # Modulation routing
    modulations: Dict[str, Any] = field(default_factory=dict)
    
    # Effects
    reverb_amount: float = 0.0
    delay_amount: float = 0.0
    distortion_amount: float = 0.0
    bit_crush_amount: float = 50.0
    
    # Arp settings
    arp_mode: str = "OFF"
    arp_rate: float = 8.0


class DelugeXMLHandler:
    """Core class for handling Deluge XML file operations."""
    
    def __init__(self):
        self.encoding = 'utf-8'
        self.xml_declaration = True
        
    def create_xml_header(self, element_type: str = "kit") -> ET.Element:
        """Create the standard Deluge XML header structure."""
        # Deluge uses different root elements for different file types
        if element_type == "kit":
            root = ET.Element("kit")
        elif element_type == "sound":
            root = ET.Element("sound")
            root.set("firmwareVersion", "c1.2.0")
            root.set("earliestCompatibleFirmware", "4.1.0")
            root.set("polyphonic", "poly")
            root.set("voicePriority", "1")
            root.set("mode", "subtractive")
        else:
            root = ET.Element(element_type)
        return root
    
    def format_xml_output(self, element: ET.Element) -> str:
        """Format XML with proper indentation and encoding for Deluge."""
        # Deluge prefers compact XML without too much whitespace
        ET.indent(element, space="  ")
        rough_string = ET.tostring(element, encoding='unicode')
        
        # Add XML declaration
        if self.xml_declaration:
            xml_str = f'<?xml version="1.0" encoding="{self.encoding}"?>\n{rough_string}'
        else:
            xml_str = rough_string
            
        return xml_str
    
    def validate_file_path(self, file_path: str) -> bool:
        """Validate that file path follows Deluge conventions."""
        path = Path(file_path)
        
        # Basic validation
        if not path.suffix.lower() == '.xml':
            return False
            
        # Check for invalid characters that Deluge doesn't like
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
        if any(char in str(path) for char in invalid_chars):
            return False
            
        return True
    
    def backup_file(self, file_path: str) -> str:
        """Create a backup of an existing file before modification."""
        backup_path = f"{file_path}.backup"
        if os.path.exists(file_path):
            shutil.copy2(file_path, backup_path)
            return backup_path
        return ""


class DelugeDrumKitHandler(DelugeXMLHandler):
    """Handles creation and management of Deluge drum kit XML files."""
    
    def __init__(self):
        super().__init__()
        self.pads = {}  # Dictionary of pad index to DelugePad objects
        
    def create_empty_kit(self, kit_name: str = "New Kit") -> None:
        """Create an empty drum kit with default pads."""
        self.pads = {}
        for i in range(MAX_DRUM_PADS):
            pad = DelugePad(index=i, name=f"Pad {i+1}")
            self.pads[i] = pad
    
    def add_sample_to_pad(self, pad_index: int, sample_path: str, 
                         min_velocity: int = 0, max_velocity: int = 127) -> bool:
        """Add a sample to a specific pad with velocity layer settings."""
        if pad_index not in range(MAX_DRUM_PADS):
            logger.error(f"Invalid pad index: {pad_index}. Must be 0-{MAX_DRUM_PADS-1}")
            return False
            
        if not os.path.exists(sample_path):
            logger.error(f"Sample file not found: {sample_path}")
            return False
            
        if pad_index not in self.pads:
            self.pads[pad_index] = DelugePad(index=pad_index)
            
        sample = DelugeSample(file_path=sample_path)
        self.pads[pad_index].add_sample(sample, min_velocity, max_velocity)
        
        logger.info(f"Added sample {sample_path} to pad {pad_index}")
        return True
    
    def generate_kit_xml(self, kit_name: str = "New Kit") -> str:
        """Generate the complete drum kit XML structure matching real Deluge format."""
        root = self.create_xml_header("kit")
        
        # Kit-level parameters (matching real Deluge format)
        ET.SubElement(root, "lpfMode").text = "24dB"
        ET.SubElement(root, "modFXType").text = "flanger"
        ET.SubElement(root, "modFXCurrentParam").text = "feedback"
        ET.SubElement(root, "currentFilterType").text = "lpf"
        
        # Default parameters block
        default_params = ET.SubElement(root, "defaultParams")
        
        # Delay section
        delay = ET.SubElement(default_params, "delay")
        ET.SubElement(delay, "rate").text = "0x00000000"
        ET.SubElement(delay, "feedback").text = "0x80000000"
        
        # Other default parameters
        ET.SubElement(default_params, "reverbAmount").text = "0x80000000"
        ET.SubElement(default_params, "volume").text = "0x3504F334"
        ET.SubElement(default_params, "pan").text = "0x00000000"
        
        # Filter defaults
        lpf = ET.SubElement(default_params, "lpf")
        ET.SubElement(lpf, "frequency").text = "0x7FFFFFFF"
        ET.SubElement(lpf, "resonance").text = "0x00000000"
        
        hpf = ET.SubElement(default_params, "hpf")
        ET.SubElement(hpf, "frequency").text = "0x80000000"
        ET.SubElement(hpf, "resonance").text = "0xC0000000"
        
        # Add more default parameters
        ET.SubElement(default_params, "modFXDepth").text = "0x00000000"
        ET.SubElement(default_params, "modFXRate").text = "0xE0000000"
        ET.SubElement(default_params, "stutterRate").text = "0x00000000"
        ET.SubElement(default_params, "sampleRateReduction").text = "0x80000000"
        ET.SubElement(default_params, "bitCrush").text = "0x80000000"
        
        # Equalizer section
        eq = ET.SubElement(default_params, "equalizer")
        ET.SubElement(eq, "bass").text = "0x00000000"
        ET.SubElement(eq, "treble").text = "0x00000000"
        ET.SubElement(eq, "bassFrequency").text = "0x00000000"
        ET.SubElement(eq, "trebleFrequency").text = "0x00000000"
        
        ET.SubElement(default_params, "modFXOffset").text = "0x00000000"
        ET.SubElement(default_params, "modFXFeedback").text = "0x80000000"
        
        # Sound sources (drum sounds)
        sound_sources = ET.SubElement(root, "soundSources")
        
        # Add drum sounds
        for pad_index in sorted(self.pads.keys()):
            pad = self.pads[pad_index]
            if pad.samples:  # Only add pads that have samples
                self._add_pad_to_xml(sound_sources, pad)
        
        # Selected drum index
        ET.SubElement(root, "selectedDrumIndex").text = "0"
        
        return self.format_xml_output(root)
    
    def _add_pad_to_xml(self, parent: ET.Element, pad: DelugePad) -> None:
        """Add a single pad's XML structure matching real Deluge format."""
        sound_elem = ET.SubElement(parent, "sound")
        
        # Sound name
        ET.SubElement(sound_elem, "name").text = pad.name or f"PAD{pad.index}"
        
        # Oscillator 1 (for samples)
        osc1 = ET.SubElement(sound_elem, "osc1")
        if pad.samples:
            sample = pad.samples[0]  # Use first sample as primary
            ET.SubElement(osc1, "type").text = "sample"
            ET.SubElement(osc1, "loopMode").text = "0"
            ET.SubElement(osc1, "reversed").text = "0"
            ET.SubElement(osc1, "timeStretchEnable").text = "0"
            ET.SubElement(osc1, "timeStretchAmount").text = "0"
            ET.SubElement(osc1, "fileName").text = self._convert_to_deluge_path(sample.file_path)
            
            # Zone information
            zone = ET.SubElement(osc1, "zone")
            ET.SubElement(zone, "startSamplePos").text = str(sample.start_pos)
            if sample.end_pos:
                ET.SubElement(zone, "endSamplePos").text = str(sample.end_pos)
        else:
            # Default oscillator settings
            ET.SubElement(osc1, "type").text = "sine"
            ET.SubElement(osc1, "transpose").text = "0"
            ET.SubElement(osc1, "cents").text = "0"
            ET.SubElement(osc1, "retrigPhase").text = "-1"
        
        # Oscillator 2 (usually disabled for drum sounds)
        osc2 = ET.SubElement(sound_elem, "osc2")
        ET.SubElement(osc2, "type").text = "square"
        ET.SubElement(osc2, "transpose").text = "0"
        ET.SubElement(osc2, "cents").text = "0"
        ET.SubElement(osc2, "retrigPhase").text = "-1"
        
        # Sound properties
        ET.SubElement(sound_elem, "polyphonic").text = "0"  # Monophonic for drums
        ET.SubElement(sound_elem, "clippingAmount").text = "0"
        ET.SubElement(sound_elem, "voicePriority").text = "1"
        
        # LFO sections
        lfo1 = ET.SubElement(sound_elem, "lfo1")
        ET.SubElement(lfo1, "type").text = "triangle"
        
        lfo2 = ET.SubElement(sound_elem, "lfo2")
        ET.SubElement(lfo2, "type").text = "triangle"
        
        # Mode
        ET.SubElement(sound_elem, "mode").text = "subtractive"
        
        # Unison section
        unison = ET.SubElement(sound_elem, "unison")
        ET.SubElement(unison, "num").text = "1"
        ET.SubElement(unison, "detune").text = "8"
        
        # Compressor section
        comp = ET.SubElement(sound_elem, "compressor")
        ET.SubElement(comp, "syncLevel").text = "6"
        ET.SubElement(comp, "attack").text = "327244"
        ET.SubElement(comp, "release").text = "936"
        
        # Delay section
        delay = ET.SubElement(sound_elem, "delay")
        ET.SubElement(delay, "pingPong").text = "1"
        ET.SubElement(delay, "analog").text = "0"
        ET.SubElement(delay, "syncLevel").text = "7"
        
        ET.SubElement(sound_elem, "lpfMode").text = "24dB"
        ET.SubElement(sound_elem, "modFXType").text = "none"
        
        # Default parameters for this sound
        self._add_sound_default_params(sound_elem, pad)
        
        # MIDI and mod knobs
        ET.SubElement(sound_elem, "midiKnobs")
        self._add_mod_knobs(sound_elem)
    
    def _add_sound_default_params(self, sound_elem: ET.Element, pad: DelugePad) -> None:
        """Add default parameters section for a sound (matching real Deluge format)."""
        default_params = ET.SubElement(sound_elem, "defaultParams")
        
        # Core parameters with hex values
        ET.SubElement(default_params, "arpeggiatorGate").text = "0x00000000"
        ET.SubElement(default_params, "portamento").text = "0x80000000"
        ET.SubElement(default_params, "compressorShape").text = "0xDC28F5B2"
        
        # Oscillator volumes and pulse widths
        ET.SubElement(default_params, "oscAVolume").text = "0x7FFFFFFF"
        ET.SubElement(default_params, "oscAPulseWidth").text = "0x00000000"
        ET.SubElement(default_params, "oscAWavetablePosition").text = "0x00000000"
        ET.SubElement(default_params, "oscBVolume").text = "0x80000000"
        ET.SubElement(default_params, "oscBPulseWidth").text = "0x00000000"
        ET.SubElement(default_params, "oscBWavetablePosition").text = "0x00000000"
        ET.SubElement(default_params, "noiseVolume").text = "0x80000000"
        
        # Volume and pan (convert from float to hex)
        volume_hex = self._float_to_deluge_hex(pad.volume)
        pan_hex = self._float_to_deluge_hex(pad.pan)
        ET.SubElement(default_params, "volume").text = volume_hex
        ET.SubElement(default_params, "pan").text = pan_hex
        
        # Filter parameters
        lpf_freq_hex = self._float_to_deluge_hex(pad.lpf_freq)
        hpf_freq_hex = self._float_to_deluge_hex(pad.hpf_freq)
        ET.SubElement(default_params, "lpfFrequency").text = lpf_freq_hex
        ET.SubElement(default_params, "lpfResonance").text = "0x80000000"
        ET.SubElement(default_params, "hpfFrequency").text = hpf_freq_hex
        ET.SubElement(default_params, "hpfResonance").text = "0x80000000"
        
        # LFO parameters
        ET.SubElement(default_params, "lfo1Rate").text = "0x1999997E"
        ET.SubElement(default_params, "lfo2Rate").text = "0x00000000"
        
        # Modulation parameters
        ET.SubElement(default_params, "modulator1Amount").text = "0x80000000"
        ET.SubElement(default_params, "modulator1Feedback").text = "0x80000000"
        ET.SubElement(default_params, "modulator2Amount").text = "0x80000000"
        ET.SubElement(default_params, "modulator2Feedback").text = "0x80000000"
        ET.SubElement(default_params, "carrier1Feedback").text = "0x80000000"
        ET.SubElement(default_params, "carrier2Feedback").text = "0x80000000"
        
        # Effects parameters
        ET.SubElement(default_params, "modFXRate").text = "0x00000000"
        ET.SubElement(default_params, "modFXDepth").text = "0x00000000"
        ET.SubElement(default_params, "delayRate").text = "0x00000000"
        ET.SubElement(default_params, "delayFeedback").text = "0x80000000"
        ET.SubElement(default_params, "reverbAmount").text = "0x80000000"
        ET.SubElement(default_params, "arpeggiatorRate").text = "0x1999997E"
        ET.SubElement(default_params, "stutterRate").text = "0x00000000"
        ET.SubElement(default_params, "sampleRateReduction").text = "0x80000000"
        ET.SubElement(default_params, "bitCrush").text = "0x80000000"
        ET.SubElement(default_params, "modFXOffset").text = "0x00000000"
        ET.SubElement(default_params, "modFXFeedback").text = "0x80000000"
        
        # Envelopes
        env1 = ET.SubElement(default_params, "envelope1")
        ET.SubElement(env1, "attack").text = "0x80000000"
        ET.SubElement(env1, "decay").text = "0xE6666654"
        ET.SubElement(env1, "sustain").text = "0x7FFFFFFF"
        ET.SubElement(env1, "release").text = "0x80000000"
        
        env2 = ET.SubElement(default_params, "envelope2")
        ET.SubElement(env2, "attack").text = "0xE6666654"
        ET.SubElement(env2, "decay").text = "0xE6666654"
        ET.SubElement(env2, "sustain").text = "0xFFFFFFE9"
        ET.SubElement(env2, "release").text = "0xE6666654"
        
        # Patch cables (modulation routing)
        patch_cables = ET.SubElement(default_params, "patchCables")
        
        # Velocity to volume
        cable1 = ET.SubElement(patch_cables, "patchCable")
        cable1.set("source", "velocity")
        cable1.set("destination", "volume")
        cable1.set("amount", "0x3FFFFFE8")
        
        # Aftertouch to volume
        cable2 = ET.SubElement(patch_cables, "patchCable")
        cable2.set("source", "aftertouch")
        cable2.set("destination", "volume")
        cable2.set("amount", "0x2A3D7094")
        
        # Y axis to filter frequency
        cable3 = ET.SubElement(patch_cables, "patchCable")
        cable3.set("source", "y")
        cable3.set("destination", "lpfFrequency")
        cable3.set("amount", "0x19999990")
        
        # Equalizer
        eq = ET.SubElement(default_params, "equalizer")
        ET.SubElement(eq, "bass").text = "0x00000000"
        ET.SubElement(eq, "treble").text = "0x00000000"
        ET.SubElement(eq, "bassFrequency").text = "0x00000000"
        ET.SubElement(eq, "trebleFrequency").text = "0x00000000"
    
    def _add_mod_knobs(self, sound_elem: ET.Element) -> None:
        """Add mod knobs section (matching real Deluge format)."""
        mod_knobs = ET.SubElement(sound_elem, "modKnobs")
        
        # Standard mod knob assignments for drums
        knob_assignments = [
            "pan", "volumePostFX", "lpfResonance", "lpfFrequency",
            "env1Release", "env1Attack", "delayFeedback", "delayRate",
            "reverbAmount", "volumePostReverbSend", "pitch", "lfo1Rate",
            "portamento", "stutterRate", "bitcrushAmount", "sampleRateReduction"
        ]
        
        for assignment in knob_assignments:
            knob = ET.SubElement(mod_knobs, "modKnob")
            knob.set("controlsParam", assignment)
            if assignment == "volumePostReverbSend":
                knob.set("patchAmountFromSource", "compressor")
            elif assignment == "pitch":
                knob.set("patchAmountFromSource", "lfo1")
    
    def _float_to_deluge_hex(self, value: float, range_min: float = -50.0, range_max: float = 50.0) -> str:
        """Convert float value to Deluge's hex format."""
        # Normalize to 0.0-1.0 range
        normalized = (value - range_min) / (range_max - range_min)
        normalized = max(0.0, min(1.0, normalized))  # Clamp to 0-1
        
        # Convert to signed 32-bit integer range
        if normalized == 0.5:  # Center value
            hex_val = 0x00000000
        elif normalized < 0.5:
            # Negative range: 0x80000000 to 0x00000000
            hex_val = int(0x80000000 + (normalized * 2.0 * 0x80000000))
        else:
            # Positive range: 0x00000000 to 0x7FFFFFFF
            hex_val = int((normalized - 0.5) * 2.0 * 0x7FFFFFFF)
        
        return f"0x{hex_val:08X}"
    
    def _convert_to_deluge_path(self, absolute_path: str) -> str:
        """Convert absolute file path to Deluge-relative path."""
        path = Path(absolute_path)
        
        # If path contains 'SAMPLES', use everything after that
        parts = path.parts
        if 'SAMPLES' in parts:
            samples_index = parts.index('SAMPLES')
            return str(Path(*parts[samples_index + 1:]))
        
        # Otherwise just use the filename
        return path.name
    
    def save_kit(self, output_path: str, kit_name: str = "New Kit") -> bool:
        """Save the drum kit to an XML file."""
        try:
            xml_content = self.generate_kit_xml(kit_name)
            
            with open(output_path, 'w', encoding=self.encoding) as f:
                f.write(xml_content)
                
            logger.info(f"Saved drum kit to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving drum kit: {e}")
            traceback.print_exc()
            return False
    
    def load_kit(self, kit_path: str) -> bool:
        """Load an existing drum kit XML file."""
        try:
            if not os.path.exists(kit_path):
                logger.error(f"Kit file not found: {kit_path}")
                return False
                
            tree = ET.parse(kit_path)
            root = tree.getroot()
            
            if root.tag != "drumKit":
                logger.error("Invalid drum kit file format")
                return False
            
            self.pads = {}
            
            # Parse sound elements (pads)
            for sound_elem in root.findall("sound"):
                pad_name = sound_elem.get("name", "")
                
                # Extract pad index from name if possible
                pad_index = self._extract_pad_index(pad_name)
                if pad_index is None:
                    continue
                    
                pad = DelugePad(index=pad_index, name=pad_name)
                self._parse_pad_from_xml(sound_elem, pad, kit_path)
                self.pads[pad_index] = pad
            
            logger.info(f"Loaded drum kit from: {kit_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading drum kit: {e}")
            traceback.print_exc()
            return False
    
    def _extract_pad_index(self, pad_name: str) -> Optional[int]:
        """Extract numeric pad index from pad name."""
        # Try to extract number from names like "pad0", "pad1", etc.
        match = re.search(r'pad(\d+)', pad_name.lower())
        if match:
            index = int(match.group(1))
            if 0 <= index < MAX_DRUM_PADS:
                return index
        return None
    
    def _parse_pad_from_xml(self, sound_elem: ET.Element, pad: DelugePad, kit_dir: str) -> None:
        """Parse pad parameters and samples from XML element."""
        # Parse volume
        volume_elem = sound_elem.find("volume")
        if volume_elem is not None and volume_elem.text:
            pad.volume = float(volume_elem.text)
        
        # Parse pan
        pan_elem = sound_elem.find("pan")
        if pan_elem is not None and pan_elem.text:
            pad.pan = float(pan_elem.text) / 50.0  # Convert from -50/50 to -1.0/1.0
        
        # Parse filter settings
        lpf_elem = sound_elem.find("lpfFrequency")
        if lpf_elem is not None and lpf_elem.text:
            pad.lpf_freq = float(lpf_elem.text)
            
        hpf_elem = sound_elem.find("hpfFrequency")
        if hpf_elem is not None and hpf_elem.text:
            pad.hpf_freq = float(hpf_elem.text)
        
        # Parse sample file
        filename_elem = sound_elem.find("fileName")
        if filename_elem is not None and filename_elem.text:
            # Convert relative path to absolute path
            sample_path = self._resolve_sample_path(filename_elem.text, kit_dir)
            if sample_path and os.path.exists(sample_path):
                sample = DelugeSample(file_path=sample_path)
                pad.add_sample(sample)
    
    def _resolve_sample_path(self, relative_path: str, kit_dir: str) -> str:
        """Resolve relative sample path to absolute path."""
        kit_path = Path(kit_dir)
        
        # Try relative to kit directory first
        full_path = kit_path.parent / "SAMPLES" / relative_path
        if full_path.exists():
            return str(full_path)
        
        # Try relative to kit file directory
        full_path = kit_path.parent / relative_path
        if full_path.exists():
            return str(full_path)
            
        # Return original if we can't resolve it
        return relative_path
    
    def _add_sound_default_params(self, sound_elem: ET.Element, pad: DelugePad) -> None:
        """Add default parameters section for a sound (matching real Deluge format)."""
        default_params = ET.SubElement(sound_elem, "defaultParams")
        
        # Core parameters with hex values
        ET.SubElement(default_params, "arpeggiatorGate").text = "0x00000000"
        ET.SubElement(default_params, "portamento").text = "0x80000000"
        ET.SubElement(default_params, "compressorShape").text = "0xDC28F5B2"
        
        # Oscillator volumes and pulse widths
        ET.SubElement(default_params, "oscAVolume").text = "0x7FFFFFFF"
        ET.SubElement(default_params, "oscAPulseWidth").text = "0x00000000"
        ET.SubElement(default_params, "oscAWavetablePosition").text = "0x00000000"
        ET.SubElement(default_params, "oscBVolume").text = "0x80000000"
        ET.SubElement(default_params, "oscBPulseWidth").text = "0x00000000"
        ET.SubElement(default_params, "oscBWavetablePosition").text = "0x00000000"
        ET.SubElement(default_params, "noiseVolume").text = "0x80000000"
        
        # Volume and pan (convert from float to hex)
        volume_hex = self._float_to_deluge_hex(pad.volume)
        pan_hex = self._float_to_deluge_hex(pad.pan)
        ET.SubElement(default_params, "volume").text = volume_hex
        ET.SubElement(default_params, "pan").text = pan_hex
        
        # Filter parameters
        lpf_freq_hex = self._float_to_deluge_hex(pad.lpf_freq)
        hpf_freq_hex = self._float_to_deluge_hex(pad.hpf_freq)
        ET.SubElement(default_params, "lpfFrequency").text = lpf_freq_hex
        ET.SubElement(default_params, "lpfResonance").text = "0x80000000"
        ET.SubElement(default_params, "hpfFrequency").text = hpf_freq_hex
        ET.SubElement(default_params, "hpfResonance").text = "0x80000000"
        
        # LFO parameters
        ET.SubElement(default_params, "lfo1Rate").text = "0x1999997E"
        ET.SubElement(default_params, "lfo2Rate").text = "0x00000000"
        
        # Modulation parameters
        ET.SubElement(default_params, "modulator1Amount").text = "0x80000000"
        ET.SubElement(default_params, "modulator1Feedback").text = "0x80000000"
        ET.SubElement(default_params, "modulator2Amount").text = "0x80000000"
        ET.SubElement(default_params, "modulator2Feedback").text = "0x80000000"
        ET.SubElement(default_params, "carrier1Feedback").text = "0x80000000"
        ET.SubElement(default_params, "carrier2Feedback").text = "0x80000000"
        
        # Effects parameters
        ET.SubElement(default_params, "modFXRate").text = "0x00000000"
        ET.SubElement(default_params, "modFXDepth").text = "0x00000000"
        ET.SubElement(default_params, "delayRate").text = "0x00000000"
        ET.SubElement(default_params, "delayFeedback").text = "0x80000000"
        ET.SubElement(default_params, "reverbAmount").text = "0x80000000"
        ET.SubElement(default_params, "arpeggiatorRate").text = "0x1999997E"
        ET.SubElement(default_params, "stutterRate").text = "0x00000000"
        ET.SubElement(default_params, "sampleRateReduction").text = "0x80000000"
        ET.SubElement(default_params, "bitCrush").text = "0x80000000"
        ET.SubElement(default_params, "modFXOffset").text = "0x00000000"
        ET.SubElement(default_params, "modFXFeedback").text = "0x80000000"
        
        # Envelopes
        env1 = ET.SubElement(default_params, "envelope1")
        ET.SubElement(env1, "attack").text = "0x80000000"
        ET.SubElement(env1, "decay").text = "0xE6666654"
        ET.SubElement(env1, "sustain").text = "0x7FFFFFFF"
        ET.SubElement(env1, "release").text = "0x80000000"
        
        env2 = ET.SubElement(default_params, "envelope2")
        ET.SubElement(env2, "attack").text = "0xE6666654"
        ET.SubElement(env2, "decay").text = "0xE6666654"
        ET.SubElement(env2, "sustain").text = "0xFFFFFFE9"
        ET.SubElement(env2, "release").text = "0xE6666654"
        
        # Patch cables (modulation routing)
        patch_cables = ET.SubElement(default_params, "patchCables")
        
        # Velocity to volume
        cable1 = ET.SubElement(patch_cables, "patchCable")
        cable1.set("source", "velocity")
        cable1.set("destination", "volume")
        cable1.set("amount", "0x3FFFFFE8")
        
        # Aftertouch to volume
        cable2 = ET.SubElement(patch_cables, "patchCable")
        cable2.set("source", "aftertouch")
        cable2.set("destination", "volume")
        cable2.set("amount", "0x2A3D7094")
        
        # Y axis to filter frequency
        cable3 = ET.SubElement(patch_cables, "patchCable")
        cable3.set("source", "y")
        cable3.set("destination", "lpfFrequency")
        cable3.set("amount", "0x19999990")
        
        # Equalizer
        eq = ET.SubElement(default_params, "equalizer")
        ET.SubElement(eq, "bass").text = "0x00000000"
        ET.SubElement(eq, "treble").text = "0x00000000"
        ET.SubElement(eq, "bassFrequency").text = "0x00000000"
        ET.SubElement(eq, "trebleFrequency").text = "0x00000000"
    
    def _add_mod_knobs(self, sound_elem: ET.Element) -> None:
        """Add mod knobs section (matching real Deluge format)."""
        mod_knobs = ET.SubElement(sound_elem, "modKnobs")
        
        # Standard mod knob assignments for drums
        knob_assignments = [
            "pan", "volumePostFX", "lpfResonance", "lpfFrequency",
            "env1Release", "env1Attack", "delayFeedback", "delayRate",
            "reverbAmount", "volumePostReverbSend", "pitch", "lfo1Rate",
            "portamento", "stutterRate", "bitcrushAmount", "sampleRateReduction"
        ]
        
        for assignment in knob_assignments:
            knob = ET.SubElement(mod_knobs, "modKnob")
            knob.set("controlsParam", assignment)
            if assignment == "volumePostReverbSend":
                knob.set("patchAmountFromSource", "compressor")
            elif assignment == "pitch":
                knob.set("patchAmountFromSource", "lfo1")
    
    def _float_to_deluge_hex(self, value: float, range_min: float = -50.0, range_max: float = 50.0) -> str:
        """Convert float value to Deluge's hex format."""
        # Normalize to 0.0-1.0 range
        normalized = (value - range_min) / (range_max - range_min)
        normalized = max(0.0, min(1.0, normalized))  # Clamp to 0-1
        
        # Convert to signed 32-bit integer range
        if normalized == 0.5:  # Center value
            hex_val = 0x00000000
        elif normalized < 0.5:
            # Negative range: 0x80000000 to 0x00000000
            hex_val = int(0x80000000 + (normalized * 2.0 * 0x80000000))
        else:
            # Positive range: 0x00000000 to 0x7FFFFFFF
            hex_val = int((normalized - 0.5) * 2.0 * 0x7FFFFFFF)
        
        return f"0x{hex_val:08X}"


class DelugeSynthHandler(DelugeXMLHandler):
    """Handles creation and management of Deluge synth instrument XML files."""
    
    def __init__(self):
        super().__init__()
        self.synth_params = DelugeSynthParams()
        self.samples = []  # For wavetable/sample-based synths
        
    def create_subtractive_synth(self, synth_name: str = "New Synth") -> None:
        """Create a basic subtractive synthesizer patch."""
        self.synth_params = DelugeSynthParams()
        # Set up basic subtractive synth defaults
        self.synth_params.osc1_type = "ANALOG_SAW"
        self.synth_params.osc2_type = "ANALOG_SAW"
        self.synth_params.osc2_transpose = -12  # One octave down
        self.synth_params.lpf_frequency = 35.0
        self.synth_params.lpf_resonance = 10.0
        
    def add_sample_based_osc(self, sample_path: str, osc_number: int = 1) -> bool:
        """Add a sample-based oscillator to the synth."""
        if not os.path.exists(sample_path):
            logger.error(f"Sample file not found: {sample_path}")
            return False
            
        sample = DelugeSample(file_path=sample_path)
        self.samples.append(sample)
        
        # Set oscillator type to wavetable/sample
        if osc_number == 1:
            self.synth_params.osc1_type = "WAVETABLE"
        elif osc_number == 2:
            self.synth_params.osc2_type = "WAVETABLE"
            
        return True
    
    def generate_synth_xml(self, synth_name: str = "New Synth") -> str:
        """Generate the complete synth XML structure."""
        root = ET.Element("synth")
        root.set("synthVersion", "4.1.4")
        root.set("earliestCompatibleFirmware", "4.1.0")
        
        # Add polyphony settings
        polyphonic = ET.SubElement(root, "polyphonic")
        polyphonic.text = "1"  # 1 = polyphonic, 0 = monophonic
        
        voices = ET.SubElement(root, "voiceCount")
        voices.text = "8"  # Default voice count
        
        # Add oscillator 1
        osc1 = ET.SubElement(root, "osc1")
        self._add_oscillator_params(osc1, self.synth_params, 1)
        
        # Add oscillator 2
        osc2 = ET.SubElement(root, "osc2")
        self._add_oscillator_params(osc2, self.synth_params, 2)
        
        # Add filter section
        filter_elem = ET.SubElement(root, "lpf")
        self._add_filter_params(filter_elem, self.synth_params)
        
        # Add envelope
        env1 = ET.SubElement(root, "env1")
        self._add_envelope_params(env1, self.synth_params)
        
        # Add LFO
        lfo1 = ET.SubElement(root, "lfo1")
        self._add_lfo_params(lfo1, self.synth_params)
        
        # Add effects
        reverb = ET.SubElement(root, "reverbAmount")
        reverb.text = str(int(self.synth_params.reverb_amount))
        
        delay = ET.SubElement(root, "delayAmount")
        delay.text = str(int(self.synth_params.delay_amount))
        
        return self.format_xml_output(root)
    
    def _add_oscillator_params(self, osc_elem: ET.Element, params: DelugeSynthParams, osc_num: int) -> None:
        """Add oscillator parameters to XML element."""
        if osc_num == 1:
            osc_type = params.osc1_type
            volume = params.osc1_volume
            transpose = params.osc1_transpose
            detune = params.osc1_detune
        else:
            osc_type = params.osc2_type
            volume = params.osc2_volume
            transpose = params.osc2_transpose
            detune = params.osc2_detune
        
        # Oscillator type
        type_elem = ET.SubElement(osc_elem, "type")
        type_elem.text = osc_type
        
        # Volume
        vol_elem = ET.SubElement(osc_elem, "volume")
        vol_elem.text = str(int(volume))
        
        # Transpose
        trans_elem = ET.SubElement(osc_elem, "transpose")
        trans_elem.text = str(transpose)
        
        # Detune
        detune_elem = ET.SubElement(osc_elem, "detune")
        detune_elem.text = str(detune)
        
        # If using samples/wavetables, add file reference
        if osc_type == "WAVETABLE" and self.samples:
            filename = ET.SubElement(osc_elem, "fileName")
            filename.text = self._convert_to_deluge_path(self.samples[0].file_path)
    
    def _add_filter_params(self, filter_elem: ET.Element, params: DelugeSynthParams) -> None:
        """Add filter parameters to XML element."""
        freq_elem = ET.SubElement(filter_elem, "frequency")
        freq_elem.text = str(int(params.lpf_frequency))
        
        res_elem = ET.SubElement(filter_elem, "resonance")
        res_elem.text = str(int(params.lpf_resonance))
    
    def _add_envelope_params(self, env_elem: ET.Element, params: DelugeSynthParams) -> None:
        """Add envelope parameters to XML element."""
        attack_elem = ET.SubElement(env_elem, "attack")
        attack_elem.text = str(int(params.env1_attack))
        
        decay_elem = ET.SubElement(env_elem, "decay")
        decay_elem.text = str(int(params.env1_decay))
        
        sustain_elem = ET.SubElement(env_elem, "sustain")
        sustain_elem.text = str(int(params.env1_sustain))
        
        release_elem = ET.SubElement(env_elem, "release")
        release_elem.text = str(int(params.env1_release))
    
    def _add_lfo_params(self, lfo_elem: ET.Element, params: DelugeSynthParams) -> None:
        """Add LFO parameters to XML element."""
        type_elem = ET.SubElement(lfo_elem, "type")
        type_elem.text = params.lfo1_type
        
        rate_elem = ET.SubElement(lfo_elem, "rate")
        rate_elem.text = str(int(params.lfo1_rate))
    
    def save_synth(self, output_path: str, synth_name: str = "New Synth") -> bool:
        """Save the synth to an XML file."""
        try:
            xml_content = self.generate_synth_xml(synth_name)
            
            with open(output_path, 'w', encoding=self.encoding) as f:
                f.write(xml_content)
                
            logger.info(f"Saved synth to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving synth: {e}")
            traceback.print_exc()
            return False


class DelugeFileSearcher:
    """Search for audio files in folder structures."""
    
    def __init__(self):
        self.supported_extensions = ['.wav', '.WAV', '.aiff', '.AIFF', '.aif', '.AIF', 
                                   '.flac', '.FLAC', '.mp3', '.MP3', '.m4a', '.M4A', 
                                   '.ogg', '.OGG']
    
    def find_audio_files(self, root_path: str, recursive: bool = True) -> Dict[str, List[str]]:
        """Find all audio files in directory structure."""
        results = defaultdict(list)
        root = Path(root_path)
        
        if not root.exists():
            logger.error(f"Path does not exist: {root_path}")
            return results
        
        # Search pattern based on recursive flag
        pattern = "**/*" if recursive else "*"
        
        for file_path in root.glob(pattern):
            if file_path.is_file() and file_path.suffix in self.supported_extensions:
                parent_dir = str(file_path.parent)
                results[parent_dir].append(str(file_path))
        
        return dict(results)
    
    def find_folders_with_audio(self, root_path: str, min_files: int = 1) -> List[Dict[str, Any]]:
        """Find folders containing audio files with metadata."""
        audio_files = self.find_audio_files(root_path)
        folders = []
        
        for folder, files in audio_files.items():
            if len(files) >= min_files:
                folder_info = {
                    'path': folder,
                    'file_count': len(files),
                    'files': files,
                    'folder_name': Path(folder).name,
                    'suggested_kit_name': self._suggest_kit_name(folder, files),
                    'has_drum_samples': self._detect_drum_samples(files)
                }
                folders.append(folder_info)
        
        return sorted(folders, key=lambda x: x['file_count'], reverse=True)
    
    def _suggest_kit_name(self, folder_path: str, files: List[str]) -> str:
        """Suggest a kit name based on folder and file names."""
        folder_name = Path(folder_path).name
        
        # Clean up common prefixes/suffixes
        cleaned = re.sub(r'\d+[-_]?', '', folder_name)  # Remove numbers
        cleaned = re.sub(r'[-_]+', ' ', cleaned)       # Replace separators with spaces
        cleaned = cleaned.strip().title()
        
        if not cleaned or len(cleaned) < 3:
            # Fall back to analyzing file names
            common_words = set()
            for file_path in files:
                name = Path(file_path).stem.lower()
                words = re.findall(r'[a-z]+', name)
                common_words.update(words)
            
            # Find most common meaningful words
            meaningful_words = [w for w in common_words if len(w) > 2 and w not in ['the', 'and', 'kit', 'drum']]
            if meaningful_words:
                cleaned = ' '.join(sorted(meaningful_words)[:2]).title()
            else:
                cleaned = f"Kit {folder_name}"
        
        return cleaned
    
    def _detect_drum_samples(self, files: List[str]) -> bool:
        """Detect if files contain drum samples based on naming."""
        drum_keywords = ['kick', 'snare', 'hihat', 'hat', 'crash', 'ride', 'tom', 
                        'clap', 'perc', 'cymbal', 'drum', 'beat']
        
        file_names = [Path(f).stem.lower() for f in files]
        
        # Count how many files have drum-related names
        drum_count = sum(1 for name in file_names 
                        if any(keyword in name for keyword in drum_keywords))
        
        # Consider it a drum kit if >30% of files have drum names
        return drum_count > len(files) * 0.3
    
    def find_kit_folders(self, root_dir: str, min_audio_files: int = 3) -> List[str]:
        """Find folders that contain multiple audio files (potential kits)."""
        kit_folders = []
        root_path = Path(root_dir)
        
        if not root_path.exists():
            return kit_folders
        
        for folder in root_path.rglob('*'):
            if folder.is_dir():
                # Count audio files in this folder
                audio_count = 0
                for ext in self.supported_extensions:
                    pattern = f"*{ext}"
                    audio_count += len(list(folder.glob(pattern)))
                
                # If folder has enough audio files, consider it a kit folder
                if audio_count >= min_audio_files:
                    kit_folders.append(str(folder))
        
        return sorted(kit_folders)


class MPCToDelugeConverter:
    """Convert MPC XPM files to Deluge format."""
    
    def __init__(self):
        self.drum_handler = DelugeDrumKitHandler()
        self.synth_handler = DelugeSynthHandler()
    
    def convert_xpm_to_deluge(self, xpm_path: str, output_dir: str) -> Dict[str, Any]:
        """Convert XPM file to Deluge kit or synth."""
        result = {
            'success': False,
            'output_files': [],
            'errors': [],
            'type': None
        }
        
        if not XPM_UTILS_AVAILABLE:
            result['errors'].append("XPM utilities not available - cannot convert MPC files")
            return result
        
        try:
            # Parse XPM file
            mappings, instrument_params = _parse_xpm_for_rebuild(xpm_path)
            
            if not mappings:
                result['errors'].append("No sample mappings found in XPM file")
                return result
            
            # Determine if it's a drum kit or instrument based on mappings
            is_drum_kit = self._is_drum_kit(mappings, instrument_params)
            
            if is_drum_kit:
                result.update(self._convert_to_drum_kit(xpm_path, mappings, instrument_params, output_dir))
                result['type'] = 'drum_kit'
            else:
                result.update(self._convert_to_synth(xpm_path, mappings, instrument_params, output_dir))
                result['type'] = 'synth'
            
        except Exception as e:
            logger.error(f"Error converting XPM file: {e}")
            result['errors'].append(str(e))
        
        return result
    
    def _is_drum_kit(self, mappings: List[Dict], instrument_params: Dict) -> bool:
        """Determine if XPM represents a drum kit or melodic instrument."""
        # Check for typical drum characteristics
        note_ranges = []
        
        for mapping in mappings:
            low_note = mapping.get('low_note', mapping.get('root_note', 60))
            high_note = mapping.get('high_note', low_note)
            note_ranges.append((low_note, high_note))
        
        # Drum kits typically have:
        # 1. Single-note mappings (low_note == high_note)
        # 2. Notes in the drum range (typically 35-81)
        # 3. Multiple discrete samples rather than chromatic mapping
        
        single_note_mappings = sum(1 for low, high in note_ranges if low == high)
        drum_range_notes = sum(1 for low, high in note_ranges if 35 <= low <= 81)
        
        is_drum = (single_note_mappings > len(note_ranges) * 0.7 and 
                  drum_range_notes > len(note_ranges) * 0.5)
        
        return is_drum
    
    def _convert_to_drum_kit(self, xmp_path: str, mappings: List[Dict], 
                           params: Dict, output_dir: str) -> Dict[str, Any]:
        """Convert XPM to Deluge drum kit."""
        self.drum_handler.create_empty_kit()
        
        # Map samples to drum pads
        pad_index = 0
        output_files = []
        
        for mapping in mappings:
            if pad_index >= MAX_DRUM_PADS:
                break
                
            sample_path = mapping.get('sample_path', '')
            if sample_path and os.path.exists(sample_path):
                # Convert sample to WAV if needed
                converter = AudioConverter()
                wav_path = converter.convert_to_wav(sample_path)
                
                if wav_path:
                    # Add to drum pad
                    success = self.drum_handler.add_sample_to_pad(pad_index, wav_path)
                    if success:
                        # Set up pad name based on original mapping
                        pad_name = self._extract_pad_name(sample_path, mapping)
                        self.drum_handler.pads[pad_index].name = pad_name
                        pad_index += 1
        
        # Save the kit
        kit_name = Path(xmp_path).stem
        output_path = Path(output_dir) / f"{kit_name}.xml"
        
        if self.drum_handler.save_kit(str(output_path), kit_name):
            output_files.append(str(output_path))
            return {'success': True, 'output_files': output_files, 'errors': []}
        else:
            return {'success': False, 'output_files': [], 'errors': ['Failed to save drum kit']}
    
    def _convert_to_synth(self, xmp_path: str, mappings: List[Dict], 
                        params: Dict, output_dir: str) -> Dict[str, Any]:
        """Convert XPM to Deluge synth instrument.""" 
        self.synth_handler.create_subtractive_synth()
        
        # For now, use the first sample as a wavetable source
        # Future enhancement: create multi-sample ranges
        if mappings:
            first_mapping = mappings[0]
            sample_path = first_mapping.get('sample_path', '')
            
            if sample_path and os.path.exists(sample_path):
                converter = AudioConverter()
                wav_path = converter.convert_to_wav(sample_path)
                
                if wav_path:
                    self.synth_handler.add_sample_based_osc(wav_path, 1)
        
        # Apply any parameters from the original XPM
        self._apply_xpm_params_to_synth(params)
        
        # Save the synth
        synth_name = Path(xmp_path).stem
        output_path = Path(output_dir) / f"{synth_name}.xml"
        
        if self.synth_handler.save_synth(str(output_path), synth_name):
            return {'success': True, 'output_files': [str(output_path)], 'errors': []}
        else:
            return {'success': False, 'output_files': [], 'errors': ['Failed to save synth']}
    
    def _extract_pad_name(self, sample_path: str, mapping: Dict) -> str:
        """Extract a meaningful pad name from sample path and mapping info."""
        # Try to get name from the sample file
        name = Path(sample_path).stem
        
        # Clean up the name
        name = re.sub(r'[_-]+', ' ', name)
        name = re.sub(r'\d+', '', name).strip()
        
        # Capitalize and limit length
        name = name.upper()[:8] if name else f"PAD{mapping.get('root_note', 60)}"
        
        return name
    
    def _apply_xpm_params_to_synth(self, params: Dict) -> None:
        """Apply XPM parameters to Deluge synth where possible."""
        synth_params = self.synth_handler.synth_params
        
        # Map volume parameters
        if 'Volume' in params:
            try:
                volume = float(params['Volume'])
                # Convert XPM volume to Deluge range
                synth_params.osc1_volume = max(-50.0, min(50.0, volume))
            except ValueError:
                pass
        
        # Map filter parameters
        if 'FilterFrequency' in params:
            try:
                freq = float(params['FilterFrequency'])
                # Convert to Deluge's 0-50 range
                synth_params.lpf_frequency = max(0.0, min(50.0, freq / 2.0))
            except ValueError:
                pass
    
    def find_mpc_files(self, root_dir: str) -> List[str]:
        """Find MPC program/keygroup files in directory."""
        mpc_files = []
        root_path = Path(root_dir)
        
        if not root_path.exists():
            return mpc_files
        
        # Look for common MPC file patterns
        patterns = ['*.xpm', '*.XPM', '*.pgm', '*.PGM', '*.keygroup', '*.KEYGROUP']
        
        for pattern in patterns:
            mpc_files.extend(str(f) for f in root_path.rglob(pattern))
        
        return sorted(mpc_files)
    
    def detect_mpc_file_type(self, file_path: str) -> str:
        """Detect the type of MPC file."""
        file_path = Path(file_path)
        ext = file_path.suffix.lower()
        
        if ext in ['.xpm']:
            return 'xpm_program'
        elif ext in ['.pgm']:
            return 'mpc_program'
        elif 'keygroup' in ext:
            return 'keygroup'
        else:
            # Try to determine from file name or content
            name = file_path.name.lower()
            if 'keygroup' in name or 'key' in name:
                return 'keygroup'
            elif 'program' in name or 'pgm' in name:
                return 'program'
            else:
                return 'unknown'
    
    def convert_to_deluge(self, mpc_file_path: str, output_path: str, **options) -> bool:
        """Convert MPC file to Deluge format."""
        try:
            file_type = self.detect_mpc_file_type(mpc_file_path)
            
            if file_type == 'xpm_program':
                return self._convert_xpm_file(mpc_file_path, output_path, **options)
            elif file_type in ['mpc_program', 'program']:
                return self._convert_pgm_file(mpc_file_path, output_path, **options)
            elif file_type == 'keygroup':
                return self._convert_keygroup_file(mpc_file_path, output_path, **options)
            else:
                logger.warning(f"Unknown file type: {file_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error converting {mpc_file_path}: {e}")
            return False
    
    def _convert_xpm_file(self, xpm_path: str, output_path: str, **options) -> bool:
        """Convert XPM file using existing conversion logic."""
        result = self.convert_xpm_to_deluge(xpm_path, str(Path(output_path).parent))
        return result['success']
    
    def _convert_pgm_file(self, pgm_path: str, output_path: str, **options) -> bool:
        """Convert MPC PGM file (placeholder implementation)."""
        logger.warning(f"PGM file conversion not yet implemented: {pgm_path}")
        return False
    
    def _convert_keygroup_file(self, keygroup_path: str, output_path: str, **options) -> bool:
        """Convert MPC keygroup file (placeholder implementation)."""
        logger.warning(f"Keygroup file conversion not yet implemented: {keygroup_path}")
        return False


class AudioConverter:
    """Audio conversion utilities adapted from XPM converter."""
    
    @staticmethod
    def convert_to_wav(input_path: str, output_path: str = None) -> str:
        """Convert audio file to WAV format for Deluge compatibility."""
        if output_path is None:
            output_path = str(Path(input_path).with_suffix('.wav'))
        
        input_ext = Path(input_path).suffix.lower()
        
        # If already WAV, just copy
        if input_ext == '.wav':
            if input_path != output_path:
                shutil.copy2(input_path, output_path)
            return output_path
        
        # Try soundfile first (preferred)
        if SOUNDFILE_AVAILABLE:
            try:
                data, samplerate = sf.read(input_path)
                sf.write(output_path, data, samplerate, subtype='PCM_16')
                logger.info(f"Converted {input_path} to WAV using soundfile")
                return output_path
            except Exception as e:
                logger.warning(f"Soundfile conversion failed: {e}")
        
        # Try librosa as fallback
        if LIBROSA_AVAILABLE:
            try:
                y, sr = librosa.load(input_path, sr=DELUGE_SAMPLE_RATE, mono=False)
                if y.ndim > 1:
                    y = y.T  # Transpose for multi-channel
                sf.write(output_path, y, sr) if SOUNDFILE_AVAILABLE else None
                logger.info(f"Converted {input_path} to WAV using librosa")
                return output_path
            except Exception as e:
                logger.warning(f"Librosa conversion failed: {e}")
        
        logger.error(f"Could not convert {input_path} - no suitable audio library available")
        return ""
    
    @staticmethod
    def validate_audio_file(file_path: str) -> dict:
        """Validate audio file and return information."""
        info = {
            'valid': False,
            'sample_rate': 0,
            'channels': 0,
            'duration': 0.0,
            'format': '',
            'bit_depth': 0
        }
        
        try:
            # Try with wave module first (for WAV files)
            if file_path.lower().endswith('.wav'):
                with wave.open(file_path, 'rb') as wav_file:
                    info['sample_rate'] = wav_file.getframerate()
                    info['channels'] = wav_file.getnchannels()
                    info['duration'] = wav_file.getnframes() / wav_file.getframerate()
                    info['format'] = 'WAV'
                    info['bit_depth'] = wav_file.getsampwidth() * 8
                    info['valid'] = True
            
            # Try with soundfile for other formats
            elif SOUNDFILE_AVAILABLE:
                sf_info = sf.info(file_path)
                info['sample_rate'] = sf_info.samplerate
                info['channels'] = sf_info.channels
                info['duration'] = sf_info.duration
                info['format'] = sf_info.format
                info['bit_depth'] = sf_info.subtype.split('_')[-1] if '_' in sf_info.subtype else '16'
                info['valid'] = True
                
        except Exception as e:
            logger.error(f"Error validating audio file {file_path}: {e}")
        
        return info


# The main application class will be implemented in the next part
class DelugeManagerGUI:
    """Main GUI application for managing Deluge files."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Deluge Synth File Manager")
        self.root.geometry("1000x700")
        
        self.drum_handler = DelugeDrumKitHandler()
        self.synth_handler = DelugeSynthHandler()
        self.converter = AudioConverter()
        self.file_searcher = DelugeFileSearcher()
        self.mpc_converter = MPCToDelugeConverter()
        
        self.create_gui()
    
    def create_gui(self):
        """Create the main GUI interface."""
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Drum Kit tab
        self.drum_frame = ttk.Frame(notebook)
        notebook.add(self.drum_frame, text="Drum Kits")
        self.create_drum_tab()
        
        # Synth tab
        self.synth_frame = ttk.Frame(notebook)
        notebook.add(self.synth_frame, text="Synth Instruments")
        self.create_synth_tab()
        
        # File Search tab
        self.search_frame = ttk.Frame(notebook)
        notebook.add(self.search_frame, text="File Search")
        self.create_search_tab()
        
        # MPC Converter tab
        self.mpc_frame = ttk.Frame(notebook)
        notebook.add(self.mpc_frame, text="MPC Converter")
        self.create_mpc_tab()
        
        # Utilities tab
        self.utils_frame = ttk.Frame(notebook)
        notebook.add(self.utils_frame, text="Utilities")
        self.create_utils_tab()
    
    def create_drum_tab(self):
        """Create the drum kit management interface."""
        # Title
        title_label = ttk.Label(self.drum_frame, text="Deluge Drum Kit Manager", 
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=(10, 20))
        
        # Buttons frame
        buttons_frame = ttk.Frame(self.drum_frame)
        buttons_frame.pack(pady=10)
        
        ttk.Button(buttons_frame, text="Create New Kit", 
                  command=self.create_new_drum_kit).pack(side='left', padx=5)
        ttk.Button(buttons_frame, text="Load Existing Kit", 
                  command=self.load_drum_kit).pack(side='left', padx=5)
        ttk.Button(buttons_frame, text="Add Samples to Kit", 
                  command=self.add_samples_to_kit).pack(side='left', padx=5)
        ttk.Button(buttons_frame, text="Save Kit", 
                  command=self.save_drum_kit).pack(side='left', padx=5)
        
        # Kit info frame
        info_frame = ttk.LabelFrame(self.drum_frame, text="Kit Information")
        info_frame.pack(fill='x', padx=20, pady=10)
        
        self.kit_info_text = tk.Text(info_frame, height=15, width=80)
        scrollbar_kit = ttk.Scrollbar(info_frame, orient='vertical', command=self.kit_info_text.yview)
        self.kit_info_text.configure(yscrollcommand=scrollbar_kit.set)
        
        self.kit_info_text.pack(side='left', fill='both', expand=True)
        scrollbar_kit.pack(side='right', fill='y')
        
    def create_synth_tab(self):
        """Create the synth instrument management interface.""" 
        # Title
        title_label = ttk.Label(self.synth_frame, text="Deluge Synth Instrument Manager", 
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=(10, 20))
        
        # Buttons frame
        buttons_frame = ttk.Frame(self.synth_frame)
        buttons_frame.pack(pady=10)
        
        ttk.Button(buttons_frame, text="Create Subtractive Synth", 
                  command=self.create_subtractive_synth).pack(side='left', padx=5)
        ttk.Button(buttons_frame, text="Create Sample-Based Synth", 
                  command=self.create_sample_synth).pack(side='left', padx=5)
        ttk.Button(buttons_frame, text="Load Existing Synth", 
                  command=self.load_synth).pack(side='left', padx=5)
        ttk.Button(buttons_frame, text="Save Synth", 
                  command=self.save_synth).pack(side='left', padx=5)
        
        # Synth parameters frame
        params_frame = ttk.LabelFrame(self.synth_frame, text="Synth Parameters")
        params_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # We'll add parameter controls here later
        self.synth_params_text = tk.Text(params_frame, height=15, width=80)
        scrollbar_synth = ttk.Scrollbar(params_frame, orient='vertical', command=self.synth_params_text.yview)
        self.synth_params_text.configure(yscrollcommand=scrollbar_synth.set)
        
        self.synth_params_text.pack(side='left', fill='both', expand=True)
        scrollbar_synth.pack(side='right', fill='y')
    
    def create_utils_tab(self):
        """Create the utilities interface."""
        # Title
        title_label = ttk.Label(self.utils_frame, text="Deluge File Utilities", 
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=(10, 20))
        
        # Buttons frame
        buttons_frame = ttk.Frame(self.utils_frame)
        buttons_frame.pack(pady=10)
        
        ttk.Button(buttons_frame, text="Convert Audio Files", 
                  command=self.convert_audio_files).pack(side='left', padx=5)
        ttk.Button(buttons_frame, text="Validate Deluge Files", 
                  command=self.validate_deluge_files).pack(side='left', padx=5)
        ttk.Button(buttons_frame, text="Organize File Structure", 
                  command=self.organize_files).pack(side='left', padx=5)
        
        # Log frame
        log_frame = ttk.LabelFrame(self.utils_frame, text="Activity Log")
        log_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        self.log_text = tk.Text(log_frame, height=15, width=80)
        scrollbar_log = ttk.Scrollbar(log_frame, orient='vertical', command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar_log.set)
        
        self.log_text.pack(side='left', fill='both', expand=True)
        scrollbar_log.pack(side='right', fill='y')
    
    # GUI Event Handlers (placeholder implementations)
    def create_new_drum_kit(self):
        """Create a new empty drum kit."""
        self.drum_handler.create_empty_kit()
        self.update_kit_info()
        self.log_message("Created new empty drum kit")
    
    def load_drum_kit(self):
        """Load an existing drum kit file."""
        file_path = filedialog.askopenfilename(
            title="Select Deluge drum kit file",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        
        if file_path:
            if self.drum_handler.load_kit(file_path):
                self.update_kit_info()
                self.log_message(f"Loaded drum kit: {file_path}")
            else:
                messagebox.showerror("Error", "Failed to load drum kit file")
    
    def add_samples_to_kit(self):
        """Add samples to the current drum kit."""
        sample_files = filedialog.askopenfilenames(
            title="Select sample files",
            filetypes=[("Audio files", "*.wav *.aiff *.flac"), ("All files", "*.*")]
        )
        
        if sample_files:
            # Simple dialog to assign samples to pads
            self.show_sample_assignment_dialog(sample_files)
    
    def save_drum_kit(self):
        """Save the current drum kit."""
        file_path = filedialog.asksaveasfilename(
            title="Save drum kit as",
            defaultextension=".xml",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        
        if file_path:
            kit_name = Path(file_path).stem
            if self.drum_handler.save_kit(file_path, kit_name):
                self.log_message(f"Saved drum kit: {file_path}")
            else:
                messagebox.showerror("Error", "Failed to save drum kit")
    
    def show_sample_assignment_dialog(self, sample_files):
        """Show dialog for assigning samples to pads.""" 
        dialog = tk.Toplevel(self.root)
        dialog.title("Assign Samples to Pads")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Assign samples to drum pads:").pack(pady=10)
        
        # Create assignment interface
        frame = ttk.Frame(dialog)
        frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        assignments = {}
        
        for i, sample_file in enumerate(sample_files):
            sample_name = Path(sample_file).name
            
            row_frame = ttk.Frame(frame)
            row_frame.pack(fill='x', pady=2)
            
            ttk.Label(row_frame, text=sample_name[:30]).pack(side='left')
            
            pad_var = tk.StringVar(value=str(i % MAX_DRUM_PADS))
            pad_combo = ttk.Combobox(row_frame, textvariable=pad_var, 
                                   values=[str(x) for x in range(MAX_DRUM_PADS)],
                                   width=10)
            pad_combo.pack(side='right')
            
            assignments[sample_file] = pad_var
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)
        
        def confirm_assignment():
            for sample_file, pad_var in assignments.items():
                try:
                    pad_index = int(pad_var.get())
                    self.drum_handler.add_sample_to_pad(pad_index, sample_file)
                except ValueError:
                    continue
            
            self.update_kit_info()
            self.log_message(f"Added {len(sample_files)} samples to kit")
            dialog.destroy()
        
        ttk.Button(button_frame, text="Assign", command=confirm_assignment).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side='left', padx=5)
        
    # Additional placeholder methods
    def create_subtractive_synth(self):
        self.synth_handler.create_subtractive_synth()
        self.update_synth_info()
        self.log_message("Created new subtractive synth")
    
    def create_sample_synth(self):
        sample_file = filedialog.askopenfilename(
            title="Select sample for synth oscillator",
            filetypes=[("Audio files", "*.wav *.aiff *.flac"), ("All files", "*.*")]
        )
        
        if sample_file:
            self.synth_handler.create_subtractive_synth()  # Start with basic synth
            self.synth_handler.add_sample_based_osc(sample_file, 1)
            self.update_synth_info()
            self.log_message(f"Created sample-based synth with: {sample_file}")
    
    def load_synth(self):
        self.log_message("Load synth functionality to be implemented")
    
    def save_synth(self):
        file_path = filedialog.asksaveasfilename(
            title="Save synth as",
            defaultextension=".xml",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        
        if file_path:
            synth_name = Path(file_path).stem
            if self.synth_handler.save_synth(file_path, synth_name):
                self.log_message(f"Saved synth: {file_path}")
            else:
                messagebox.showerror("Error", "Failed to save synth")
    
    def convert_audio_files(self):
        files = filedialog.askopenfilenames(
            title="Select audio files to convert",
            filetypes=[("Audio files", "*.mp3 *.m4a *.ogg *.flac *.aiff"), ("All files", "*.*")]
        )
        
        if files:
            output_dir = filedialog.askdirectory(title="Select output directory")
            if output_dir:
                converted_count = 0
                for file_path in files:
                    output_path = Path(output_dir) / f"{Path(file_path).stem}.wav"
                    if self.converter.convert_to_wav(file_path, str(output_path)):
                        converted_count += 1
                
                self.log_message(f"Converted {converted_count} audio files")
    
    def validate_deluge_files(self):
        self.log_message("File validation functionality to be implemented")
    
    def organize_files(self):
        self.log_message("File organization functionality to be implemented")
    
    def update_kit_info(self):
        """Update the drum kit information display."""
        info_text = "Drum Kit Information:\n\n"
        
        for pad_index in sorted(self.drum_handler.pads.keys()):
            pad = self.drum_handler.pads[pad_index]
            info_text += f"Pad {pad_index}: {len(pad.samples)} sample(s)\n"
            
            for i, sample in enumerate(pad.samples):
                sample_name = Path(sample.file_path).name
                velocity_range = pad.velocity_layers[i] if i < len(pad.velocity_layers) else (0, 127)
                info_text += f"  - {sample_name} (vel: {velocity_range[0]}-{velocity_range[1]})\n"
            
            info_text += "\n"
        
        self.kit_info_text.delete('1.0', tk.END)
        self.kit_info_text.insert('1.0', info_text)
    
    def update_synth_info(self):
        """Update the synth information display."""
        params = self.synth_handler.synth_params
        info_text = f"Synth Parameters:\n\n"
        info_text += f"OSC1: {params.osc1_type} (vol: {params.osc1_volume}, transpose: {params.osc1_transpose})\n"
        info_text += f"OSC2: {params.osc2_type} (vol: {params.osc2_volume}, transpose: {params.osc2_transpose})\n"
        info_text += f"Filter: LPF @ {params.lpf_frequency} (res: {params.lpf_resonance})\n"
        info_text += f"Envelope: A:{params.env1_attack} D:{params.env1_decay} S:{params.env1_sustain} R:{params.env1_release}\n"
        info_text += f"Effects: Reverb:{params.reverb_amount} Delay:{params.delay_amount}\n\n"
        
        if self.synth_handler.samples:
            info_text += "Sample-based oscillators:\n"
            for i, sample in enumerate(self.synth_handler.samples):
                info_text += f"  - {Path(sample.file_path).name}\n"
        
        self.synth_params_text.delete('1.0', tk.END)
        self.synth_params_text.insert('1.0', info_text)
    
    def log_message(self, message: str):
        """Add a message to the activity log."""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
    
    def create_search_tab(self):
        """Create the file search interface."""
        # Title
        title_label = ttk.Label(self.search_frame, text="Deluge File Search & Batch Processing", 
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=(10, 20))
        
        # Search input frame
        search_frame = ttk.LabelFrame(self.search_frame, text="Search Parameters")
        search_frame.pack(fill='x', padx=20, pady=10)
        
        # Root directory selection
        dir_frame = ttk.Frame(search_frame)
        dir_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(dir_frame, text="Search Root Directory:").pack(side='left')
        self.search_dir_var = tk.StringVar()
        ttk.Entry(dir_frame, textvariable=self.search_dir_var, width=50).pack(side='left', padx=5)
        ttk.Button(dir_frame, text="Browse", command=self.browse_search_dir).pack(side='left', padx=5)
        
        # File type selection
        type_frame = ttk.Frame(search_frame)
        type_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(type_frame, text="File Types:").pack(side='left')
        self.search_wav = tk.BooleanVar(value=True)
        self.search_aiff = tk.BooleanVar(value=True)
        self.search_flac = tk.BooleanVar(value=True)
        ttk.Checkbutton(type_frame, text="WAV", variable=self.search_wav).pack(side='left', padx=5)
        ttk.Checkbutton(type_frame, text="AIFF", variable=self.search_aiff).pack(side='left', padx=5)
        ttk.Checkbutton(type_frame, text="FLAC", variable=self.search_flac).pack(side='left', padx=5)
        
        # Search controls
        control_frame = ttk.Frame(search_frame)
        control_frame.pack(fill='x', padx=10, pady=10)
        ttk.Button(control_frame, text="Search for Audio Files", 
                  command=self.search_audio_files).pack(side='left', padx=5)
        ttk.Button(control_frame, text="Find Kit Folders", 
                  command=self.find_kit_folders).pack(side='left', padx=5)
        
        # Results frame
        results_frame = ttk.LabelFrame(self.search_frame, text="Search Results")
        results_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Results listbox
        self.search_results = tk.Listbox(results_frame, height=15)
        scrollbar_results = ttk.Scrollbar(results_frame, orient='vertical', command=self.search_results.yview)
        self.search_results.configure(yscrollcommand=scrollbar_results.set)
        
        self.search_results.pack(side='left', fill='both', expand=True)
        scrollbar_results.pack(side='right', fill='y')
        
        # Batch operations frame
        batch_frame = ttk.LabelFrame(self.search_frame, text="Batch Operations")
        batch_frame.pack(fill='x', padx=20, pady=10)
        
        batch_buttons = ttk.Frame(batch_frame)
        batch_buttons.pack(fill='x', padx=10, pady=10)
        ttk.Button(batch_buttons, text="Create Kit from Selected", 
                  command=self.create_kit_from_selected).pack(side='left', padx=5)
        ttk.Button(batch_buttons, text="Convert Selected to WAV", 
                  command=self.convert_selected_to_wav).pack(side='left', padx=5)
        
    def create_mpc_tab(self):
        """Create the MPC converter interface."""
        # Title
        title_label = ttk.Label(self.mpc_frame, text="MPC to Deluge Converter", 
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=(10, 20))
        
        # Source selection frame
        source_frame = ttk.LabelFrame(self.mpc_frame, text="MPC Source Files")
        source_frame.pack(fill='x', padx=20, pady=10)
        
        # MPC file selection
        mpc_dir_frame = ttk.Frame(source_frame)
        mpc_dir_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(mpc_dir_frame, text="MPC Programs/Keygroups Directory:").pack(side='left')
        self.mpc_dir_var = tk.StringVar()
        ttk.Entry(mpc_dir_frame, textvariable=self.mpc_dir_var, width=50).pack(side='left', padx=5)
        ttk.Button(mpc_dir_frame, text="Browse", command=self.browse_mpc_dir).pack(side='left', padx=5)
        
        # Conversion options frame
        options_frame = ttk.LabelFrame(self.mpc_frame, text="Conversion Options")
        options_frame.pack(fill='x', padx=20, pady=10)
        
        # Options checkboxes
        option_checkboxes = ttk.Frame(options_frame)
        option_checkboxes.pack(fill='x', padx=10, pady=10)
        
        self.convert_samples = tk.BooleanVar(value=True)
        self.preserve_velocity = tk.BooleanVar(value=True)
        self.auto_tune = tk.BooleanVar(value=True)
        self.organize_output = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(option_checkboxes, text="Convert Samples to WAV", 
                       variable=self.convert_samples).pack(anchor='w')
        ttk.Checkbutton(option_checkboxes, text="Preserve Velocity Mapping", 
                       variable=self.preserve_velocity).pack(anchor='w')
        ttk.Checkbutton(option_checkboxes, text="Auto-tune Detection", 
                       variable=self.auto_tune).pack(anchor='w')
        ttk.Checkbutton(option_checkboxes, text="Organize Output Structure", 
                       variable=self.organize_output).pack(anchor='w')
        
        # Output directory selection
        output_frame = ttk.Frame(source_frame)
        output_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(output_frame, text="Output Directory:").pack(side='left')
        self.output_dir_var = tk.StringVar()
        ttk.Entry(output_frame, textvariable=self.output_dir_var, width=50).pack(side='left', padx=5)
        ttk.Button(output_frame, text="Browse", command=self.browse_output_dir).pack(side='left', padx=5)
        
        # Conversion controls
        convert_control_frame = ttk.Frame(options_frame)
        convert_control_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(convert_control_frame, text="Scan MPC Files", 
                  command=self.scan_mpc_files).pack(side='left', padx=5)
        ttk.Button(convert_control_frame, text="Convert Selected", 
                  command=self.convert_mpc_files).pack(side='left', padx=5)
        ttk.Button(convert_control_frame, text="Convert All", 
                  command=self.convert_all_mpc_files).pack(side='left', padx=5)
        
        # MPC files list frame
        mpc_list_frame = ttk.LabelFrame(self.mpc_frame, text="MPC Files Found")
        mpc_list_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # MPC files listbox with checkboxes simulation
        self.mpc_files_listbox = tk.Listbox(mpc_list_frame, height=10, selectmode=tk.EXTENDED)
        scrollbar_mpc = ttk.Scrollbar(mpc_list_frame, orient='vertical', command=self.mpc_files_listbox.yview)
        self.mpc_files_listbox.configure(yscrollcommand=scrollbar_mpc.set)
        
        self.mpc_files_listbox.pack(side='left', fill='both', expand=True)
        scrollbar_mpc.pack(side='right', fill='y')

    # Search tab event handlers
    def browse_search_dir(self):
        """Browse for search root directory."""
        directory = filedialog.askdirectory(title="Select directory to search for audio files")
        if directory:
            self.search_dir_var.set(directory)
    
    def search_audio_files(self):
        """Search for audio files in the selected directory."""
        if not self.search_dir_var.get():
            messagebox.showwarning("Warning", "Please select a search directory first")
            return
        
        self.log_message(f"Searching for audio files in: {self.search_dir_var.get()}")
        
        # Use the file searcher
        audio_files_dict = self.file_searcher.find_audio_files(self.search_dir_var.get())
        
        # Flatten the dictionary to get all files
        all_files = []
        for folder, files in audio_files_dict.items():
            all_files.extend(files)
        
        # Filter by selected extensions
        filtered_files = []
        for file_path in all_files:
            ext = Path(file_path).suffix.lower()
            if (self.search_wav.get() and ext in ['.wav']) or \
               (self.search_aiff.get() and ext in ['.aiff', '.aif']) or \
               (self.search_flac.get() and ext in ['.flac']):
                filtered_files.append(file_path)
        
        # Update results listbox
        self.search_results.delete(0, tk.END)
        for file_path in sorted(filtered_files):
            self.search_results.insert(tk.END, file_path)
        
        self.log_message(f"Found {len(filtered_files)} audio files")
    
    def find_kit_folders(self):
        """Find folders that look like drum kit collections."""
        if not self.search_dir_var.get():
            messagebox.showwarning("Warning", "Please select a search directory first")
            return
        
        self.log_message(f"Searching for kit folders in: {self.search_dir_var.get()}")
        
        kit_folders = self.file_searcher.find_kit_folders(self.search_dir_var.get())
        
        # Update results listbox
        self.search_results.delete(0, tk.END)
        for folder in kit_folders:
            self.search_results.insert(tk.END, f"[FOLDER] {folder}")
        
        self.log_message(f"Found {len(kit_folders)} potential kit folders")
    
    def create_kit_from_selected(self):
        """Create a Deluge kit from selected audio files."""
        selection = self.search_results.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select audio files first")
            return
        
        selected_files = [self.search_results.get(i) for i in selection]
        # Filter out folders
        audio_files = [f for f in selected_files if not f.startswith("[FOLDER]")]
        
        if not audio_files:
            messagebox.showwarning("Warning", "No audio files selected")
            return
        
        # Create new kit and add samples
        self.drum_handler.create_empty_kit()
        
        for i, file_path in enumerate(audio_files[:16]):  # Max 16 pads
            if Path(file_path).exists():
                self.drum_handler.add_sample_to_pad(i, file_path)
        
        self.update_kit_info()
        self.log_message(f"Created kit from {len(audio_files)} files")
    
    def convert_selected_to_wav(self):
        """Convert selected files to WAV format."""
        selection = self.search_results.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select files first")
            return
        
        output_dir = filedialog.askdirectory(title="Select output directory for WAV files")
        if not output_dir:
            return
        
        selected_files = [self.search_results.get(i) for i in selection]
        # Filter out folders
        audio_files = [f for f in selected_files if not f.startswith("[FOLDER]")]
        
        converted_count = 0
        for file_path in audio_files:
            if Path(file_path).exists():
                output_path = Path(output_dir) / f"{Path(file_path).stem}.wav"
                if self.converter.convert_to_wav(file_path, str(output_path)):
                    converted_count += 1
        
        self.log_message(f"Converted {converted_count}/{len(audio_files)} files to WAV")
    
    # MPC tab event handlers
    def browse_mpc_dir(self):
        """Browse for MPC files directory."""
        directory = filedialog.askdirectory(title="Select directory containing MPC programs/keygroups")
        if directory:
            self.mpc_dir_var.set(directory)
    
    def browse_output_dir(self):
        """Browse for output directory."""
        directory = filedialog.askdirectory(title="Select output directory for Deluge files")
        if directory:
            self.output_dir_var.set(directory)
    
    def scan_mpc_files(self):
        """Scan for MPC files in the selected directory."""
        if not self.mpc_dir_var.get():
            messagebox.showwarning("Warning", "Please select MPC files directory first")
            return
        
        self.log_message(f"Scanning for MPC files in: {self.mpc_dir_var.get()}")
        
        mpc_files = self.mpc_converter.find_mpc_files(self.mpc_dir_var.get())
        
        # Update MPC files listbox
        self.mpc_files_listbox.delete(0, tk.END)
        for file_path in mpc_files:
            file_type = self.mpc_converter.detect_mpc_file_type(file_path)
            display_name = f"[{file_type.upper()}] {Path(file_path).name}"
            self.mpc_files_listbox.insert(tk.END, display_name)
        
        # Store the actual paths for conversion
        self.mpc_file_paths = mpc_files
        
        self.log_message(f"Found {len(mpc_files)} MPC files")
    
    def convert_mpc_files(self):
        """Convert selected MPC files to Deluge format."""
        if not hasattr(self, 'mpc_file_paths'):
            messagebox.showwarning("Warning", "Please scan for MPC files first")
            return
        
        selection = self.mpc_files_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select MPC files to convert")
            return
        
        if not self.output_dir_var.get():
            messagebox.showwarning("Warning", "Please select output directory")
            return
        
        selected_files = [self.mpc_file_paths[i] for i in selection]
        
        conversion_options = {
            'convert_samples': self.convert_samples.get(),
            'preserve_velocity': self.preserve_velocity.get(),
            'auto_tune': self.auto_tune.get(),
            'organize_output': self.organize_output.get()
        }
        
        converted_count = 0
        for file_path in selected_files:
            try:
                output_path = Path(self.output_dir_var.get()) / Path(file_path).stem
                if self.mpc_converter.convert_to_deluge(file_path, str(output_path), **conversion_options):
                    converted_count += 1
                    self.log_message(f"Converted: {Path(file_path).name}")
            except Exception as e:
                self.log_message(f"Failed to convert {Path(file_path).name}: {e}")
        
        self.log_message(f"Conversion complete: {converted_count}/{len(selected_files)} files converted")
    
    def convert_all_mpc_files(self):
        """Convert all found MPC files to Deluge format."""
        if not hasattr(self, 'mpc_file_paths'):
            messagebox.showwarning("Warning", "Please scan for MPC files first")
            return
        
        if not self.output_dir_var.get():
            messagebox.showwarning("Warning", "Please select output directory")
            return
        
        # Confirm with user
        if not messagebox.askyesno("Confirm", f"Convert all {len(self.mpc_file_paths)} MPC files?"):
            return
        
        conversion_options = {
            'convert_samples': self.convert_samples.get(),
            'preserve_velocity': self.preserve_velocity.get(),
            'auto_tune': self.auto_tune.get(),
            'organize_output': self.organize_output.get()
        }
        
        converted_count = 0
        for file_path in self.mpc_file_paths:
            try:
                output_path = Path(self.output_dir_var.get()) / Path(file_path).stem
                if self.mpc_converter.convert_to_deluge(file_path, str(output_path), **conversion_options):
                    converted_count += 1
                    self.log_message(f"Converted: {Path(file_path).name}")
            except Exception as e:
                self.log_message(f"Failed to convert {Path(file_path).name}: {e}")
        
        self.log_message(f"Batch conversion complete: {converted_count}/{len(self.mpc_file_paths)} files converted")

    def run(self):
        """Start the GUI application."""
        self.root.mainloop()


def main():
    """Main entry point for the application."""
    print("🎵 Deluge Synth File Manager")
    print("=" * 40)
    print("Initializing application...")
    
    # Check for optional dependencies
    if SOUNDFILE_AVAILABLE:
        print("✓ SoundFile library available")
    else:
        print("⚠ SoundFile not available - limited audio conversion")
    
    if LIBROSA_AVAILABLE:
        print("✓ Librosa library available")
    else:
        print("⚠ Librosa not available - basic audio analysis only")
    
    # Launch GUI
    app = DelugeManagerGUI()
    app.run()


if __name__ == "__main__":
    main()