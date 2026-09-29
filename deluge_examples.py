#!/usr/bin/env python3
"""
Deluge Examples and Test Script

This script demonstrates how to use the Deluge Synth Manager 
programmatically and provides example usage patterns.
"""

import os
import sys
from pathlib import Path

# Add the current directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from deluge_synth_manager import (
    DelugeDrumKitHandler, 
    DelugeSynthHandler, 
    AudioConverter,
    DelugeSample,
    DelugePad,
    DelugeSynthParams
)
from deluge_format_specs import (
    validate_deluge_parameter,
    validate_osc_type,
    get_deluge_file_template,
    create_example_drum_kit,
    create_example_synth
)


def example_create_basic_drum_kit():
    """Example: Create a basic drum kit programmatically."""
    print("🥁 Creating Basic Drum Kit Example")
    print("-" * 40)
    
    # Initialize drum kit handler
    kit_handler = DelugeDrumKitHandler()
    kit_handler.create_empty_kit("Basic Drum Kit")
    
    # Example sample files (these would need to exist in practice)
    example_samples = [
        {
            'file': 'kick_heavy.wav',
            'pad': 0,
            'description': 'Heavy kick drum'
        },
        {
            'file': 'snare_crisp.wav', 
            'pad': 1,
            'description': 'Crisp snare'
        },
        {
            'file': 'hihat_closed.wav',
            'pad': 2, 
            'description': 'Closed hi-hat'
        },
        {
            'file': 'hihat_open.wav',
            'pad': 3,
            'description': 'Open hi-hat'
        }
    ]
    
    # Add samples to pads
    for sample_info in example_samples:
        sample_path = f"SAMPLES/DRUMS/{sample_info['file']}"
        print(f"Adding {sample_info['description']} to pad {sample_info['pad']}")
        
        # In practice, you'd check if the file exists:
        # if os.path.exists(sample_path):
        #     kit_handler.add_sample_to_pad(sample_info['pad'], sample_path)
        
        # For demo purposes, we'll just show the XML generation
    
    # Generate and display the XML
    xml_output = kit_handler.generate_kit_xml("Basic Drum Kit")
    print(f"\nGenerated XML (first 500 characters):")
    print(xml_output[:500] + "...")
    
    # Save the kit (would save to actual file in practice)
    # kit_handler.save_kit("output/basic_drum_kit.xml", "Basic Drum Kit")
    print(f"\n✅ Drum kit example completed")


def example_create_subtractive_synth():
    """Example: Create a basic subtractive synth."""
    print("\n🎹 Creating Subtractive Synth Example")
    print("-" * 40)
    
    # Initialize synth handler
    synth_handler = DelugeSynthHandler()
    synth_handler.create_subtractive_synth("Basic Subtractive")
    
    # Modify some parameters
    params = synth_handler.synth_params
    
    # Set up a classic analog-style patch
    params.osc1_type = "ANALOG_SAW"
    params.osc1_volume = 0.0
    params.osc2_type = "ANALOG_SAW"
    params.osc2_volume = -12.0  # Quieter second oscillator
    params.osc2_transpose = -12  # One octave down
    params.osc2_detune = 5       # Slight detune for richness
    
    # Filter settings for warm analog sound
    params.lpf_frequency = 30.0  # Mid-range cutoff
    params.lpf_resonance = 15.0  # Some resonance for character
    
    # Envelope for classic synth response
    params.env1_attack = 5.0     # Quick attack
    params.env1_decay = 15.0     # Medium decay
    params.env1_sustain = 35.0   # Moderate sustain
    params.env1_release = 20.0   # Natural release
    
    # Add some effects
    params.reverb_amount = 10.0  # Light reverb
    
    print(f"Oscillator 1: {params.osc1_type} @ {params.osc1_volume}dB")
    print(f"Oscillator 2: {params.osc2_type} @ {params.osc2_volume}dB, {params.osc2_transpose} semitones")
    print(f"Filter: LPF @ {params.lpf_frequency}, resonance {params.lpf_resonance}")
    print(f"Envelope: A{params.env1_attack} D{params.env1_decay} S{params.env1_sustain} R{params.env1_release}")
    
    # Generate XML
    xml_output = synth_handler.generate_synth_xml("Basic Subtractive")
    print(f"\nGenerated XML (first 500 characters):")
    print(xml_output[:500] + "...")
    
    # Save the synth (would save to actual file in practice)  
    # synth_handler.save_synth("output/basic_subtractive.xml", "Basic Subtractive")
    print(f"\n✅ Subtractive synth example completed")


def example_create_sample_based_synth():
    """Example: Create a sample-based synth (wavetable)."""
    print("\n🌊 Creating Sample-Based Synth Example")
    print("-" * 40)
    
    synth_handler = DelugeSynthHandler()
    synth_handler.create_subtractive_synth("Wavetable Synth")
    
    # Simulate adding a wavetable sample
    example_wavetable = "SAMPLES/MISC/wavetable_pad.wav"
    print(f"Adding wavetable sample: {example_wavetable}")
    
    # In practice: synth_handler.add_sample_based_osc(example_wavetable, 1)
    
    # Configure for wavetable synthesis
    params = synth_handler.synth_params
    params.osc1_type = "WAVETABLE"
    params.osc1_volume = 0.0
    params.osc2_type = "SINE"     # Sine wave for harmonic content
    params.osc2_volume = -20.0    # Much quieter
    params.osc2_transpose = 12    # One octave up
    
    # Filter for wavetable shaping 
    params.lpf_frequency = 40.0   # Higher cutoff for brightness
    params.lpf_resonance = 5.0    # Light resonance
    
    # Slower envelope for pad sounds
    params.env1_attack = 25.0     # Slow attack
    params.env1_decay = 30.0      # Long decay
    params.env1_sustain = 40.0    # High sustain
    params.env1_release = 35.0    # Long release
    
    # More reverb for ambient sound
    params.reverb_amount = 25.0
    params.delay_amount = 15.0
    
    print(f"Wavetable oscillator configured")
    print(f"Filter: LPF @ {params.lpf_frequency}, resonance {params.lpf_resonance}")
    print(f"Envelope: Slow attack/release for pad sound")
    print(f"Effects: Reverb {params.reverb_amount}, Delay {params.delay_amount}")
    
    xml_output = synth_handler.generate_synth_xml("Wavetable Synth")
    print(f"\nGenerated XML (first 500 characters):")
    print(xml_output[:500] + "...")
    
    print(f"\n✅ Sample-based synth example completed")


def example_audio_conversion():
    """Example: Audio file conversion for Deluge compatibility."""
    print("\n🔄 Audio Conversion Example")
    print("-" * 40)
    
    converter = AudioConverter()
    
    # Example audio files (various formats)
    example_files = [
        "sample1.mp3",
        "sample2.flac", 
        "sample3.aiff",
        "sample4.ogg"
    ]
    
    print("Converting audio files to Deluge-compatible WAV format:")
    
    for audio_file in example_files:
        print(f"\nProcessing: {audio_file}")
        
        # Validate the audio file first
        # info = converter.validate_audio_file(audio_file)
        # if info['valid']:
        #     print(f"  Format: {info['format']}")
        #     print(f"  Sample Rate: {info['sample_rate']} Hz")
        #     print(f"  Channels: {info['channels']}")
        #     print(f"  Duration: {info['duration']:.2f} seconds")
        #     
        #     # Convert to WAV
        #     wav_output = converter.convert_to_wav(audio_file)
        #     if wav_output:
        #         print(f"  ✅ Converted to: {wav_output}")
        #     else:
        #         print(f"  ❌ Conversion failed")
        # else:
        #     print(f"  ❌ Invalid audio file")
        
        # For demo purposes, just show what would happen
        wav_filename = Path(audio_file).with_suffix('.wav')
        print(f"  Would convert to: {wav_filename}")
    
    print(f"\n✅ Audio conversion example completed")


def example_parameter_validation():
    """Example: Validate Deluge parameters."""
    print("\n✅ Parameter Validation Example")
    print("-" * 40)
    
    # Test various parameter values
    test_cases = [
        ('volume', 25.0, True),
        ('volume', 100.0, False),  # Too high
        ('pan', -25.0, True),
        ('pan', -75.0, False),     # Too low
        ('filter_frequency', 35.0, True),
        ('transpose', -24, True),
        ('transpose', 50, False),  # Too high
    ]
    
    print("Testing parameter validation:")
    for param, value, expected in test_cases:
        result = validate_deluge_parameter(param, value)
        status = "✅" if result == expected else "❌"
        print(f"  {status} {param} = {value}: {result}")
    
    # Test oscillator types
    print(f"\nTesting oscillator types:")
    osc_tests = [
        ('ANALOG_SAW', True),
        ('SINE', True),
        ('INVALID_TYPE', False),
        ('WAVETABLE', True)
    ]
    
    for osc_type, expected in osc_tests:
        result = validate_osc_type(osc_type)
        status = "✅" if result == expected else "❌"
        print(f"  {status} {osc_type}: {result}")
    
    print(f"\n✅ Parameter validation example completed")


def example_file_structure():
    """Example: Show proper Deluge file structure."""
    print("\n📁 Deluge File Structure Example")
    print("-" * 40)
    
    from deluge_format_specs import suggest_deluge_file_structure
    
    # Suggest structure for a hypothetical SD card
    base_path = "/Volumes/DELUGE"  # Typical SD card mount point
    
    print(f"Suggested file structure for: {base_path}")
    
    structure = suggest_deluge_file_structure(base_path)
    
    for path, info in structure.items():
        if info['create']:
            relative_path = Path(path).relative_to(base_path)
            print(f"  📂 {relative_path}/  # {info['description']}")
    
    print(f"\nExample file placement:")
    print(f"  📄 KITS/my_drum_kit.xml          # Drum kit definition")
    print(f"  📄 SYNTHS/my_synth_patch.xml     # Synth preset")
    print(f"  🎵 SAMPLES/DRUMS/kick.wav        # Drum samples")
    print(f"  🎵 SAMPLES/HITS/stab.wav         # One-shot samples")
    print(f"  🎵 SAMPLES/LOOPS/beat.wav        # Audio loops")
    
    print(f"\n✅ File structure example completed")


def run_all_examples():
    """Run all example functions."""
    print("🎵 Deluge Synth Manager Examples")
    print("=" * 50)
    print("This script demonstrates core functionality")
    print("Note: Some features require actual audio files to work fully")
    print()
    
    try:
        example_create_basic_drum_kit()
        example_create_subtractive_synth()
        example_create_sample_based_synth()
        example_audio_conversion()
        example_parameter_validation()
        example_file_structure()
        
        print(f"\n🎉 All examples completed successfully!")
        print(f"\nNext steps:")
        print(f"  1. Run 'python3 deluge_synth_manager.py' for GUI interface")
        print(f"  2. Place actual audio files in appropriate folders")
        print(f"  3. Test created files on your Deluge hardware")
        
    except ImportError as e:
        print(f"❌ ImportError: {e}")
        print(f"Make sure deluge_synth_manager.py is in the same directory")
    except Exception as e:
        print(f"❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_examples()