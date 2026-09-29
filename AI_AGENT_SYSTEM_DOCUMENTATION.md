# 🎵 XPM Version 2 - Complete System Documentation
## AI Agent Continuation Guide for Advanced Music Production Tool

---

## 📋 **PROJECT OVERVIEW**

**XPM Version 2** is a comprehensive, professional-grade music production tool focusing on MPC (Music Production Center) sample management, conversion, and advanced music theory analysis. This is NOT a simple audio converter - it's a complete ecosystem for professional music producers working with Akai MPC hardware.

### **Core Mission**
- Convert various audio/sampler formats to professional XPM format for MPC hardware
- Provide advanced music theory analysis and chord progression tools
- Enable intelligent MIDI chord analysis and library building
- Maintain professional MPC standards and firmware compatibility

---

## 🏗️ **ARCHITECTURE OVERVIEW**

### **Main Application Structure**
```
Project Root: /Users/marlsz/Documents/GitHub/XPM-version-2/
├── Gemini wav_TO_XpmV2.py         # Main GUI application (12,214 lines)
├── scripts/                       # Modular functionality
├── tk_file_utils.py               # Safe file dialog utilities
├── xpm_utils.py                   # XPM format utilities
├── audio_pitch.py                 # Audio analysis
├── xpm_parameter_editor.py        # XPM parameter manipulation
└── [Additional utility modules]
```

### **Critical Constants & Standards**
```python
APP_VERSION = "v2.11.6.6"  # ConvertWithMoss professional standard
SUPPORTED_FIRMWARES = ["2.3.0.0", "2.6.0.17", "3.4.0", "3.5.0"]
MAX_LAYERS_BY_FIRMWARE = {'3.4.0': 8, '3.5.0': 8}  # Firmware limits

# Professional XPM Standards (NEVER MODIFY):
# 1. Root notes: +1 offset (MPC hardware convention)
# 2. File_Version: 2.1, Application_Version: v2.11.6.6  
# 3. Group samples by key ranges, not single notes
# 4. Maximum 8 layers per keygroup (firmware 3.4+)
# 5. Use consecutive key ranges for playability
```

---

## 🎼 **SCRIPTS DIRECTORY - MODULAR ARCHITECTURE**

### **🎵 MIDI & Music Theory System (Recently Enhanced)**
```
scripts/
├── midi_chord_analyzer.py      # Core MIDI chord detection (678 lines)
├── database_enhancer.py        # Database enhancement for MIDI data (523 lines)  
├── midi_import_gui.py          # MIDI drag-drop GUI interface (583 lines)
├── machine_learning_engine.py  # ML for chord learning (692 lines)
├── music_theory_engine.py      # Advanced music theory analysis
└── progression_rebuilder_gui.py # Main music theory GUI (enhanced)
```

**CRITICAL**: The progression import button now supports MIDI files alongside .progression files. This enables the "algorithm improvement through more chord data" functionality.

### **Legacy Music Tools**
```
├── midi_to_progression.py       # Basic MIDI conversion utility
├── ripchord_to_progression_gui.py # Ripchord file converter
├── relink_xpm.py               # XPM sample path repair
└── check_java_and_moss.py      # ConvertWithMoss integration
```

---

## 🎛️ **MAIN APPLICATION CLASSES**

### **Core Application Class**
```python
class App(tk.Tk):  # Line 10942 in main file
    # Main GUI application with professional MPC theming
    # Handles all major workflows and tool integration
```

### **Key Utility Windows** 
```python
class ExpansionDoctorWindow(tk.Toplevel):    # XPM bloat analysis & repair
class ExpansionBuilderWindow(tk.Toplevel):   # Multi-sample XPM creation
class MultiFormatConverterWindow(tk.Toplevel): # Batch format conversion
class SampleMappingEditorWindow:             # Sample-to-key mapping
class KeyboardMapperWindow:                  # Visual keyboard mapping
```

---

## 🔧 **TECHNICAL DEPENDENCIES**

### **Core Dependencies (Required)**
```python
# Always Required:
import tkinter as tk  # Main GUI framework
import xml.etree.ElementTree as ET  # XPM format handling
from tk_file_utils import *  # Safe file dialogs (macOS compatibility)

# Audio Processing:
import wave  # Basic WAV support
import struct  # Binary data manipulation
```

### **Enhanced Dependencies (Optional but Recommended)**
```python
# pip install mido numpy scipy scikit-learn
import mido           # MIDI file processing (NEW REQUIREMENT)
import numpy as np    # Advanced audio analysis  
import librosa        # Professional audio analysis
import soundfile as sf # Alternative audio I/O
import PIL           # Image processing for GUI enhancements

# Advanced Analysis:
import pretty_midi    # Enhanced MIDI analysis
import music21       # Deep music theory (optional)
```

### **Dependency Management Pattern**
```python
try:
    import advanced_module
    ADVANCED_AVAILABLE = True
except ImportError:
    ADVANCED_AVAILABLE = False
    # Always provide graceful fallback functionality
```

---

## 💽 **DATA FORMATS & STANDARDS**

### **XPM Format (Target Output)**
- **XML-based** MPC sampler format
- **Professional Standards**: File_Version 2.1, Application_Version v2.11.6.6
- **Key Features**: Multi-layer support, velocity sensitivity, keygroup mapping
- **Hardware Compatibility**: MPC Live, MPC Live II, MPC One, MPC X firmware 2.3+

### **Input Format Support**
```python
SUPPORTED_AUDIO_FORMATS = {
    '.wav': 'WAV Audio', '.aiff': 'AIFF Audio', '.flac': 'FLAC Audio',
    '.mp3': 'MP3 Audio', '.m4a': 'M4A Audio', '.ogg': 'OGG Audio'
}

SUPPORTED_SAMPLER_FORMATS = {
    '.sfz': 'SFZ Sampler', '.sf2': 'SoundFont 2', '.exs': 'EXS24',
    '.nki': 'Kontakt', '.rex': 'REX Loop', '.akai': 'Akai MPC Program'
}
```

### **MIDI Analysis Data (NEW)**
```python
# ProgressionAnalysis object structure:
{
    'file_path': str,
    'chord_symbols': List[str],      # ['C', 'Am', 'F', 'G']
    'key_signature': str,            # 'C major'
    'complexity_score': float,       # 0.0-1.0
    'confidence_scores': List[float] # Per-chord confidence
}
```

---

## 🎯 **RECENT MAJOR ENHANCEMENTS**

### **🎼 MIDI Chord Import System (February 2026)**
**CRITICAL NEW FUNCTIONALITY**: Complete MIDI chord analysis and machine learning system

#### **What Was Added:**
1. **MIDI Chord Analyzer** (`midi_chord_analyzer.py`)
   - Advanced chord detection using multiple algorithms
   - Key signature detection via Krumhansl-Schmuckler profiles
   - Voicing analysis and confidence scoring

2. **Database Enhancement** (`database_enhancer.py`)
   - Extended SQLite schema for MIDI data storage
   - Learning statistics tracking
   - Backward compatibility with existing data

3. **Machine Learning Engine** (`machine_learning_engine.py`)
   - **THIS IS THE KEY**: System learns from user corrections
   - Pattern recognition for chord progressions
   - Predictive analysis for better future accuracy

4. **Enhanced GUI Integration**
   - Added MIDI import tab to progression builder
   - **Modified**: "Import Progressions" button now accepts MIDI files
   - Drag-drop MIDI file support with real-time analysis

#### **Why This Matters:**
- **User Request**: "The more chords that get added the better the algorithm becomes"
- **Implementation**: MIDI imports automatically feed the learning algorithm
- **Result**: System becomes smarter with each MIDI file imported

### **Integration Points:**
```python
# In progression_rebuilder_gui.py:
def import_progressions_to_library(self):
    # NOW ACCEPTS: .progression AND .mid/.midi files
    # Automatically detects file type and processes accordingly
    # MIDI files → chord detection → library storage → algorithm improvement
```

---

## ⚙️ **CONFIGURATION & WORKFLOW**

### **Professional XPM Creation Workflow**
1. **Input Selection**: Audio files, sample libraries, or MIDI progressions
2. **Analysis Phase**: Pitch detection, key mapping, theory analysis  
3. **Conversion**: Professional XPM generation with firmware compliance
4. **Enhancement**: Layer management, velocity mapping, keygroup optimization
5. **Quality Control**: Expansion Doctor analysis for bloat detection

### **MIDI Learning Workflow (NEW)**
1. **Import MIDI**: Via "Import Progressions & MIDI" button
2. **Automatic Analysis**: Chord detection and key identification
3. **User Correction**: Fix any incorrect detections  
4. **Machine Learning**: System learns from corrections
5. **Algorithm Improvement**: Better accuracy on future imports

### **Key Settings & Preferences**
```python
# Firmware Selection (affects layer limits and features)
self.firmware_version = tk.StringVar(value="3.5.0")

# Creative Mode Configuration
self.creative_config = {}  # User-defined creative parameters

# File Dialog Safety (macOS compatibility)
self.last_browse_path = os.path.expanduser("~")
```

---

## 🎨 **GUI THEMING & DESIGN**

### **Professional MPC Color Scheme**
```python
MPC_BEIGE = "#EAE6DA"      # Background
MPC_DARK_GREY = "#414042"  # Text/borders  
MPC_PAD_GREY = "#7B7C7D"   # Buttons
MPC_RED = "#B91C1C"        # Accents/warnings
MPC_WHITE = "#FFFFFF"      # Highlights
```

### **Layout Philosophy**
- **Professional**: Clean, organized interface matching MPC aesthetic
- **Modular**: Each major function in own window/frame
- **Accessible**: Clear labeling, logical grouping, keyboard shortcuts
- **Responsive**: Proper grid weights and sizing

---

## 🚨 **CRITICAL PRESERVATION RULES**

### **DO NOT MODIFY:**
1. **XPM Professional Standards** (lines 28-35 in main file)
2. **APP_VERSION** constant (`v2.11.6.6`)
3. **Firmware compatibility matrices** 
4. **Root note offset calculations** (+1 for MPC hardware)
5. **File format support dictionaries**

### **MODIFY WITH EXTREME CAUTION:**
1. **Database schema changes** (use migration scripts)
2. **Audio format detection logic**
3. **XPM XML structure generation**
4. **Core utility functions** in `xmp_utils.py`

### **SAFE TO ENHANCE:**
1. **GUI improvements and new tools**
2. **Additional audio format support** 
3. **MIDI analysis algorithms**
4. **Machine learning enhancements**
5. **User experience features**

---

## 🔍 **DEBUGGING & LOGGING**

### **Logging System**
```python
# Dual output: File + GUI text widget
logging.info("Application started. Version {APP_VERSION}.")
# Logs to both converter.log and GUI log viewer
```

### **Error Handling Patterns**
```python
try:
    # Risky operation
    result = complex_operation()
except SpecificException as e:
    logging.error(f"Specific failure: {e}")
    # Graceful fallback
except Exception as e:
    logging.error(f"Unexpected error in {operation}: {e}")
    # User-friendly error message
```

### **Common Debug Points**
- **MIDI Import Issues**: Check mido availability
- **Audio Conversion**: Check librosa/soundfile availability  
- **GUI Crashes**: Usually file dialog safety issues on macOS
- **XPM Validation**: ConvertWithMoss standards compliance

---

## 📊 **TESTING & QUALITY ASSURANCE**

### **Test Scenarios**
1. **Format Compatibility**: All supported input formats → XPM
2. **Firmware Compliance**: Generated XPM works on all MPC models
3. **MIDI Import**: Various MIDI styles and complexities
4. **Learning Accuracy**: Machine learning improvement over time
5. **GUI Responsiveness**: All windows and dialogs function properly

### **Quality Metrics**
- **Conversion Accuracy**: Audio fidelity preservation
- **MIDI Chord Detection**: Accuracy vs manual analysis
- **Learning Improvement**: Algorithm accuracy over time
- **File Size Optimization**: Minimal XPM bloat
- **User Experience**: Workflow efficiency

---

## 🎯 **FUTURE ENHANCEMENT AREAS**

### **Immediate Opportunities**
1. **Enhanced MIDI Analysis**: Rhythm detection, melody analysis
2. **Advanced Machine Learning**: Deep learning chord classification
3. **Cloud Integration**: Shared learning database
4. **Real-time Processing**: Live MIDI input analysis

### **Long-term Vision**
1. **AI-Powered Sample Matching**: Automatic sample-to-chord mapping
2. **Advanced Music Theory**: Jazz harmony, modal interchange
3. **Integration APIs**: Third-party DAW connectivity
4. **Professional Workflows**: Batch operations, project management

---

## 💡 **KEY SUCCESS FACTORS**

### **What Makes This System Unique**
1. **Professional Standards**: Actual industry-grade XPM generation
2. **Intelligent Learning**: MIDI analysis that improves over time
3. **Hardware Integration**: Direct MPC hardware compatibility
4. **Comprehensive Toolset**: Complete workflow from audio → MPC

### **User Value Proposition**
- **Producers**: Professional XPM creation for MPC hardware
- **Musicians**: Advanced music theory analysis and learning
- **Educators**: Chord progression analysis and pattern recognition
- **Developers**: Modular system for music technology integration

---

## 🔧 **TECHNICAL IMPLEMENTATION NOTES**

### **File Safety (macOS Critical)**
```python
# Always use safe file dialogs
from tk_file_utils import askopenfilename as safe_askopenfilename
# Prevents NSInvalidArgumentException crashes
```

### **Dependency Management**
```python
# Pattern for optional features
try:
    from advanced_module import Feature
    FEATURE_AVAILABLE = True
except ImportError:
    Feature = DummyFeature  # Always provide fallback
    FEATURE_AVAILABLE = False
```

### **Database Updates**
```python
# Use enhance_music_theory_database() for schema changes
# Maintains backward compatibility with existing data
```

---

## 🎵 **CONCLUSION FOR AI AGENTS**

This is a **professional music production system** with **advanced AI learning capabilities**, NOT a simple file converter. The MIDI chord analysis system is the crown jewel - it enables continuous algorithm improvement through user interaction.

**Key Understanding**: Every MIDI file import makes the system smarter. The machine learning engine learns from user corrections and pattern recognition, fulfilling the core requirement that "the more chords that get added the better the algorithm becomes."

**Architecture**: Modular, extensible, professional-grade with proper error handling and backward compatibility.

**Standards**: Maintains strict MPC hardware compatibility and professional XPM generation standards.

**Future**: Ready for enhancement in AI/ML areas while preserving core functionality and professional standards.

---

**Remember**: This system represents thousands of hours of professional music production tool development. Approach modifications with respect for the existing architecture and user workflows.