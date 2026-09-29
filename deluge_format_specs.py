#!/usr/bin/env python3
"""
Deluge File Format Specifications and Templates

This file contains detailed specifications for Deluge XML file formats,
example templates, and validation schemas.
"""

# Example Deluge Drum Kit XML Template
DELUGE_DRUM_KIT_TEMPLATE = '''<?xml version="1.0" encoding="utf-8"?>
<drumKit drumKitVersion="4.1.4" earliestCompatibleFirmware="4.1.0">
    <lpfFrequency>50</lpfFrequency>
    <hpfFrequency>0</hpfFrequency>
    <reverbAmount>0x80000000</reverbAmount>
    <delayAmount>0x80000000</delayAmount>
    <compressorShape>0xDC28F5C3</compressorShape>
    <sound name="pad0">
        <volume>0</volume>
        <pan>0</pan>
        <lpfFrequency>50</lpfFrequency>
        <hpfFrequency>0</hpfFrequency>
        <fileName>SAMPLES/DRUMS/808.wav</fileName>
        <mode>MULTISAMPLED</mode>
        <transpose>0</transpose>
        <startRate>1000</startRate>
        <endRate>1000</endRate>
    </sound>
</drumKit>'''

# Example Deluge Synth XML Template
DELUGE_SYNTH_TEMPLATE = '''<?xml version="1.0" encoding="utf-8"?>
<synth synthVersion="4.1.4" earliestCompatibleFirmware="4.1.0">
    <polyphonic>1</polyphonic>
    <voiceCount>8</voiceCount>
    <osc1>
        <type>ANALOG_SAW</type>
        <volume>0</volume>
        <transpose>0</transpose>
        <detune>0</detune>
    </osc1>
    <osc2>
        <type>ANALOG_SAW</type>
        <volume>-50</volume>
        <transpose>-12</transpose>
        <detune>0</detune>
    </osc2>
    <lpf>
        <frequency>35</frequency>
        <resonance>10</resonance>
    </lpf>
    <hpf>
        <frequency>0</frequency>
        <resonance>0</resonance>
    </hpf>
    <env1>
        <attack>0</attack>
        <decay>0</decay>
        <sustain>50</sustain>
        <release>0</release>
    </env1>
    <lfo1>
        <type>TRIANGLE</type>
        <rate>2</rate>
    </lfo1>
    <reverbAmount>0</reverbAmount>
    <delayAmount>0</delayAmount>
</synth>'''

# Deluge-specific parameter ranges and values
DELUGE_PARAMETER_RANGES = {
    'volume': (-50, 50),  # dB range
    'pan': (-50, 50),     # Left-Right pan
    'filter_frequency': (0, 50),  # Filter frequency range
    'filter_resonance': (0, 50),  # Resonance range
    'envelope_values': (-50, 50),  # Envelope parameter range
    'lfo_rate': (0, 50),   # LFO rate range
    'transpose': (-48, 48),  # Semitone transpose range
    'detune': (-50, 50),    # Detune in cents
}

# Valid oscillator types for Deluge synths
DELUGE_OSC_TYPES = [
    'SINE',
    'TRIANGLE', 
    'ANALOG_SAW',
    'ANALOG_SQUARE',
    'SAW',
    'SQUARE',
    'WAVETABLE',
    'ANALOG_SAMPLE_AND_HOLD',
    'DIGITAL_SAMPLE_AND_HOLD',
    'INPUT_L',
    'INPUT_R',
    'INPUT_STEREO'
]

# Valid LFO types
DELUGE_LFO_TYPES = [
    'TRIANGLE',
    'SINE',
    'SQUARE',
    'SAW',
    'SAMPLE_AND_HOLD',
    'RANDOM_WALK'
]

# Valid filter modes
DELUGE_FILTER_MODES = [
    'LPF',      # Low Pass Filter
    'HPF',      # High Pass Filter
    'BPF',      # Band Pass Filter
    'NOTCH',    # Notch Filter
    'SVF_LPF',  # State Variable Filter - Low Pass
    'SVF_HPF',  # State Variable Filter - High Pass
    'SVF_BPF'   # State Variable Filter - Band Pass
]

# Deluge file system structure
DELUGE_FILE_STRUCTURE = {
    'root': {
        'SAMPLES': {
            'DRUMS': ['Kick samples', 'Snare samples', 'Hi-hat samples', 'etc.'],
            'HITS': ['One-shot samples', 'Stabs', 'Impact sounds'],
            'LOOPS': ['Drum loops', 'Music loops'],
            'RESAMPLE': ['Recorded/resampled content'],
            'MISC': ['Other samples']
        },
        'KITS': ['Drum kit XML files'],
        'SYNTHS': ['Synth preset XML files'],
        'SONGS': ['Song project files'],
        'CLIPS': ['Audio clips'],
        'TEMPLATES': ['Song templates']
    }
}

# Common Deluge XML elements and their purposes
DELUGE_XML_ELEMENTS = {
    'drumKit': {
        'description': 'Root element for drum kits',
        'attributes': ['drumKitVersion', 'earliestCompatibleFirmware'],
        'children': ['lpfFrequency', 'hpfFrequency', 'reverbAmount', 'delayAmount', 'sound']
    },
    'synth': {
        'description': 'Root element for synthesizer patches',
        'attributes': ['synthVersion', 'earliestCompatibleFirmware'],
        'children': ['polyphonic', 'voiceCount', 'osc1', 'osc2', 'lpf', 'hpf', 'env1', 'lfo1']
    },
    'sound': {
        'description': 'Individual drum sound within a kit',
        'attributes': ['name'],
        'children': ['volume', 'pan', 'lpfFrequency', 'hpfFrequency', 'fileName', 'mode']
    }
}

# Deluge firmware version compatibility
DELUGE_FIRMWARE_COMPATIBILITY = {
    '4.1.4': {
        'max_kit_sounds': 64,
        'max_synth_voices': 16,
        'supports_reverb': True,
        'supports_delay': True,
        'supports_multisampling': True,
        'supports_wavetables': True
    },
    '4.0.0': {
        'max_kit_sounds': 64,
        'max_synth_voices': 8,
        'supports_reverb': True,
        'supports_delay': True,
        'supports_multisampling': True,
        'supports_wavetables': False
    }
}

# Validation functions
def validate_deluge_parameter(param_name: str, value: float) -> bool:
    """Validate a Deluge parameter value is within acceptable range."""
    if param_name in DELUGE_PARAMETER_RANGES:
        min_val, max_val = DELUGE_PARAMETER_RANGES[param_name]
        return min_val <= value <= max_val
    return True  # Allow unknown parameters

def validate_osc_type(osc_type: str) -> bool:
    """Validate oscillator type is supported by Deluge."""
    return osc_type.upper() in DELUGE_OSC_TYPES

def validate_lfo_type(lfo_type: str) -> bool:
    """Validate LFO type is supported by Deluge."""
    return lfo_type.upper() in DELUGE_LFO_TYPES

def get_deluge_file_template(file_type: str) -> str:
    """Get XML template for specified Deluge file type."""
    templates = {
        'drum_kit': DELUGE_DRUM_KIT_TEMPLATE,
        'synth': DELUGE_SYNTH_TEMPLATE
    }
    return templates.get(file_type, '')

def suggest_deluge_file_structure(base_path: str) -> dict:
    """Suggest proper Deluge file structure for a given base path."""
    from pathlib import Path
    
    base = Path(base_path)
    structure = {}
    
    for folder, subfolders in DELUGE_FILE_STRUCTURE['root'].items():
        folder_path = base / folder
        structure[str(folder_path)] = {
            'create': True,
            'description': f'Deluge {folder} folder'
        }
        
        if isinstance(subfolders, dict):
            for subfolder in subfolders:
                subfolder_path = folder_path / subfolder
                structure[str(subfolder_path)] = {
                    'create': True,
                    'description': f'Deluge {subfolder} samples'
                }
    
    return structure


# Example usage and testing functions
def create_example_drum_kit():
    """Create an example drum kit for testing."""
    from deluge_synth_manager import DelugeDrumKitHandler, DelugeSample
    
    kit = DelugeDrumKitHandler()
    kit.create_empty_kit("Example Kit")
    
    # Add some example samples (these would need to exist)
    example_samples = [
        ("kick.wav", 0),
        ("snare.wav", 1), 
        ("hihat.wav", 2),
        ("crash.wav", 3)
    ]
    
    for sample_name, pad_index in example_samples:
        sample_path = f"SAMPLES/DRUMS/{sample_name}"
        # Note: In real usage, these files would need to exist
        print(f"Adding {sample_name} to pad {pad_index}")
    
    return kit

def create_example_synth():
    """Create an example synth patch for testing."""
    from deluge_synth_manager import DelugeSynthHandler
    
    synth = DelugeSynthHandler()
    synth.create_subtractive_synth("Example Synth")
    
    # Customize some parameters
    synth.synth_params.osc1_type = "ANALOG_SAW"
    synth.synth_params.osc2_type = "ANALOG_SQUARE"
    synth.synth_params.osc2_transpose = -12
    synth.synth_params.lpf_frequency = 25.0
    synth.synth_params.lpf_resonance = 15.0
    
    return synth


if __name__ == "__main__":
    print("Deluge File Format Specifications")
    print("=" * 40)
    
    # Print supported formats
    print("\nSupported Oscillator Types:")
    for osc_type in DELUGE_OSC_TYPES:
        print(f"  - {osc_type}")
    
    print("\nSupported LFO Types:")
    for lfo_type in DELUGE_LFO_TYPES:
        print(f"  - {lfo_type}")
    
    print("\nParameter Ranges:")
    for param, (min_val, max_val) in DELUGE_PARAMETER_RANGES.items():
        print(f"  {param}: {min_val} to {max_val}")
    
    # Test validation functions
    print(f"\nValidation Tests:")
    print(f"  Volume 25.0: {validate_deluge_parameter('volume', 25.0)}")
    print(f"  Volume 100.0: {validate_deluge_parameter('volume', 100.0)}")
    print(f"  OSC type 'ANALOG_SAW': {validate_osc_type('ANALOG_SAW')}")
    print(f"  OSC type 'INVALID': {validate_osc_type('INVALID')}")