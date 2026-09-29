# Deluge Synth Manager - Complete Feature Guide

## 🎵 Overview

The Deluge Synth Manager is a comprehensive application for managing Deluge Synth hardware files. It provides tools to "read and write drum kits and synth instruments for the deluge synth hardware", "understand the deluges filing system and write xml files that deluge uses", "search folders and sub folder for folder containing wav files", perform "batch process" operations, and "convert drum kits and instruments mainly from akai mpc to the deluge format".

## 🚀 Key Features

### ✅ **Drum Kit Management**
- Create new empty drum kits
- Load existing Deluge drum kit XML files
- Add audio samples to kit pads with proper velocity mapping
- Generate proper Deluge XML format with hex-encoded parameters
- Save kits with correct folder structure for Deluge hardware

### ✅ **Synth Instrument Management** 
- Create subtractive synthesizers with dual oscillators
- Support for sample-based oscillators
- Full parameter control (envelope, filter, LFO, effects)
- Export to Deluge-compatible XML format

### ✅ **File Search & Batch Processing**
- **Search folders and subfolders** for audio files (WAV, AIFF, FLAC)
- Find folders containing multiple audio files (potential drum kits)  
- **Batch operations**:
  - Create Deluge kits from selected audio files
  - Convert multiple files to WAV format
  - Organize file structures
- Real-time file filtering and selection

### ✅ **MPC to Deluge Converter**
- **Convert drum kits and instruments from Akai MPC** to Deluge format
- Support for XPM, PGM, and Keygroup files
- Automatic file type detection
- **Batch conversion** with options:
  - Convert samples to WAV format
  - Preserve velocity mapping
  - Auto-tune detection
  - Organize output structure
- Scan entire directories for MPC files

### ✅ **Audio Conversion Utilities**
- Convert between multiple audio formats
- Support for MP3, M4A, OGG, FLAC, AIFF → WAV conversion
- Automatic format validation and metadata extraction
- Batch audio processing capabilities

## 📁 Understanding Deluge File System

### **Deluge XML Structure**
The application generates XML files that match the Deluge's exact format requirements:

```xml
<kit>
  <defaultParams>
    <!-- Hex-encoded parameter values -->
    <delay>
      <pingPong>0x80000000</pingPong>
      <analog>0x80000000</analog>
      <syncLevel>0x00000007</syncLevel>
    </delay>
  </defaultParams>
  
  <soundSources>
    <sound index="0">
      <fileName>SAMPLES/DRUMS/KICK001.wav</fileName>
      <mode>subtractive</mode>
      <!-- Complete parameter structure -->
    </sound>
  </soundSources>
</kit>
```

### **Parameter Encoding**
- All parameter values are hex-encoded (e.g., `0x80000000` for center position)
- Proper element hierarchy with soundSources, defaultParams, modKnobs
- Correct file path references for sample locations

## 🎛️ GUI Interface

### **Tab-Based Design**

1. **Drum Kits Tab**
   - Create, load, and save drum kits
   - Add samples to individual pads
   - View kit information and pad assignments

2. **Synth Instruments Tab** 
   - Create subtractive and sample-based synths
   - Parameter control sliders
   - Real-time parameter display

3. **File Search Tab**
   - Directory browser for searching audio files
   - File type filters (WAV, AIFF, FLAC)
   - Results list with batch operations
   - Kit creation from selected files

4. **MPC Converter Tab**
   - Browse MPC file directories
   - Scan and list found MPC files
   - Conversion options and batch processing
   - Output directory organization

5. **Utilities Tab**
   - Audio format conversion
   - File validation tools
   - Activity logging
   - System status information

## 🔧 Technical Implementation

### **Core Classes**

- **DelugeDrumKitHandler**: Manages drum kit creation and XML generation
- **DelugeSynthHandler**: Handles synth instrument creation
- **DelugeFileSearcher**: Provides folder scanning and audio file discovery
- **MPCToDelugeConverter**: Converts MPC files to Deluge format
- **AudioConverter**: Handles audio format conversion
- **DelugeManagerGUI**: Main application interface

### **Audio Processing**
- SoundFile library for audio format support
- Librosa for advanced audio analysis
- Automatic sample rate and format validation
- Cross-platform file path handling

### **XML Generation**
- ElementTree for proper XML structure
- Hex parameter encoding for Deluge compatibility  
- Complete parameter sets with default values
- Proper file reference handling

## 📝 Usage Examples

### **Creating a Drum Kit from Audio Files**

1. Open **File Search** tab
2. Browse to directory containing WAV files
3. Click "Search for Audio Files"
4. Select desired audio files from results
5. Click "Create Kit from Selected"
6. Save the kit from the **Drum Kits** tab

### **Converting MPC Programs to Deluge**

1. Open **MPC Converter** tab
2. Browse to directory containing XPM/PGM files
3. Click "Scan MPC Files"
4. Select conversion options
5. Choose output directory
6. Click "Convert Selected" or "Convert All"

### **Batch Audio Processing**

1. Open **File Search** tab
2. Search for non-WAV audio files
3. Select files for conversion
4. Click "Convert Selected to WAV"
5. Choose output directory

## 🎯 Real-World Hardware Compatibility

The application generates XML files that match the exact format used by Deluge hardware:

- **Correct hex parameter encoding** based on real Deluge files
- **Proper file path structure** for sample references
- **Complete parameter sets** with all required elements
- **Valid XML hierarchy** matching Deluge expectations

## 🔄 Batch Processing Capabilities

- **Search entire directory trees** for audio content
- **Identify potential drum kit folders** based on file content
- **Convert multiple MPC files** in one operation
- **Organize output structures** automatically
- **Progress tracking** with detailed logging

## 📋 Requirements

- Python 3.8+
- tkinter (GUI framework)
- xml.etree.ElementTree (XML processing)
- Optional: soundfile, librosa (enhanced audio support)
- Optional: XPM utilities for MPC file conversion

## 🎉 Getting Started

```bash
# Run the application
python3 deluge_synth_manager.py

# Test functionality
python3 test_new_features.py

# Run examples
python3 deluge_examples.py
```

The application provides a complete solution for Deluge Synth file management, from individual file creation to comprehensive batch processing and format conversion.