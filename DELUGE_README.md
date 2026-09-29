# Deluge Synth File Manager

A comprehensive tool for creating, editing, and managing drum kits and synth instruments for the **Deluge** synthesizer/groovebox hardware. Built on core features adapted from the XPM converter, this tool understands the Deluge's XML-based file system and provides an intuitive interface for working with Deluge files.

![Deluge](https://img.shields.io/badge/Hardware-Deluge-blue)
![Python](https://img.shields.io/badge/Python-3.8+-green)
![Format](https://img.shields.io/badge/Format-XML-orange)

## 🎯 Features

### 🥁 Drum Kit Management
- **Create new drum kits** with up to 16 pads
- **Load and edit existing** Deluge drum kit XML files
- **Multi-velocity layer support** for dynamic playing
- **Sample assignment** with drag-and-drop interface
- **Parameter control** for volume, pan, filters per pad

### 🎹 Synth Instrument Creation
- **Subtractive synthesis** with dual oscillators
- **Sample-based oscillators** using WAV files
- **Complete parameter control** (filters, envelopes, LFOs)
- **Wavetable support** for advanced synthesis
- **Modulation routing** for complex patches

### 🔧 Audio Processing
- **Multi-format support**: WAV, AIFF, FLAC, MP3, OGG
- **Automatic conversion** to Deluge-compatible formats
- **Sample rate optimization** for best performance
- **Audio validation** and quality checking

### 📁 File System Management
- **Deluge folder structure** understanding
- **Proper file organization** (KITS, SYNTHS, SAMPLES)
- **Path validation** and error checking
- **Backup creation** for safety

## 🚀 Quick Start

### Installation

1. **Clone or download** the script files
2. **Install dependencies**:
   ```bash
   pip install soundfile librosa numpy
   ```
3. **Run the application**:
   ```bash
   python3 deluge_synth_manager.py
   ```

### Basic Usage

#### Creating a Drum Kit

1. **Launch the application**
2. **Go to "Drum Kits" tab**
3. **Click "Create New Kit"**
4. **Click "Add Samples to Kit"**
5. **Select your audio files**
6. **Assign samples to pads (0-15)**
7. **Click "Save Kit"**
8. **Choose output location** in your Deluge's KITS folder

#### Creating a Synth Instrument

1. **Go to "Synth Instruments" tab**
2. **Choose synth type**:
   - **"Create Subtractive Synth"** for traditional synthesis
   - **"Create Sample-Based Synth"** for wavetable/sample oscillators
3. **Edit parameters** as needed
4. **Click "Save Synth"**
5. **Save to your Deluge's SYNTHS folder**

## 📖 Understanding Deluge File Formats

### Drum Kit XML Structure

```xml
<?xml version="1.0" encoding="utf-8"?>
<drumKit drumKitVersion="4.1.4" earliestCompatibleFirmware="4.1.0">
    <lpfFrequency>50</lpfFrequency>
    <hpfFrequency>0</hpfFrequency>
    <sound name="pad0">
        <volume>0</volume>
        <pan>0</pan>
        <fileName>SAMPLES/DRUMS/kick.wav</fileName>
        <mode>MULTISAMPLED</mode>
    </sound>
</drumKit>
```

### Synth XML Structure

```xml
<?xml version="1.0" encoding="utf-8"?>
<synth synthVersion="4.1.4" earliestCompatibleFirmware="4.1.0">
    <polyphonic>1</polyphonic>
    <voiceCount>8</voiceCount>
    <osc1>
        <type>ANALOG_SAW</type>
        <volume>0</volume>
    </osc1>
    <lpf>
        <frequency>35</frequency>
        <resonance>10</resonance>
    </lpf>
</synth>
```

## 🏗️ Deluge File System Structure

The Deluge expects files to be organized in a specific folder structure on the SD card:

```
/
├── KITS/           # Drum kit XML files
├── SYNTHS/         # Synth preset XML files  
├── SONGS/          # Song project files
└── SAMPLES/
    ├── DRUMS/      # Drum samples
    ├── HITS/       # One-shot samples  
    ├── LOOPS/      # Audio loops
    ├── RESAMPLE/   # Recorded content
    └── MISC/       # Other samples
```

## 🎛️ Parameters and Ranges

### Volume and Pan
- **Volume**: -50 to +50 dB
- **Pan**: -50 (left) to +50 (right)

### Filter Parameters
- **Frequency**: 0 to 50 (logarithmic scale)
- **Resonance**: 0 to 50

### Oscillator Types
- `SINE`, `TRIANGLE`, `SAW`, `SQUARE`
- `ANALOG_SAW`, `ANALOG_SQUARE`
- `WAVETABLE` (sample-based)
- `INPUT_L`, `INPUT_R`, `INPUT_STEREO`

### Envelope Parameters
- **Attack, Decay, Release**: -50 to +50
- **Sustain**: 0 to 50

## 💡 Tips and Best Practices

### For Drum Kits
1. **Use appropriate sample formats**: 44.1kHz WAV files work best
2. **Organize by velocity**: Use velocity layers for dynamic drums
3. **Keep file paths short**: Deluge has path length limitations
4. **Test on hardware**: Always verify kits work on actual Deluge

### For Synth Patches
1. **Start simple**: Build complexity gradually
2. **Use relative paths**: Reference samples in SAMPLES folder correctly
3. **Mind the polyphony**: Too many voices can cause performance issues
4. **Save frequently**: Create backups of complex patches

### File Organization
1. **Follow Deluge conventions**: Use the standard folder structure
2. **Use descriptive names**: Clear naming helps with organization
3. **Avoid special characters**: Stick to alphanumeric characters
4. **Keep samples organized**: Group related samples in subfolders

## 🔧 Advanced Features

### Batch Processing
- **Convert multiple audio files** at once
- **Organize file structures** automatically
- **Validate Deluge file formats** in batches

### Sample Management
- **Multi-velocity layer** assignments
- **Sample loop point** detection and setting
- **Audio format conversion** with quality preservation

### Modulation and Routing
- **LFO to filter** frequency modulation
- **Envelope to amplitude** and filter control
- **Velocity sensitivity** for all parameters

## 📚 Core Components

### Classes and Structure

1. **`DelugeXMLHandler`**: Base class for XML operations
2. **`DelugeDrumKitHandler`**: Drum kit creation and management  
3. **`DelugeSynthHandler`**: Synth instrument creation and management
4. **`AudioConverter`**: Audio format conversion utilities
5. **`DelugeManagerGUI`**: Main GUI application interface

### Data Classes

- **`DelugeSample`**: Represents individual audio samples
- **`DelugePad`**: Represents drum pads with samples and parameters
- **`DelugeSynthParams`**: Complete synth parameter set

## 🛠️ Dependencies

### Required
- **Python 3.8+**
- **tkinter** (usually included with Python)
- **xml.etree.ElementTree** (standard library)

### Optional (Enhanced Features)
- **soundfile**: High-quality audio conversion
- **librosa**: Advanced audio analysis
- **numpy**: Numerical processing support

Install optional dependencies:
```bash
pip install soundfile librosa numpy
```

## 🤝 Contributing

Contributions are welcome! Areas for improvement:

1. **Additional oscillator types** and modulation options
2. **Advanced sample editing** features
3. **Preset library management** 
4. **MIDI learn** functionality integration
5. **Additional audio format support**

## 📄 License

This project builds on the core features of the XPM converter and is provided as-is for educational and creative use.

## 🔗 Related Projects

- **Original XPM Converter**: MPC format creation and management
- **ConvertWithMoss**: Professional sampler format converter
- **Deluge Community**: Hardware user community resources

## 📞 Support

For issues, feature requests, or questions:

1. **Check the FAQ** section in the code documentation
2. **Review example files** in the `/examples` directory  
3. **Test with simple cases** first before complex projects
4. **Verify Deluge firmware compatibility** for your hardware

---

**Happy music making with your Deluge! 🎵**