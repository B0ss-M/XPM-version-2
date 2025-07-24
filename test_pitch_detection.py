#!/usr/bin/env python3
"""
Standalone pitch detection test script.
Usage: python test_pitch_detection.py <path_to_wav_file>
"""

import sys
import os

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_pitch_detection(sample_path):
    """Test pitch detection on a single sample file."""
    
    # Import the main functions
    try:
        from audio_pitch import detect_fundamental_pitch
        from xpm_parameter_editor import extract_root_note_from_wav, infer_note_from_filename
        # Import from the correct module name (with spaces replaced by underscores)
        import importlib.util
        spec = importlib.util.spec_from_file_location("main_module", "Gemini wav_TO_XpmV2.py")
        main_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(main_module)
        detect_sample_note = main_module.detect_sample_note
        IMPORTS_OK = True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all required modules are in the same directory.")
        IMPORTS_OK = False
    except Exception as e:
        print(f"❌ Module loading error: {e}")
        IMPORTS_OK = False

    if not os.path.exists(sample_path):
        print(f"❌ Error: File not found: {sample_path}")
        return

    if not sample_path.lower().endswith('.wav'):
        print(f"❌ Error: File must be a WAV file: {sample_path}")
        return

    filename = os.path.basename(sample_path)
    print(f"🎵 Pitch Detection Test: {filename}")
    print("=" * 60)
    print()

    def midi_to_note_name(midi_note):
        """Convert MIDI note number to note name."""
        if not isinstance(midi_note, int) or midi_note < 0 or midi_note > 127:
            return "Invalid"
        
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = (midi_note // 12) - 1
        note = note_names[midi_note % 12]
        return f"{note}{octave}"

    # Test Method 1: WAV Metadata
    if IMPORTS_OK:
        try:
            metadata_note = extract_root_note_from_wav(sample_path)
            if metadata_note is not None:
                note_name = midi_to_note_name(metadata_note)
                print(f"✅ WAV Metadata: MIDI {metadata_note} ({note_name})")
            else:
                print(f"❌ WAV Metadata: No 'smpl' chunk found")
        except Exception as e:
            print(f"❌ WAV Metadata: Error - {e}")

        # Test Method 2: Filename Inference
        try:
            filename_note = infer_note_from_filename(sample_path)
            if filename_note is not None:
                note_name = midi_to_note_name(filename_note)
                print(f"✅ Filename Inference: MIDI {filename_note} ({note_name})")
            else:
                print(f"❌ Filename Inference: No note pattern found")
        except Exception as e:
            print(f"❌ Filename Inference: Error - {e}")

        # Test Method 3: Audio Analysis
        try:
            pitch_note = detect_fundamental_pitch(sample_path)
            if pitch_note is not None:
                note_name = midi_to_note_name(pitch_note)
                print(f"✅ Audio Analysis: MIDI {pitch_note} ({note_name})")
            else:
                print(f"❌ Audio Analysis: Detection failed")
        except Exception as e:
            print(f"❌ Audio Analysis: Error - {e}")

        # Test the enhanced main function
        print("\n" + "-" * 40)
        print("🎯 Enhanced Detection Function:")
        try:
            main_result = detect_sample_note(sample_path)
            note_name = midi_to_note_name(main_result)
            print(f"✅ Final Result: MIDI {main_result} ({note_name})")
        except Exception as e:
            print(f"❌ Enhanced Function: Error - {e}")
            
        # Show a comparison summary
        print("\n" + "-" * 40)
        print("📊 Detection Method Comparison:")
        results = []
        if IMPORTS_OK:
            try:
                metadata_note = extract_root_note_from_wav(sample_path)
                if metadata_note:
                    results.append(("WAV Metadata", metadata_note, midi_to_note_name(metadata_note)))
            except:
                pass
                
            try:
                filename_note = infer_note_from_filename(sample_path)
                if filename_note:
                    results.append(("Filename", filename_note, midi_to_note_name(filename_note)))
            except:
                pass
                
            try:
                audio_note = detect_fundamental_pitch(sample_path)
                if audio_note:
                    results.append(("Audio Analysis", audio_note, midi_to_note_name(audio_note)))
            except:
                pass
        
        if results:
            print("Method           | MIDI | Note")
            print("-" * 35)
            for method, midi, note in results:
                print(f"{method:<15} | {midi:>4} | {note}")
                
            # Analysis
            notes = [midi for _, midi, _ in results]
            if len(set(notes)) == 1:
                print(f"\n✅ All methods agree: {notes[0]} ({midi_to_note_name(notes[0])})")
            else:
                print(f"\n⚠️  Methods disagree - range: {min(notes)}-{max(notes)} MIDI")
                closest_pair = min([(abs(a-b), a, b) for i, (_, a, _) in enumerate(results) 
                                   for _, b, _ in results[i+1:]])
                print(f"Closest agreement: {closest_pair[2]} semitones apart")

    # File info
    print("\n" + "-" * 40)
    print("📊 File Information:")
    try:
        import wave
        with wave.open(sample_path, 'rb') as wav:
            frames = wav.getnframes()
            framerate = wav.getframerate()
            channels = wav.getnchannels()
            duration = frames / framerate
            
            print(f"Duration: {duration:.2f} seconds")
            print(f"Sample Rate: {framerate} Hz")
            print(f"Channels: {channels}")
            print(f"Frames: {frames:,}")
    except Exception as e:
        print(f"Could not read file info: {e}")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_pitch_detection.py <path_to_wav_file>")
        print("Example: python test_pitch_detection.py /path/to/sample.wav")
        sys.exit(1)
    
    sample_path = sys.argv[1]
    test_pitch_detection(sample_path)
