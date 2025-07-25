# Multi-Format Support for XPM Converter

## Overview

The XPM Converter now supports reading and converting multiple audio and sampler formats into valid XPM files, with full support for firmware 3.4+ features including up to 8 layers per keygroup.

## Supported Formats

### Audio Formats
- ✅ **WAV** - Full native support
- ✅ **AIFF/AIF** - Converted to WAV using soundfile/librosa
- ✅ **FLAC** - Lossless conversion to WAV
- ✅ **MP3** - Converted to WAV (quality loss expected)
- ✅ **M4A** - Converted to WAV
- ✅ **OGG** - Converted to WAV

### Sampler Formats
- ✅ **SFZ** - Full support with region mapping, velocity layers, root notes
- 🔄 **SF2** - Basic support (placeholder - requires binary parsing)
- 🔄 **NKI/NKM** - Kontakt format (placeholder - proprietary format)
- 🔄 **EXS** - EXS24 format (placeholder)
- 🔄 **REX/RX2** - REX loops (placeholder)

## Firmware 3.4+ Features

### Enhanced Layer Support
- **Up to 8 layers** per keygroup (vs 4 in older firmware)
- Automatic layer limit detection based on target firmware version
- Intelligent velocity splitting for multiple layers

### Advanced Parameters
- **Enhanced envelope controls**: Attack, Decay, Release
- **Advanced filtering**: FilterType, FilterFreq, FilterRes, FilterKeytrack
- **Modulation**: LFO controls, ModWheel, Aftertouch
- **Velocity sensitivity**: VelocityToVolume, VelocityToFilter, VelocityToPitch
- **Key tracking**: Improved KeyTrack implementation

### SFZ Parameter Mapping
- Volume (dB) → Linear conversion for XPM
- Pan (-100 to 100) → 0.0 to 1.0 range
- Tune (cents) → TuneCoarse/TuneFine separation
- Velocity ranges → Proper layer splitting
- Key ranges → Intelligent keygroup assignment

## Usage

### Multi-Format Converter Window
1. Open **Advanced Tools** → **Multi-Format Converter**
2. The converter will automatically scan your selected folder for supported formats
3. Files are categorized by type (Audio/Sampler) and format
4. Select target firmware version (3.4+ recommended for 8-layer support)
5. Choose conversion mode: multi-sample, drum-kit, or one-shot
6. Convert selected files or all files at once

### Automatic Format Detection
- The main interface now shows format statistics when browsing folders
- Status message indicates: "Found X WAV, Y other audio, Z sampler files"
- Non-WAV files prompt to use the Multi-Format Converter

### SFZ Workflow
1. Place your SFZ file and all referenced samples in the same folder structure
2. Use Multi-Format Converter to import the SFZ
3. The converter will:
   - Parse all `<region>` blocks
   - Extract key mappings (lokey, hikey, key, pitch_keycenter)
   - Map velocity ranges (lovel, hivel)
   - Convert parameters (volume, pan, tune)
   - Create proper keygroups with velocity layers

## Technical Implementation

### Layer Management
```python
# Firmware-specific layer limits
MAX_LAYERS_BY_FIRMWARE = {
    '2.3.0.0': 4,
    '2.6.0.17': 4, 
    '3.4.0': 8,
    '3.5.0': 8
}

# Intelligent layer distribution
max_layers = MAX_LAYERS_BY_FIRMWARE.get(firmware_version, 4)
num_layers = min(len(available_samples), max_layers)
```

### Format Detection
```python
# Automatic format detection
def detect_file_format(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    if ext in SUPPORTED_AUDIO_FORMATS:
        return {'type': 'audio', 'format': ext}
    elif ext in SUPPORTED_SAMPLER_FORMATS:
        return {'type': 'sampler', 'format': ext}
    return None
```

### Audio Conversion
```python
# Non-WAV to WAV conversion
def convert_audio_format_to_wav(input_path, output_path=None):
    if SOUNDFILE_AVAILABLE:
        data, samplerate = sf.read(input_path)
        sf.write(output_path, data, samplerate, subtype='PCM_16')
    elif LIBROSA_AVAILABLE:
        y, sr = librosa.load(input_path, sr=None, mono=False)
        sf.write(output_path, y.T if y.ndim > 1 else y, sr)
```

## Dependencies

### Required for Audio Conversion
- `soundfile` - Primary audio I/O library
- `librosa` - Fallback audio processing (requires numpy)

### Optional Enhancements
- `numpy` - Enhanced audio analysis and processing

### Installation
```bash
pip install soundfile librosa numpy
```

## Best Practices

### For 8-Layer Instruments (Firmware 3.4+)
1. Use firmware version 3.4.0 or 3.5.0 as target
2. Organize samples with clear velocity ranges
3. Use intelligent naming: `Piano_C4_vel64.wav`, `Piano_C4_vel127.wav`
4. Keep velocity layers balanced (avoid single-sample instruments with 8 layers)

### For SFZ Conversion
1. Ensure all sample files are accessible relative to the SFZ file
2. Use proper key and velocity range definitions
3. Test parameter mappings (volume, pan, tune) in the resulting XPM
4. Verify keygroup assignments match your expectations

### For Maximum Compatibility
1. Use WAV files when possible for best results
2. Keep firmware target consistent across your project
3. Test XPM files on actual MPC hardware when possible
4. Use Expansion Doctor to validate created XPM files

## Troubleshooting

### Common Issues
- **"Failed to convert format"**: Install missing audio libraries
- **"No mappings found"**: Check SFZ syntax and sample paths
- **"Too many layers"**: Samples exceed firmware layer limit
- **"Sample not found"**: Verify relative paths in sampler files

### Performance Tips
- Large audio files may take time to convert
- Temporary WAV files are cleaned up automatically
- Use "Auto-detect velocity layers" for intelligent layer splitting
- Monitor the log viewer for detailed conversion information

## Future Enhancements

### Planned Features
- Full SF2 binary format parsing
- Kontakt NKI extraction (if legally possible)
- REX loop slicing and tempo detection
- Batch SFZ processing with folder scanning
- Advanced parameter interpolation for missing values

### Community Contributions
- Submit SFZ files for testing compatibility
- Report conversion issues with specific formats
- Suggest parameter mapping improvements
- Test on various MPC firmware versions
